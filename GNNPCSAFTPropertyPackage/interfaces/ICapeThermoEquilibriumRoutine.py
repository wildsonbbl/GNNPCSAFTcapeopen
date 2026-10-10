"ICapeThermoEquilibriumRoutine"

import copy
import logging
from typing import List

import si_units as si
from comtypes.gen import CAPEOPEN110
from gnnepcsaft.pcsaft.feos.equilibria import (
    is_stable_feos,
    mix_ph_flash_feos,
    mix_ps_flash_feos,
    mix_tp_flash_feos,
    mix_vp_feos,
)

from . import ecape_errors
from .ICapeThermoPropertyRoutine import (
    ICapeThermoPropertyRoutine,
)
from .pc_saft_feos import (
    compute_bp_or_dp,
    compute_incipient_fracs,
    find_p_from_phase_fraction,
    find_t_from_phase_fraction,
    solve_enthalpy,
)

_FV_SNAP = 1e-4


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

        spec1 = self._as_list(specification1.value)
        spec2 = self._as_list(specification2.value)
        logging.debug(
            "IN CalcEquilibrium ---> (specification1,specification2,solutionType) ="
            " %r",
            (specification1, specification2, solutionType),
        )
        assert self.material is not None
        material = self.material
        pcsaft_parameters = copy.deepcopy(self.pcsaft_parameters)
        kij_matrix = copy.deepcopy(self._kij_matrix)
        assert pcsaft_parameters is not None
        assert kij_matrix is not None

        temperature = self._get_overall_scalar("temperature")
        pressure = self._get_overall_scalar("pressure")
        fractions = self._get_overall_fractions()
        if 0.0 in fractions:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeFailedInitialisation,
                description=f"Overall fractions wrongly set to {fractions}."
                " All components should have at least a residual molar fraction (e.g., 1E-10)",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
            )
        state = [temperature, pressure, *fractions]

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
                pcsaft_parameters=pcsaft_parameters,
                kij_matrix=kij_matrix,
                overall_temperature=temperature,
                overall_pressure=pressure,
                overall_fractions=fractions,
                material=material,
            )
        if spec_names == {"pressure", "phasefraction"}:
            return self._pphasefraction_equilibrium_logic(
                pcsaft_parameters=pcsaft_parameters,
                kij_matrix=kij_matrix,
                overall_temperature=temperature,
                overall_pressure=pressure,
                overall_fractions=fractions,
                material=material,
            )
        if spec_names == {"pressure", "enthalpy"}:
            return self._penthalpy_equilibrium_logic(
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
                    {"pressure", "enthalpy"},  # needs ideal gas model
                    # {"pressure", "entropy"}, # needs ideal gas model
                )
            )
            or soltype not in ("unspecified", "normal")
            or basis not in ({"none"}, {"none", "mole"})
            or phaselabels not in ({"overall", "vapor"}, {"overall"})
        ):
            return False

        return True

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
                enthalpy = self._get_overall_scalar("enthalpy", "Mole")
                state = [temperature, pressure, enthalpy, *fractions]
                return mix_ph_flash_feos(
                    parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
                )
            if spec_names == {"pressure", "entropy"}:
                entropy = self._get_overall_scalar("entropy", "Mole")
                state = [temperature, pressure, entropy, *fractions]
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

    def _set_incipient_phase(
        self,
        temperature,
        pressure,
        fractions_at_phase,
        phase_label,
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
            self.r8_array_variant([0.0]),
        )

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

        phaselabel2 = "Liquid 2" if _is_liquid_like(flash.vapor) else "Vapor"

        logging.debug(
            "IN CalcEquilibrium ---> [liquid_fractions, vapor/liquid2_fractions] == %s",
            [liquid_fractions, vapor_fractions],
        )
        logging.debug(
            "IN CalcEquilibrium ---> [liquid_beta, vapor/liquid2_beta] == %s",
            [liquid_beta, vapor_beta],
        )

        material.SetSinglePhaseProp(
            "temperature",
            phaselabel2,
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
            phaselabel2,
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
            phaselabel2,
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
            phaselabel2,
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

            try:
                bp, _dp = mix_vp_feos(
                    parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
                )
            except RuntimeError as exc:
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeSolvingError,
                    description="Failed to calculate from"
                    f" overall state = {state}: {exc}",
                    interfaceName="ICapeThermoEquilibriumRoutine",
                    operation="CalcEquilibrium",
                )
            if pressure >= bp:
                stable_phase_label = "Liquid"
            else:
                stable_phase_label = "Vapor"

            material.SetPresentPhases(
                self.bstr_array_variant([stable_phase_label]),
                self.i4_array_variant([CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS]),
            )
            self._set_equilibrium_for_stable_phase(
                temperature=temperature,
                pressure=pressure,
                fractions_at_phase=fractions,
                phase_label=stable_phase_label,
            )
            material.SetPresentPhases(
                self.bstr_array_variant([stable_phase_label]),
                self.i4_array_variant([CAPEOPEN110.CAPE_ATEQUILIBRIUM]),
            )
            return 0

        logging.debug("UNSTABLE PHASE")
        material.SetPresentPhases(
            self.bstr_array_variant(["Vapor", "Liquid", "Liquid 2"]),
            self.i4_array_variant(
                [
                    CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                    CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                    CAPEOPEN110.CAPE_UNKNOWNPHASESTATUS,
                ]
            ),
        )
        try:
            flash = self._get_flash(spec_names=spec_names)
        except RuntimeError as exc:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeSolvingError,
                description=f"Flash failed to converge: {exc}",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
            )
        self._set_equilibrium_from_flash(flash=flash)
        material.SetPresentPhases(
            self.bstr_array_variant(
                ["Liquid 2" if _is_liquid_like(flash.vapor) else "Vapor", "Liquid"]
            ),
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
        pcsaft_parameters: List[List[float]],
        kij_matrix: List[List[float]],
        overall_temperature: float,
        overall_pressure: float,
        overall_fractions: List[float],
        material: CAPEOPEN110.ICapeThermoMaterial,
    ):
        state = [overall_temperature, overall_pressure, *overall_fractions]

        phaseFraction = _snap_phase_fraction(
            material.GetSinglePhaseProp("phaseFraction", "Vapor", "Mole", None)[0]
        )
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
            try:
                pressure = compute_bp_or_dp(
                    prop=prop,
                    pcsaft_parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=kij_matrix,
                )
                incipient_fractions = compute_incipient_fracs(
                    prop=prop,
                    pcsaft_parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=kij_matrix,
                )
            except RuntimeError as exc:
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeSolvingError,
                    description=f"BP/DP calculation failed: {exc}",
                    interfaceName="ICapeThermoEquilibriumRoutine",
                    operation="CalcEquilibrium",
                )

            logging.debug("IN CalcEquilibrium --->%r = %r", prop, pressure)
            material.SetOverallProp("Pressure", None, self.r8_array_variant([pressure]))
            self._set_equilibrium_for_stable_phase(
                temperature=overall_temperature,
                pressure=pressure,
                fractions_at_phase=overall_fractions,
                phase_label="Vapor",
            )
            self._set_incipient_phase(
                temperature=overall_temperature,
                pressure=pressure,
                fractions_at_phase=incipient_fractions,
                phase_label="Liquid",
            )
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [CAPEOPEN110.CAPE_ATEQUILIBRIUM, CAPEOPEN110.CAPE_ATEQUILIBRIUM]
                ),
            )

        elif phaseFraction == 0.0:
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
            try:
                pressure = compute_bp_or_dp(
                    prop=prop,
                    pcsaft_parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=kij_matrix,
                )
                incipient_fractions = compute_incipient_fracs(
                    prop=prop,
                    pcsaft_parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=kij_matrix,
                )
            except RuntimeError as exc:
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeSolvingError,
                    description=f"BP/DP calculation failed: {exc}",
                    interfaceName="ICapeThermoEquilibriumRoutine",
                    operation="CalcEquilibrium",
                )
            logging.debug("IN CalcEquilibrium --->%r = %r", prop, pressure)
            material.SetOverallProp("Pressure", None, self.r8_array_variant([pressure]))
            self._set_equilibrium_for_stable_phase(
                temperature=overall_temperature,
                pressure=pressure,
                fractions_at_phase=overall_fractions,
                phase_label="Liquid",
            )
            self._set_incipient_phase(
                temperature=overall_temperature,
                pressure=pressure,
                fractions_at_phase=incipient_fractions,
                phase_label="Vapor",
            )
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [CAPEOPEN110.CAPE_ATEQUILIBRIUM, CAPEOPEN110.CAPE_ATEQUILIBRIUM]
                ),
            )
        else:
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
                pressure = find_p_from_phase_fraction(
                    state_temperature=state[0],
                    state_pressure=state[1],
                    overall_fractions=state[2:],
                    pcsaft_parameters=pcsaft_parameters,
                    kij_matrix=kij_matrix,
                    phasefraction=phaseFraction,
                )
            except RuntimeError as exc:
                return self.raise_cape_error(
                    error_cls=ecape_errors.ECapeSolvingError,
                    description="Failed to calculate from"
                    f" vapor phase fraction = {phaseFraction}: {exc}",
                    interfaceName="ICapeThermoEquilibriumRoutine",
                    operation="CalcEquilibrium",
                    moreInfo="Bubble/dew point calculation or the root finding on"
                    " the vapor phase fraction did not converge.",
                )
            logging.debug("IN CalcEquilibrium ---> Overall Pressure = %r", pressure)
            material.SetOverallProp("Pressure", None, self.r8_array_variant([pressure]))
            self.CalcEquilibrium(
                self.bstr_array_variant(["Temperature", "none", "Overall"]),
                self.bstr_array_variant(["Pressure", "none", "Overall"]),
                "Unspecified",
            )
        return 0

    def _pphasefraction_equilibrium_logic(
        self,
        pcsaft_parameters: List[List[float]],
        kij_matrix: List[List[float]],
        overall_temperature: float,
        overall_pressure: float,
        overall_fractions: List[float],
        material: CAPEOPEN110.ICapeThermoMaterial,
    ):
        state = [overall_temperature, overall_pressure, *overall_fractions]
        phaseFraction = _snap_phase_fraction(
            material.GetSinglePhaseProp("phaseFraction", "Vapor", "Mole", None)[0]
        )
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
            try:
                temperature = compute_bp_or_dp(
                    prop=prop,
                    pcsaft_parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=kij_matrix,
                )
                incipient_fractions = compute_incipient_fracs(
                    prop=prop,
                    pcsaft_parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=kij_matrix,
                )
            except RuntimeError as exc:
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeSolvingError,
                    description=f"BP/DP calculation failed: {exc}",
                    interfaceName="ICapeThermoEquilibriumRoutine",
                    operation="CalcEquilibrium",
                )
            logging.debug("IN CalcEquilibrium --->%r = %r", prop, temperature)
            material.SetOverallProp(
                "Temperature", None, self.r8_array_variant([temperature])
            )
            self._set_equilibrium_for_stable_phase(
                temperature=temperature,
                pressure=overall_pressure,
                fractions_at_phase=overall_fractions,
                phase_label="Vapor",
            )
            self._set_incipient_phase(
                temperature=temperature,
                pressure=overall_pressure,
                fractions_at_phase=incipient_fractions,
                phase_label="Liquid",
            )
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [CAPEOPEN110.CAPE_ATEQUILIBRIUM, CAPEOPEN110.CAPE_ATEQUILIBRIUM]
                ),
            )
        elif phaseFraction == 0.0:
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
            try:
                temperature = compute_bp_or_dp(
                    prop=prop,
                    pcsaft_parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=kij_matrix,
                )
                incipient_fractions = compute_incipient_fracs(
                    prop=prop,
                    pcsaft_parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=kij_matrix,
                )
            except RuntimeError as exc:
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeSolvingError,
                    description=f"BP/DP calculation failed: {exc}",
                    interfaceName="ICapeThermoEquilibriumRoutine",
                    operation="CalcEquilibrium",
                )
            logging.debug("IN CalcEquilibrium --->%r = %r", prop, temperature)
            material.SetOverallProp(
                "Temperature", None, self.r8_array_variant([temperature])
            )
            self._set_equilibrium_for_stable_phase(
                temperature=temperature,
                pressure=overall_pressure,
                fractions_at_phase=overall_fractions,
                phase_label="Liquid",
            )
            self._set_incipient_phase(
                temperature=temperature,
                pressure=overall_pressure,
                fractions_at_phase=incipient_fractions,
                phase_label="Vapor",
            )
            material.SetPresentPhases(
                self.bstr_array_variant(["Vapor", "Liquid"]),
                self.i4_array_variant(
                    [CAPEOPEN110.CAPE_ATEQUILIBRIUM, CAPEOPEN110.CAPE_ATEQUILIBRIUM]
                ),
            )
        else:
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
                temperature = find_t_from_phase_fraction(
                    state_temperature=state[0],
                    state_pressure=state[1],
                    overall_fractions=state[2:],
                    pcsaft_parameters=pcsaft_parameters,
                    kij_matrix=kij_matrix,
                    phasefraction=phaseFraction,
                )
            except RuntimeError as exc:
                return self.raise_cape_error(
                    error_cls=ecape_errors.ECapeSolvingError,
                    description="Failed to calculate from"
                    f" vapor phase fraction = {phaseFraction}: {exc}",
                    interfaceName="ICapeThermoEquilibriumRoutine",
                    operation="CalcEquilibrium",
                    moreInfo="Bubble/dew point calculation or the root finding on"
                    " the vapor phase fraction did not converge.",
                )
            logging.debug(
                "IN CalcEquilibrium ---> Overall Temperature = %r", temperature
            )
            material.SetOverallProp(
                "Temperature", None, self.r8_array_variant([temperature])
            )
            self.CalcEquilibrium(
                self.bstr_array_variant(["Temperature", "none", "Overall"]),
                self.bstr_array_variant(["Pressure", "none", "Overall"]),
                "Unspecified",
            )
        return 0

    def _penthalpy_equilibrium_logic(
        self,
        pcsaft_parameters: List[List[float]],
        kij_matrix: List[List[float]],
        overall_temperature: float,
        overall_pressure: float,
        overall_fractions: List[float],
        material: CAPEOPEN110.ICapeThermoMaterial,
    ):
        overall_enthalpy = material.GetOverallProp("enthalpy", "Mole", [])[0]
        logging.debug("IN CalcEquilibrium ---> enthalpy = %r", overall_enthalpy)
        updated_temperature = solve_enthalpy(
            h=overall_enthalpy,
            init_temp=overall_temperature,
            pressure=overall_pressure,
            fractions=overall_fractions,
            parameters=pcsaft_parameters,
            kij_matrix=kij_matrix,
        )
        logging.debug(
            "IN CalcEquilibrium ---> updated temperature = %r", updated_temperature
        )
        material.SetOverallProp(
            "Temperature", None, self.r8_array_variant([updated_temperature])
        )
        self.CalcEquilibrium(
            self.bstr_array_variant(["Temperature", "none", "Overall"]),
            self.bstr_array_variant(["Pressure", "none", "Overall"]),
            "Unspecified",
        )
        return 0


def _is_liquid_like(state, z_max=0.2) -> bool:
    z = state.compressibility()
    return z < z_max


def _snap_phase_fraction(fv: float) -> float:
    if fv >= 1.0 - _FV_SNAP:
        return 1.0
    if fv <= _FV_SNAP:
        return 0.0
    return fv
