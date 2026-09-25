"ICapeThermoEquilibriumRoutine"

import copy
import logging

from comtypes.gen import CAPEOPEN110
from gnnepcsaft.pcsaft.pcsaft_feos import (
    is_stable_feos,
    mix_bp_at_fixed_pressure_feos,
    mix_dp_at_fixed_pressure_feos,
    mix_tp_flash_feos,
    mix_vp_feos,
)

from . import ecape_errors
from .ICapeThermoPropertyRoutine import (
    ICapeThermoPropertyRoutine,
)


class ICapeThermoEquilibriumRoutine(
    ICapeThermoPropertyRoutine, CAPEOPEN110.ICapeThermoEquilibriumRoutine
):
    "ICapeThermoEquilibriumRoutine Class with methods implemented"

    # --- ICapeThermoEquilibriumRoutine ---
    def CalcEquilibrium(
        self,
        specification1,
        specification2,
        solutionType,
    ):
        """
        Calculates the amounts, compositions, temperature and pressure of
        the Phases present in the Material Object (as set via
        SetPresentPhases) at equilibrium, given two specifications read
        from the Material Object.

        Args:
            specification1 (CapeArrayString): first specification, as a
                sequence [property identifier, basis, phase label,
                (compound identifier)] -- see spec section 6.6 for details
                and examples (e.g. fixed T/P, fixed P/H, fixed T/vapour
                phase fraction, etc.).
            specification2 (CapeArrayString): second specification, same
                format as specification1.
            solutionType (CapeString): "Unspecified", "Normal" or
                "Retrograde".

        Returns: - (results are written back into the Material Object via
            SetPresentPhases / SetSinglePhaseProp, not returned directly)

        Raises (per spec): ECapeNoImpl, ECapeBadInvOrder, ECapeSolvingError,
            ECapeLimitedImpl, ECapeInvalidArgument,
            ECapeFailedInitialisation, ECapeUnknown.
        """
        spec1 = self._as_list(specification1.value)
        spec2 = self._as_list(specification2.value)
        logging.debug(
            "IN CalcEquilibrium ---> (specification1,specification2,solutionType) ="
            " %r",
            (specification1, specification2, solutionType),
        )
        self._require_material(
            interfaceName="ICapeThermoEquilibriumRoutine",
            operation="CalcEquilibrium",
        )
        assert self.material is not None
        material = self.material
        pcsaft_parameters = copy.copy(self.pcsaft_parameters)
        _kij_matrix = copy.copy(self._kij_matrix)
        assert pcsaft_parameters is not None

        if not self.CheckEquilibriumSpec(specification1, specification2, solutionType):
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeLimitedImpl,
                description="Only a Temperature/Pressure (TP) flash specification is "
                "implemented by this Property Package",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
            )

        temperature = self._get_overall_scalar("temperature")
        pressure = self._get_overall_scalar("pressure")
        fractions = self._get_overall_fractions()
        if 0.0 in fractions:
            return 0
        state = [temperature, pressure, *fractions]
        logging.debug("FROM MATERIAL ---> state = %s", state)

        material.SetPresentPhases(
            self.bstr_array_variant(["Vapor", "Liquid"]),
            self.i4_array_variant(
                [
                    CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                    CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                ]
            ),
        )

        try:
            if is_stable_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=_kij_matrix
            ):
                logging.debug("STABLE PHASE")
                # TODO: setup if STABLE PHASE is liquid or vapor based on TPfractions
                # Fixing at Liquid for now
                liquid_fractions = fractions
                vapor_fractions = [0.0] * len(fractions)
                # TODO: setup if STABLE PHASE is liquid or vapor based on TPfractions

                vapor_beta, liquid_beta = self._get_vl_beta(
                    fractions, liquid_fractions, vapor_fractions
                )

                self._set_equilibrium(
                    spec1,
                    spec2,
                    pcsaft_parameters,
                    _kij_matrix,
                    temperature,
                    pressure,
                    state,
                    liquid_fractions,
                    vapor_fractions,
                    vapor_beta,
                    liquid_beta,
                    material,
                )
                return 0
            logging.debug("UNSTABLE PHASE")
            result = mix_tp_flash_feos(pcsaft_parameters, state, _kij_matrix)
        except Exception as exc:  # pylint:disable=broad-exception-caught
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeSolvingError,
                description=f"TP flash failed to converge: {exc}",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
            )

        liquid_fractions = result.liquid.molefracs
        vapor_fractions = result.vapor.molefracs

        vapor_beta, liquid_beta = self._get_vl_beta(
            fractions, liquid_fractions, vapor_fractions
        )

        logging.debug(
            "IN CalcEquilibrium ---> [liquid_fractions, vapor_fractions] == %s",
            [liquid_fractions, vapor_fractions],
        )
        logging.debug(
            "IN CalcEquilibrium ---> [liquid_beta, vapor_beta] == %s",
            [liquid_beta, vapor_beta],
        )

        self._set_equilibrium(
            spec1,
            spec2,
            pcsaft_parameters,
            _kij_matrix,
            temperature,
            pressure,
            state,
            liquid_fractions,
            vapor_fractions,
            vapor_beta,
            liquid_beta,
            material,
        )

        return 0

    def CheckEquilibriumSpec(
        self,
        specification1,
        specification2,
        solutionType,
    ):
        """
        Checks whether this component can perform the Equilibrium
        Calculation implied by the given specifications and solution type,
        for the combination of Phases currently present in the Material
        Object (SetPresentPhases must have been called first).

        Args:
            specification1 (CapeArrayString): first specification, same
                format as in CalcEquilibrium.
            specification2 (CapeArrayString): second specification, same
                format as in CalcEquilibrium.
            solutionType (CapeString): "Unspecified", "Normal" or
                "Retrograde".

        Returns:
            isSupported (CapeBoolean)

        Raises (per spec): ECapeNoImpl, ECapeInvalidArgument,
            ECapeBadInvOrder, ECapeUnknown.
        """
        spec1 = self._as_list(specification1.value)
        spec2 = self._as_list(specification2.value)
        soltype = str(solutionType)
        if not spec1 or not spec2:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeInvalidArgument,
                description="Missing equilibrium specifications",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CheckEquilibriumSpec",
                moreInfo="Both equilibrium specifications are required",
            )
        names = {str(spec1[0]).strip().lower(), str(spec2[0]).strip().lower()}
        return (
            names
            in (
                {"temperature", "pressure"},
                {"temperature", "phasefraction"},
                {"pressure", "phasefraction"},
            )
        ) and soltype in (
            "Unspecified",
            "Normal",
        )

    def _compute_bp_or_dp(self, prop, pcsaft_parameters, state, _kij_matrix):

        if prop in ("dewPointPressure", "bubblePointPressure"):
            bp, dp = mix_vp_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=_kij_matrix
            )
            if prop == "bubblePointPressure":
                return [bp]
            return [dp]
        if prop == "dewPointTemperature":
            try:
                return [
                    mix_dp_at_fixed_pressure_feos(
                        parameters=pcsaft_parameters,
                        state=state,
                        kij_matrix=_kij_matrix,
                    )
                ]
            except Exception:  # pylint:disable=broad-exception-caught
                return [float("nan")]
        if prop == "bubblePointTemperature":
            try:
                return [
                    mix_bp_at_fixed_pressure_feos(
                        parameters=pcsaft_parameters,
                        state=state,
                        kij_matrix=_kij_matrix,
                    )
                ]
            except Exception:  # pylint:disable=broad-exception-caught
                return [float("nan")]
        return []

    def _not_setted_bp_or_dp(
        self, spec1, spec2, pcsaft_parameters, _kij_matrix, state, material
    ):
        if (
            spec1[0] == "Temperature"
            and spec2[0] == "phaseFraction"
            and spec2[2] == "Vapor"
        ) or (
            spec1[0] == "Pressure"
            and spec2[0] == "phaseFraction"
            and spec2[2] == "Vapor"
        ):
            phaseFraction = material.GetSinglePhaseProp(  # type: ignore
                "phaseFraction", "Vapor", "Mole"
            )[0]

            logging.debug("IN CalcEquilibrium ---> phaseFraction = %r", phaseFraction)

            if spec1[0] == "Temperature" and spec2[0] == "phaseFraction":
                if phaseFraction == 1.0:
                    prop = "dewPointPressure"
                    value = self._compute_bp_or_dp(
                        prop=prop,
                        pcsaft_parameters=pcsaft_parameters,
                        state=state,
                        _kij_matrix=_kij_matrix,
                    )

                    logging.debug("IN CalcEquilibrium --->%r = %r", prop, value)

                    material.SetSinglePhaseProp(
                        "Pressure", "Vapor", None, self.r8_array_variant(value)
                    )

                if phaseFraction == 0.0:
                    prop = "bubblePointPressure"
                    value = self._compute_bp_or_dp(
                        prop=prop,
                        pcsaft_parameters=pcsaft_parameters,
                        state=state,
                        _kij_matrix=_kij_matrix,
                    )

                    logging.debug("IN CalcEquilibrium --->%r = %r", prop, value)

                    material.SetSinglePhaseProp(
                        "Pressure", "Liquid", None, self.r8_array_variant(value)
                    )
            if spec1[0] == "Pressure" and spec2[0] == "phaseFraction":
                if phaseFraction == 1.0:
                    prop = "dewPointTemperature"
                    value = self._compute_bp_or_dp(
                        prop=prop,
                        pcsaft_parameters=pcsaft_parameters,
                        state=state,
                        _kij_matrix=_kij_matrix,
                    )

                    logging.debug("IN CalcEquilibrium --->%r = %r", prop, value)

                    material.SetSinglePhaseProp(
                        "Temperature", "Vapor", None, self.r8_array_variant(value)
                    )

                if phaseFraction == 0.0:
                    prop = "bubblePointTemperature"
                    value = self._compute_bp_or_dp(
                        prop=prop,
                        pcsaft_parameters=pcsaft_parameters,
                        state=state,
                        _kij_matrix=_kij_matrix,
                    )
                    logging.debug("IN CalcEquilibrium --->%r = %r", prop, value)
                    material.SetSinglePhaseProp(
                        "Temperature", "Liquid", None, self.r8_array_variant(value)
                    )
            return False
        return True

    def _set_equilibrium(
        self,
        spec1,
        spec2,
        pcsaft_parameters,
        _kij_matrix,
        temperature,
        pressure,
        state,
        liquid_fractions,
        vapor_fractions,
        vapor_beta,
        liquid_beta,
        material,
    ):
        if self._not_setted_bp_or_dp(
            spec1,
            spec2,
            pcsaft_parameters,
            _kij_matrix,
            state,
            material,
        ):

            material.SetSinglePhaseProp(
                "temperature",
                "Vapor",
                None,
                self.r8_array_variant([temperature]),
            )
            material.SetSinglePhaseProp(
                "temperature",
                "Liquid",
                None,
                self.r8_array_variant([temperature]),
            )
            material.SetSinglePhaseProp(
                "pressure",
                "Vapor",
                None,
                self.r8_array_variant([pressure]),
            )
            material.SetSinglePhaseProp(
                "pressure",
                "Liquid",
                None,
                self.r8_array_variant([pressure]),
            )
        material.SetSinglePhaseProp(
            "fraction",
            "Vapor",
            "Mole",
            self.r8_array_variant(vapor_fractions),
        )
        material.SetSinglePhaseProp(
            "fraction",
            "Liquid",
            "Mole",
            self.r8_array_variant(liquid_fractions),
        )
        if vapor_beta is not None:
            material.SetSinglePhaseProp(
                "phaseFraction",
                "Vapor",
                "Mole",
                self.r8_array_variant([vapor_beta]),
            )
        if liquid_beta is not None:
            material.SetSinglePhaseProp(
                "phaseFraction",
                "Liquid",
                "Mole",
                self.r8_array_variant([liquid_beta]),
            )

        rss_mb = self.rss_mb()
        logging.debug("PROCESS MEMORY: %r MB", rss_mb)

    def _get_vl_beta(self, fractions, liquid_fractions, vapor_fractions):
        vapor_beta = 0.0
        liquid_beta = 1.0 - vapor_beta
        for x_i, y_i, z_i in zip(liquid_fractions, vapor_fractions, fractions):
            if x_i != y_i:
                # Vapor fraction (V) and Liquid fraction (L)
                vapor_beta = (z_i - x_i) / (y_i - x_i)
                liquid_beta = 1.0 - vapor_beta
                break
        return vapor_beta, liquid_beta
