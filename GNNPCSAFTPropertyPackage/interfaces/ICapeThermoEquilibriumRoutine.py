"ICapeThermoEquilibriumRoutine"

import copy
import logging
import math
from typing import List

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
from scipy.optimize import root_scalar

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
        self.CheckEquilibriumSpec(specification1, specification2, solutionType)
        spec1 = self._as_list(specification1.value)
        spec2 = self._as_list(specification2.value)
        logging.debug(
            "IN CalcEquilibrium ---> (specification1,specification2,solutionType) ="
            " %r",
            (specification1, specification2, solutionType),
        )
        assert self.material is not None
        material = self.material
        pcsaft_parameters = copy.copy(self.pcsaft_parameters)
        kij_matrix = copy.copy(self._kij_matrix)
        assert pcsaft_parameters is not None
        assert kij_matrix is not None

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

        logging.debug("IN CalcEquilibrium ---> state = %s", state)
        spec_names = {str(spec1[0]).strip().lower(), str(spec2[0]).strip().lower()}
        logging.debug("IN CalcEquilibrium ---> spec_names = %s", spec_names)

        if spec_names == {"temperature", "pressure"}:

            return self._tp_equilibrium_logic(
                spec_names=spec_names,
                pcsaft_parameters=pcsaft_parameters,
                kij_matrix=kij_matrix,
                temperature=temperature,
                pressure=pressure,
                fractions=fractions,
                material=material,
            )
        if spec_names == {"temperature", "phasefraction"}:
            return self._tphasefraction_equilibrium_logic(
                spec_names=spec_names,
                pcsaft_parameters=pcsaft_parameters,
                kij_matrix=kij_matrix,
                overall_temperature=temperature,
                overall_pressure=pressure,
                overall_fractions=fractions,
                material=material,
            )
        if spec_names == {"pressure", "phasefraction"}:
            return self._pphasefraction_equilibrium_logic(
                spec_names=spec_names,
                pcsaft_parameters=pcsaft_parameters,
                kij_matrix=kij_matrix,
                overall_temperature=temperature,
                overall_pressure=pressure,
                overall_fractions=fractions,
                material=material,
            )
        return self.raise_cape_error(
            error_cls=ecape_errors.ECapeLimitedImpl,
            description="Only TP, Tphasefraction, Pphasefraction"
            " flash specification is"
            " implemented by this Property Package."
            f" Specifications {(specification1, specification2, solutionType)}"
            " not supported",
            interfaceName="ICapeThermoEquilibriumRoutine",
            operation="CalcEquilibrium",
        )

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
        self._require_material(
            interfaceName="ICapeThermoEquilibriumRoutine",
            operation="CheckEquilibriumSpec",
        )
        if not spec1 or not spec2:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeInvalidArgument,
                description="Missing equilibrium specifications",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CheckEquilibriumSpec",
                moreInfo="Both equilibrium specifications are required",
            )
        if len(spec1) < 3 or len(spec2) < 3:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeInvalidArgument,
                description="Incorrect minimum number of specifications:"
                f" len(spec1) == {len(spec1)} and len(spec2) == {len(spec2)}",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CheckEquilibriumSpec",
            )
        names = {str(spec1[0]).strip().lower(), str(spec2[0]).strip().lower()}
        basis = {str(spec1[1]).strip().lower(), str(spec2[1]).strip().lower()}
        phaselabels = {str(spec1[2]).strip().lower(), str(spec2[2]).strip().lower()}
        if (
            (
                names
                not in (
                    {"temperature", "pressure"},
                    {"temperature", "phasefraction"},
                    {"pressure", "phasefraction"},
                    # {"pressure", "enthalpy"}, # needs ideal gas model
                    # {"pressure", "entropy"}, # needs ideal gas model
                )
            )
            or soltype not in ("unspecified", "normal")
            or basis not in ({"none"}, {"none", "mole"})
            or phaselabels not in ({"overall", "vapor"}, {"overall"})
        ):
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeLimitedImpl,
                description="Only TP, Tphasefraction, Pphasefraction"
                " flash specification is"
                " implemented by this Property Package."
                f" Specifications {(specification1, specification2, solutionType)}"
                " not supported",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CheckEquilibriumSpec",
            )
        return True

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

    def _get_flash(self, spec_names: set[str]):
        temperature = self._get_overall_scalar("temperature")
        pressure = self._get_overall_scalar("pressure")
        fractions = self._get_overall_fractions()
        pcsaft_parameters = self.pcsaft_parameters
        assert pcsaft_parameters is not None
        kij_matrix = self._kij_matrix
        assert kij_matrix is not None
        state = [temperature, pressure, *fractions]
        try:
            if spec_names in (
                {
                    "temperature",
                    "pressure",
                },
                {
                    "pressure",
                    "phasefraction",
                },
                {
                    "temperature",
                    "phasefraction",
                },
            ):
                return mix_tp_flash_feos(
                    parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
                )
            if spec_names == {"pressure", "enthalpy"}:
                return mix_ph_flash_feos(
                    parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
                )
            if spec_names == {"pressure", "entropy"}:
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
        except RuntimeError as exc:
            return self.raise_cape_error(
                error_cls=ecape_errors.ECapeSolvingError,
                description=f"Flash calculation failed: {exc}",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
            )

    def _set_equilibrium_for_stable_phase(
        self,
        temperature: float,
        pressure: float,
        fractions_at_phase: List[float],
        phase_label: str,
    ):
        material = self.material
        assert material is not None
        material.SetSinglePhaseProp(
            "temperature",
            phase_label,
            None,
            self.r8_array_variant([temperature]),
        )
        material.SetSinglePhaseProp(
            "pressure",
            phase_label,
            None,
            self.r8_array_variant([pressure]),
        )
        material.SetSinglePhaseProp(
            "fraction",
            phase_label,
            "Mole",
            self.r8_array_variant(fractions_at_phase),
        )
        material.SetSinglePhaseProp(
            "phaseFraction",
            phase_label,
            "Mole",
            self.r8_array_variant([1.0]),
        )

        phase_label2 = "Liquid" if phase_label == "Vapor" else "Vapor"

        material.SetSinglePhaseProp(
            "temperature",
            phase_label2,
            None,
            self.r8_array_variant([temperature]),
        )
        material.SetSinglePhaseProp(
            "pressure",
            phase_label2,
            None,
            self.r8_array_variant([pressure]),
        )
        material.SetSinglePhaseProp(
            "fraction",
            phase_label2,
            "Mole",
            self.r8_array_variant([0.0] * len(fractions_at_phase)),
        )
        material.SetSinglePhaseProp(
            "phaseFraction",
            phase_label2,
            "Mole",
            self.r8_array_variant([0.0]),
        )

        rss_mb = self.rss_mb()
        logging.debug("PROCESS MEMORY: %r MB", rss_mb)

    def _set_equilibrium_from_flash(
        self,
        flash,
    ):

        liquid_fractions = flash.liquid.molefracs
        vapor_fractions = flash.vapor.molefracs

        vapor_beta = flash.vapor_phase_fraction
        liquid_beta = 1.0 - vapor_beta

        liquid_temperature = flash.liquid.temperature / si.KELVIN
        liquid_pressure = flash.liquid.pressure() / si.PASCAL

        vapor_temperature = flash.vapor.temperature / si.KELVIN
        vapor_pressure = flash.vapor.pressure() / si.PASCAL
        material = self.material
        assert material is not None

        logging.debug(
            "IN CalcEquilibrium ---> [liquid_fractions, vapor_fractions] == %s",
            [liquid_fractions, vapor_fractions],
        )
        logging.debug(
            "IN CalcEquilibrium ---> [liquid_beta, vapor_beta] == %s",
            [liquid_beta, vapor_beta],
        )

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

    def _solve_phase_fraction(
        self,
        beta_of,
        x_beta0: float,
        x_beta1: float,
        phasefraction: float,
    ) -> float:
        """
        Solve beta_of(x) = phasefraction for x between the two single-phase
        boundaries x_beta0 (where beta = 0, i.e. the bubble point) and
        x_beta1 (where beta = 1, i.e. the dew point).

        The boundary values are assigned analytically instead of being
        flashed, so f(x_beta0) = phasefraction > 0 and
        f(x_beta1) = phasefraction - 1 < 0 always hold. Every phasefraction
        strictly inside (0, 1) is therefore guaranteed to be bracketed, no
        matter how close to 0 or 1 it is or how narrow the boiling range.
        Only the interior points are flashed.
        """
        lo, hi = sorted((x_beta0, x_beta1))
        direction = 1.0 if x_beta1 > x_beta0 else -1.0  # +1 for T, -1 for P

        def residual(x: float) -> float:
            if (x - x_beta0) * direction <= 0.0:
                return phasefraction  # at or beyond the beta = 0 boundary
            if (x - x_beta1) * direction >= 0.0:
                return phasefraction - 1.0  # at or beyond the beta = 1 boundary
            try:
                beta = beta_of(x)
            except RuntimeError:
                beta = 0.0
            # clip: single-phase results from the flash are beta = 0 or 1
            return phasefraction - min(1.0, max(0.0, beta))

        return root_scalar(
            f=residual,
            method="brentq",
            bracket=[lo, hi],
            xtol=1e-9,
            rtol=1e-10,
            maxiter=200,
        ).root

    def _find_t_from_phase_fraction(
        self,
        state_temperature,
        state_pressure,
        overall_fractions,
        pcsaft_parameters,
        kij_matrix,
        phasefraction,
    ) -> float:

        state = [state_temperature, state_pressure, *overall_fractions]
        try:
            t_bubble = mix_bp_at_fixed_pressure_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
            )
            t_dew = mix_dp_at_fixed_pressure_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
            )
            if not (math.isfinite(t_bubble) and math.isfinite(t_dew)):
                raise ValueError(f"bubble/dew T not finite: {t_bubble}, {t_dew}")
            if not t_dew > t_bubble:
                raise ValueError(
                    f"no two-phase region at this pressure: Tbubble={t_bubble}, Tdew={t_dew}"
                )
            return self._solve_phase_fraction(
                beta_of=lambda temperature: mix_tp_flash_feos(
                    parameters=pcsaft_parameters,
                    state=[temperature, state_pressure, *overall_fractions],
                    kij_matrix=kij_matrix,
                ).vapor_phase_fraction,
                x_beta0=t_bubble,
                x_beta1=t_dew,
                phasefraction=phasefraction,
            )
        except (ValueError, RuntimeError) as exc:
            return self.raise_cape_error(
                error_cls=ecape_errors.ECapeSolvingError,
                description="Failed to calculate from"
                f" vapor phase fraction = {phasefraction}: {exc}",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
                moreInfo="Bubble/dew point calculation or the root finding on"
                " the vapor phase fraction did not converge.",
            )

    def _find_p_from_phase_fraction(
        self,
        state_temperature,
        state_pressure,
        overall_fractions,
        pcsaft_parameters,
        kij_matrix,
        phasefraction,
    ) -> float:

        state = [state_temperature, state_pressure, *overall_fractions]
        try:
            p_bubble, p_dew = mix_vp_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
            )
            if not (math.isfinite(p_bubble) and math.isfinite(p_dew)):
                raise ValueError(f"bubble/dew P not finite: {p_bubble}, {p_dew}")
            if not p_bubble > p_dew:
                raise ValueError(
                    f"no two-phase region at this temperature: Pbubble={p_bubble}, Pdew={p_dew}"
                )
            return self._solve_phase_fraction(
                beta_of=lambda pressure: mix_tp_flash_feos(
                    parameters=pcsaft_parameters,
                    state=[state_temperature, pressure, *overall_fractions],
                    kij_matrix=kij_matrix,
                ).vapor_phase_fraction,
                x_beta0=p_bubble,
                x_beta1=p_dew,
                phasefraction=phasefraction,
            )
        except (ValueError, RuntimeError) as exc:
            return self.raise_cape_error(
                error_cls=ecape_errors.ECapeSolvingError,
                description="Failed to calculate from"
                f" vapor phase fraction = {phasefraction}: {exc}",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
                moreInfo="Bubble/dew point calculation or the root finding on"
                " the vapor phase fraction did not converge.",
            )

    def _tp_equilibrium_logic(
        self,
        spec_names: set[str],
        pcsaft_parameters: List[List[float]],
        kij_matrix: List[List[float]],
        temperature: float,
        pressure: float,
        fractions: List[float],
        material: CAPEOPEN110.ICapeThermoMaterial,
    ):
        is_stable = True
        state = [temperature, pressure, *fractions]
        try:
            is_stable = is_stable_feos(
                parameters=pcsaft_parameters,
                state=state,
                kij_matrix=kij_matrix,
            )
        except RuntimeError as exc:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeSolvingError,
                description="Failed to calculate from"
                f" overall state = {state}: {exc}",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
                moreInfo="It was not possible to conclude stability analysis.",
            )
        if is_stable:
            logging.debug("STABLE PHASE")

            bp, _dp = mix_vp_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
            )
            if pressure > bp:
                stable_phase_label = "Liquid"
            else:
                stable_phase_label = "Vapor"

            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                    ]
                ),
            )
            self._set_equilibrium_for_stable_phase(
                temperature=temperature,
                pressure=pressure,
                fractions_at_phase=fractions,
                phase_label=stable_phase_label,
            )
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                    ]
                ),
            )
            return 0

        logging.debug("UNSTABLE PHASE")
        material.SetPresentPhases(
            self.bstr_array_variant(["Vapor", "Liquid"]),
            self.i4_array_variant(
                [
                    CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                    CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                ]
            ),
        )
        try:
            flash = self._get_flash(spec_names=spec_names)
        except (ValueError, RuntimeError) as exc:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeSolvingError,
                description=f"Flash failed to converge: {exc}",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
            )
        self._set_equilibrium_from_flash(flash=flash)
        material.SetPresentPhases(
            self.bstr_array_variant(["Vapor", "Liquid"]),
            self.i4_array_variant(
                [
                    CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                    CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                ]
            ),
        )
        return 0

    def _tphasefraction_equilibrium_logic(
        self,
        spec_names: set[str],
        pcsaft_parameters: List[List[float]],
        kij_matrix: List[List[float]],
        overall_temperature: float,
        overall_pressure: float,
        overall_fractions: List[float],
        material: CAPEOPEN110.ICapeThermoMaterial,
    ):
        state = [overall_temperature, overall_pressure, *overall_fractions]

        phaseFraction = material.GetSinglePhaseProp(
            "phaseFraction", "Vapor", "Mole", None
        )[0]
        logging.debug("IN CalcEquilibrium ---> phaseFraction = %r", phaseFraction)
        if phaseFraction == 1.0:
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                    ]
                ),
            )
            prop = "dewPointPressure"
            pressure = self._compute_bp_or_dp(
                prop=prop,
                pcsaft_parameters=pcsaft_parameters,
                state=state,
                kij_matrix=kij_matrix,
            )

            logging.debug("IN CalcEquilibrium --->%r = %r", prop, pressure)
            self._set_equilibrium_for_stable_phase(
                temperature=overall_temperature,
                pressure=pressure[0],
                fractions_at_phase=overall_fractions,
                phase_label="Vapor",
            )
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                    ]
                ),
            )

        if phaseFraction == 0.0:
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                    ]
                ),
            )
            prop = "bubblePointPressure"
            pressure = self._compute_bp_or_dp(
                prop=prop,
                pcsaft_parameters=pcsaft_parameters,
                state=state,
                kij_matrix=kij_matrix,
            )
            logging.debug("IN CalcEquilibrium --->%r = %r", prop, pressure)
            self._set_equilibrium_for_stable_phase(
                temperature=overall_temperature,
                pressure=pressure[0],
                fractions_at_phase=overall_fractions,
                phase_label="Liquid",
            )
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                    ]
                ),
            )
        if 0.0 < phaseFraction < 1.0:
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                    ]
                ),
            )

            pressure = self._find_p_from_phase_fraction(
                state_temperature=state[0],
                state_pressure=state[1],
                overall_fractions=state[2:],
                pcsaft_parameters=pcsaft_parameters,
                kij_matrix=kij_matrix,
                phasefraction=phaseFraction,
            )
            material.SetOverallProp("Pressure", None, self.r8_array_variant([pressure]))
            try:
                flash = self._get_flash(spec_names=spec_names)
            except (ValueError, RuntimeError) as exc:
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeSolvingError,
                    description=f"Flash failed to converge: {exc}",
                    interfaceName="ICapeThermoEquilibriumRoutine",
                    operation="CalcEquilibrium",
                )
            self._set_equilibrium_from_flash(flash=flash)
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                    ]
                ),
            )
        return 0

    def _pphasefraction_equilibrium_logic(
        self,
        spec_names: set[str],
        pcsaft_parameters: List[List[float]],
        kij_matrix: List[List[float]],
        overall_temperature: float,
        overall_pressure: float,
        overall_fractions: List[float],
        material: CAPEOPEN110.ICapeThermoMaterial,
    ):
        state = [overall_temperature, overall_pressure, *overall_fractions]
        phaseFraction = material.GetSinglePhaseProp(
            "phaseFraction", "Vapor", "Mole", None
        )[0]
        logging.debug("IN CalcEquilibrium ---> phaseFraction = %r", phaseFraction)
        if phaseFraction == 1.0:
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                    ]
                ),
            )
            prop = "dewPointTemperature"
            temperature = self._compute_bp_or_dp(
                prop=prop,
                pcsaft_parameters=pcsaft_parameters,
                state=state,
                kij_matrix=kij_matrix,
            )
            logging.debug("IN CalcEquilibrium --->%r = %r", prop, temperature)
            self._set_equilibrium_for_stable_phase(
                temperature=temperature[0],
                pressure=overall_pressure,
                fractions_at_phase=overall_fractions,
                phase_label="Vapor",
            )
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                    ]
                ),
            )
        if phaseFraction == 0.0:
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                    ]
                ),
            )
            prop = "bubblePointTemperature"
            temperature = self._compute_bp_or_dp(
                prop=prop,
                pcsaft_parameters=pcsaft_parameters,
                state=state,
                kij_matrix=kij_matrix,
            )
            logging.debug("IN CalcEquilibrium --->%r = %r", prop, temperature)
            self._set_equilibrium_for_stable_phase(
                temperature=temperature[0],
                pressure=overall_pressure,
                fractions_at_phase=overall_fractions,
                phase_label="Liquid",
            )
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                    ]
                ),
            )
        if 0.0 < phaseFraction < 1.0:
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                        CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                    ]
                ),
            )

            temperature = self._find_t_from_phase_fraction(
                state_temperature=state[0],
                state_pressure=state[1],
                overall_fractions=state[2:],
                pcsaft_parameters=pcsaft_parameters,
                kij_matrix=kij_matrix,
                phasefraction=phaseFraction,
            )
            material.SetOverallProp(
                "Temperature", None, self.r8_array_variant([temperature])
            )
            try:
                flash = self._get_flash(spec_names=spec_names)
            except (ValueError, RuntimeError) as exc:
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeSolvingError,
                    description=f"Flash failed to converge: {exc}",
                    interfaceName="ICapeThermoEquilibriumRoutine",
                    operation="CalcEquilibrium",
                )
            self._set_equilibrium_from_flash(flash=flash)
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                        CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                    ]
                ),
            )
        return 0
