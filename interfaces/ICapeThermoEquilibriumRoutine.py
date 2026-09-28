"ICapeThermoEquilibriumRoutine"

import copy
import logging
from typing import List, Optional

import si_units as si
from comtypes.gen import CAPEOPEN110
from gnnepcsaft.pcsaft.feos.equilibria import (
    is_stable_feos,
    mix_bp_at_fixed_pressure_feos,
    mix_dp_at_fixed_pressure_feos,
    mix_ph_flash_feos,
    mix_ps_flash_feos,
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
        kij_matrix = copy.copy(self._kij_matrix)
        assert pcsaft_parameters is not None

        if not self.CheckEquilibriumSpec(specification1, specification2, solutionType):
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeLimitedImpl,
                description="Only TP, Tphasefraction, Pphasefraction"
                " flash specification is"
                " implemented by this Property Package."
                f" Specifications {(specification1, specification2, solutionType)}"
                " not supported",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
            )

        temperature = self._get_overall_scalar("temperature")
        pressure = self._get_overall_scalar("pressure")
        fractions = self._get_overall_fractions()
        if 0.0 in fractions:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeFailedInitialisation,
                description=f"Overall fractions wrongly set to {fractions}",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
            )
        state = [temperature, pressure, *fractions]
        if spec2[0].lower() == "enthalpy":
            enthalpy = self._get_overall_scalar("enthalpy", "Mole")
            state = [temperature, pressure, enthalpy, *fractions]
        if spec2[0].lower() == "entropy":
            entropy = self._get_overall_scalar("entropy", "Mole")
            state = [temperature, pressure, entropy, *fractions]
        state_for_stability = [temperature, pressure, *fractions]

        logging.debug("IN CalcEquilibrium ---> state = %s", state)

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
                parameters=pcsaft_parameters,
                state=state_for_stability,
                kij_matrix=kij_matrix,
            ):
                logging.debug("STABLE PHASE")

                bp, _dp = mix_vp_feos(
                    parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
                )
                if pressure > bp:
                    liquid_fractions = fractions
                    vapor_fractions = [0.0] * len(fractions)
                else:
                    liquid_fractions = [0.0] * len(fractions)
                    vapor_fractions = fractions

                vapor_beta, liquid_beta = self._get_vl_beta(
                    fractions, liquid_fractions, vapor_fractions
                )

                self._set_equilibrium_for_stable_phase(
                    spec1,
                    spec2,
                    pcsaft_parameters,
                    kij_matrix,
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
            flash = self._get_flash(
                spec1_0=spec1[0].lower(),
                spec2_0=spec2[0].lower(),
                pcsaft_parameters=pcsaft_parameters,
                kij_matrix=kij_matrix,
                state=state,
            )

        except Exception as exc:  # pylint:disable=broad-exception-caught
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeSolvingError,
                description=f"Flash failed to converge: {exc}",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
            )

        self._set_equilibrium_from_flash(
            spec1=spec1,
            spec2=spec2,
            pcsaft_parameters=pcsaft_parameters,
            kij_matrix=kij_matrix,
            state=state,
            material=material,
            flash=flash,
            overall_fractions=fractions,
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
        soltype = str(solutionType).lower()
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
                # {"pressure", "enthalpy"}, # needs ideal gas model
                # {"pressure", "entropy"}, # needs ideal gas model
            )
        ) and soltype in (
            "unspecified",
            "normal",
        )

    def _compute_bp_or_dp(self, prop, pcsaft_parameters, state, kij_matrix):

        if prop in ("dewPointPressure", "bubblePointPressure"):
            bp, dp = mix_vp_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
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
                        kij_matrix=kij_matrix,
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
                        kij_matrix=kij_matrix,
                    )
                ]
            except Exception:  # pylint:disable=broad-exception-caught
                return [float("nan")]
        return [float("nan")]

    def _not_setted_bp_or_dp(
        self,
        spec1: List[str],
        spec2: List[str],
        pcsaft_parameters: List[List[float]],
        kij_matrix: List[List[float]],
        state: List[float],
        material: CAPEOPEN110.ICapeThermoMaterial,
    ):
        if (
            spec1[0].lower() in ("temperature", "pressure")
            and spec2[0].lower() == "phasefraction"
            and spec2[2].lower() == "vapor"
        ):
            phaseFraction = material.GetSinglePhaseProp(
                "phaseFraction", "Vapor", "Mole", None
            )[0]

            logging.debug("IN CalcEquilibrium ---> phaseFraction = %r", phaseFraction)

            if spec1[0].lower() == "temperature":
                if phaseFraction == 1.0:
                    prop = "dewPointPressure"
                    value = self._compute_bp_or_dp(
                        prop=prop,
                        pcsaft_parameters=pcsaft_parameters,
                        state=state,
                        kij_matrix=kij_matrix,
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
                        kij_matrix=kij_matrix,
                    )

                    logging.debug("IN CalcEquilibrium --->%r = %r", prop, value)

                    material.SetSinglePhaseProp(
                        "Pressure", "Liquid", None, self.r8_array_variant(value)
                    )
            if spec1[0].lower() == "pressure":
                if phaseFraction == 1.0:
                    prop = "dewPointTemperature"
                    value = self._compute_bp_or_dp(
                        prop=prop,
                        pcsaft_parameters=pcsaft_parameters,
                        state=state,
                        kij_matrix=kij_matrix,
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
                        kij_matrix=kij_matrix,
                    )
                    logging.debug("IN CalcEquilibrium --->%r = %r", prop, value)
                    material.SetSinglePhaseProp(
                        "Temperature", "Liquid", None, self.r8_array_variant(value)
                    )
            return False
        return True

    def _get_flash(
        self,
        spec1_0: str,
        spec2_0: str,
        pcsaft_parameters: List[List[float]],
        kij_matrix: Optional[List[List[float]]],
        state: List[float],
    ):
        if spec1_0 in (
            "temperature",
            "pressure",
        ) and spec2_0 in (
            "pressure",
            "phasefraction",
        ):
            return mix_tp_flash_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
            )
        if spec1_0 == "pressure" and spec2_0 == "enthalpy":
            return mix_ph_flash_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
            )
        if spec1_0 == "pressure" and spec2_0 == "entropy":
            return mix_ps_flash_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
            )
        return self.raise_cape_error(
            error_cls=ecape_errors.ECapeLimitedImpl,
            description="Only TP, Tphasefraction, Pphasefraction"
            " flash specification is "
            "implemented by this Property Package",
            interfaceName="ICapeThermoEquilibriumRoutine",
            operation="CalcEquilibrium",
        )

    def _set_equilibrium_for_stable_phase(
        self,
        spec1,
        spec2,
        pcsaft_parameters,
        kij_matrix,
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
            kij_matrix,
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
        material.SetSinglePhaseProp(
            "phaseFraction",
            "Vapor",
            "Mole",
            self.r8_array_variant([vapor_beta]),
        )
        material.SetSinglePhaseProp(
            "phaseFraction",
            "Liquid",
            "Mole",
            self.r8_array_variant([liquid_beta]),
        )

        rss_mb = self.rss_mb()
        logging.debug("PROCESS MEMORY: %r MB", rss_mb)

    def _set_equilibrium_from_flash(
        self,
        spec1,
        spec2,
        pcsaft_parameters,
        kij_matrix,
        state,
        material,
        flash,
        overall_fractions,
    ):

        liquid_fractions = flash.liquid.molefracs
        vapor_fractions = flash.vapor.molefracs

        vapor_beta, liquid_beta = self._get_vl_beta(
            overall_fractions, liquid_fractions, vapor_fractions
        )

        liquid_temperature = flash.liquid.temperature / si.KELVIN
        liquid_pressure = flash.liquid.pressure() / si.PASCAL

        vapor_temperature = flash.vapor.temperature / si.KELVIN
        vapor_pressure = flash.vapor.pressure() / si.PASCAL

        logging.debug(
            "IN CalcEquilibrium ---> [liquid_fractions, vapor_fractions] == %s",
            [liquid_fractions, vapor_fractions],
        )
        logging.debug(
            "IN CalcEquilibrium ---> [liquid_beta, vapor_beta] == %s",
            [liquid_beta, vapor_beta],
        )

        if self._not_setted_bp_or_dp(
            spec1, spec2, pcsaft_parameters, kij_matrix, state, material
        ):

            material.SetSinglePhaseProp(
                "temperature",
                "Vapor",
                None,
                self.r8_array_variant([vapor_temperature]),
            )
            material.SetSinglePhaseProp(
                "temperature",
                "Liquid",
                None,
                self.r8_array_variant([liquid_temperature]),
            )
            material.SetSinglePhaseProp(
                "pressure",
                "Vapor",
                None,
                self.r8_array_variant([vapor_pressure]),
            )
            material.SetSinglePhaseProp(
                "pressure",
                "Liquid",
                None,
                self.r8_array_variant([liquid_pressure]),
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
        material.SetSinglePhaseProp(
            "phaseFraction",
            "Vapor",
            "Mole",
            self.r8_array_variant([vapor_beta]),
        )
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


def _find_t_from_phase_fraction(
    state_temperature,
    state_pressure,
    overall_fractions,
    pcsaft_parameters,
    kij_matrix,
    phasefraction,
) -> float:

    bp = (
        mix_bp_at_fixed_pressure_feos(
            parameters=pcsaft_parameters,
            state=[state_temperature, state_pressure, *overall_fractions],
            kij_matrix=kij_matrix,
        )
        * 1.001
    )

    dp = (
        mix_dp_at_fixed_pressure_feos(
            parameters=pcsaft_parameters,
            state=[state_temperature, state_pressure, *overall_fractions],
            kij_matrix=kij_matrix,
        )
        * 0.999
    )

    find_root = root_scalar(
        f=lambda temperature: phasefraction
        - mix_tp_flash_feos(
            parameters=pcsaft_parameters,
            state=[temperature, state_pressure, *overall_fractions],
            kij_matrix=kij_matrix,
        ).vapor_phase_fraction,
        method="brentq",
        bracket=[bp, dp],
        x0=(bp + dp) / 2,
    )

    return find_root.root


def _find_p_from_phase_fraction(
    state_temperature,
    state_pressure,
    overall_fractions,
    pcsaft_parameters,
    kij_matrix,
    phasefraction,
) -> float:

    bp, dp = mix_vp_feos(
        parameters=pcsaft_parameters,
        state=[state_temperature, state_pressure, *overall_fractions],
        kij_matrix=kij_matrix,
    )
    bp *= 0.99
    dp *= 1.01

    find_root = root_scalar(
        f=lambda pressure: phasefraction
        - mix_tp_flash_feos(
            parameters=pcsaft_parameters,
            state=[state_temperature, pressure, *overall_fractions],
            kij_matrix=kij_matrix,
        ).vapor_phase_fraction,
        method="brentq",
        bracket=[dp, bp],
        x0=(bp + dp) / 2,
    )

    return find_root.root
