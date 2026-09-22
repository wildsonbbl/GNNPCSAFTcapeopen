"ICapeThermoPropertyRoutine"

import copy
from typing import List

import numpy as np
from gnnepcsaft.pcsaft.pcsaft_feos import (
    mix_bp_at_fixed_pressure_feos,
    mix_den_feos,
    mix_dp_at_fixed_pressure_feos,
    mix_ln_activity_coefficient,
    mix_ln_fugacity_coefficient,
    mix_vp_feos,
)

from . import ecape_errors
from .utils_common import GNNPCSAFTPPbase

_SINGLE_PHASE_PROPS = (
    "activityCoefficient",
    "density",
    "logFugacityCoefficient",
    "molecularWeight",
    "dewPressure",
    "bubblePressure",
    "dewTemperature",
    "bubbleTemperature",
)
_SINGLE_PHASE_PROPS_MOLE = ("density",)
_TWO_PHASE_PROPS = ("kvalue", "logKvalue")
_PHASE_LABELS = ("1", "2")

# eCapeCalculationCode flags used by CalcAndGetLnPhi's fFlags argument
CAPE_NO_CALCULATION = 0
CAPE_LOG_FUGACITY_COEFFICIENTS = 1
CAPE_T_DERIVATIVE = 2
CAPE_P_DERIVATIVE = 4
CAPE_MOLE_NUMBERS_DERIVATIVES = 8


class ICapeThermoPropertyRoutine(GNNPCSAFTPPbase):
    "ICapeThermoPropertyRoutine Class with methods implemented"

    # --- ICapeThermoPropertyRoutine ---
    def ICapeThermoPropertyRoutine_CalcAndGetLnPhi(
        self,
        phaseLabel,
        temperature,
        pressure,
        moleNumbers,
        fFlags,
    ):
        """
        Calculates the natural logarithm of the fugacity coefficients (and
        optionally their T/P/mole-number derivatives) for a single-Phase
        mixture, from T/P/composition given directly as arguments (not
        pulled from the Material Object). Does not affect the state of the
        Material Object.

        Args:
            phaseLabel (CapeString): Phase label, one of GetPhaseList's
                values.
            temperature (CapeDouble): temperature (K).
            pressure (CapeDouble): pressure (Pa).
            moleNumbers (CapeArrayDouble): mole fractions of the Compounds
                (name is a historical misnomer -- these are fractions).
            fFlags (CapeInteger): eCapeCalculationCode bit flags selecting
                which of {value, dT, dP, dn} to compute.

        Returns (all ACTUALLYout, CapeArrayDouble):
            lnPhi, lnPhiDT, lnPhiDP, lnPhiDn

        Raises (per spec): ECapeNoImpl, ECapeLimitedImpl, ECapeBadInvOrder,
            ECapeFailedInitialisation, ECapeThrmPropertyNotAvailable,
            ECapeSolvingError, ECapeInvalidArgument, ECapeUnknown.
        """
        _moleNumbers = self._as_list(moleNumbers.value)

        self._require_components(
            interfaceName="ICapeThermoPropertyRoutine",
            operation="CalcAndGetLnPhi",
        )
        pcsaft_parameters = copy.copy(self.pcsaft_parameters)
        _kij_matrix = copy.copy(self._kij_matrix)
        assert pcsaft_parameters is not None

        self._require_phase_label(phaseLabel)
        if fFlags != CAPE_LOG_FUGACITY_COEFFICIENTS:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeLimitedImpl,
                description="Only the plain log-fugacity-coefficient calculation is "
                "implemented; T/P/mole-number derivatives are not available",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcAndGetLnPhi",
            )
        fractions = [float(v) for v in _moleNumbers]
        if len(fractions) != len(pcsaft_parameters):
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeInvalidArgument,
                description="moleNumbers must have one entry per configured compound",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcAndGetLnPhi",
            )
        state = [float(temperature), float(pressure), *fractions]
        ln_phi = mix_ln_fugacity_coefficient(pcsaft_parameters, state, _kij_matrix)
        return np.asarray(ln_phi).tolist()

    def ICapeThermoPropertyRoutine_CalcSinglePhaseProp(self, props, phaseLabel):
        """Calculates properties/derivatives that depend on one phase"""
        _co_properties = self._as_list(props.value)
        if any(
            not self.ICapeThermoPropertyRoutine_CheckSinglePhasePropSpec(
                co_property=prop, phaseLabel=phaseLabel
            )
            for prop in _co_properties
        ):
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeLimitedImpl,
                description="Unsupported single-phase"
                f" properties ---> {_co_properties} <---"
                f" with phaseLable ---> {phaseLabel} <---",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcSinglePhaseProp",
            )

        self._require_material(
            interfaceName="ICapeThermoPropertyRoutine",
            operation="CalcSinglePhaseProp",
        )
        assert self.material is not None
        material = self.material
        self._require_phase_label(phaseLabel)
        requested = [str(p) for p in _co_properties]
        unsupported = [p for p in requested if p not in _SINGLE_PHASE_PROPS]
        if unsupported:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeLimitedImpl,
                description=f"Unsupported single-phase"
                f" propert{'y' if len(unsupported)==1 else 'ies'}:"
                f" {', '.join(unsupported)}",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcSinglePhaseProp",
                moreInfo="GNNPCSAFT Property Package can't "
                "calculate these properties. Choose another Package",
            )

        temperature, pressure, fractions = self._get_tp_fraction(phaseLabel)
        state = [temperature, pressure, *fractions]

        # Compute everything before writing anything back (a partial failure
        # must not leave partial results in the Material Object).
        computed = {
            prop: self._compute_single_phase_property(prop, state) for prop in requested
        }
        for prop, value in computed.items():
            if prop in _SINGLE_PHASE_PROPS_MOLE:
                material.SetSinglePhaseProp(
                    prop, phaseLabel, "Mole", self.r8_array_variant(value)
                )
            else:
                material.SetSinglePhaseProp(
                    prop, phaseLabel, None, self.r8_array_variant(value)
                )
        return

    def ICapeThermoPropertyRoutine_CalcTwoPhaseProp(self, props, phaseLabels):
        """
        Calculates mixture properties/derivatives that depend on two Phases
        (e.g. surface tension, K-values) at the current T/P/composition of
        the Material Object. Does not perform an Equilibrium Calculation.

        Args:
            props (CapeArrayString): two-phase property identifiers
                (sections 7.5.6 and 7.6).
            phaseLabels (CapeArrayString): the two Phase labels, both from
                GetPhaseList and both present in the Material Object.

        Returns: -  (values are written back into the Material Object via
            SetTwoPhaseProp, not returned directly)

        Raises (per spec): ECapeNoImpl, ECapeLimitedImpl, ECapeBadInvOrder,
            ECapeFailedInitialisation, ECapeThrmPropertyNotAvailable,
            ECapeSolvingError, ECapeInvalidArgument, ECapeUnknown.
        """
        _co_properties = self._as_list(props.value)
        _co_phase_labels = self._as_list(phaseLabels.value)

        self._require_material(
            interfaceName="ICapeThermoPropertyRoutine",
            operation="CalcTwoPhaseProp",
        )
        assert self.material is not None
        material = self.material
        pcsaft_parameters = copy.copy(self.pcsaft_parameters)
        _kij_matrix = copy.copy(self._kij_matrix)
        assert pcsaft_parameters is not None

        labels = [str(l) for l in _co_phase_labels]
        if len(labels) != 2:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeInvalidArgument,
                description="phaseLabels must contain exactly two labels",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcTwoPhaseProp",
            )
        for label in labels:
            self._require_phase_label(label)
        requested = [str(p) for p in _co_properties]
        unsupported = [p for p in requested if p not in _TWO_PHASE_PROPS]
        if unsupported:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeLimitedImpl,
                description=f"Unsupported two-phase"
                f" propert{'y' if len(unsupported)==1 else 'ies'}:"
                f" {', '.join(unsupported)}",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcTwoPhaseProp",
                moreInfo="GNNPCSAFT Property Package can't "
                "calculate these properties. Choose another Package",
            )

        t1, p1, x1 = self._get_tp_fraction(labels[0])
        t2, p2, x2 = self._get_tp_fraction(labels[1])
        if abs(t1 - t2) > 1e-6 or abs(p1 - p2) > 1e-6:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeFailedInitialisation,
                description="CalcTwoPhaseProp requires both phases to share the same "
                "temperature and pressure",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcTwoPhaseProp",
            )

        ln_phi_1 = mix_ln_fugacity_coefficient(
            pcsaft_parameters, [t1, p1, *x1], _kij_matrix
        )
        ln_phi_2 = mix_ln_fugacity_coefficient(
            pcsaft_parameters, [t1, p1, *x2], _kij_matrix
        )
        log_kvalue = np.asarray(ln_phi_2) - np.asarray(ln_phi_1)

        computed = {}
        for prop in requested:
            if prop == "logKvalue":
                computed[prop] = log_kvalue.tolist()
            elif prop == "kvalue":
                computed[prop] = np.exp(log_kvalue).tolist()
        for prop, value in computed.items():
            material.SetTwoPhaseProp(prop, labels, "Mole", value)

    def ICapeThermoPropertyRoutine_CheckSinglePhasePropSpec(
        self, co_property, phaseLabel
    ):
        """
        Checks whether CalcSinglePhaseProp can calculate the given property
        for the given Phase. Depends only on this component's capabilities
        and configuration, not on any Material Object state.

        Args:
            property (CapeString): identifier to check, must be one of
                GetSinglePhasePropList's values to be valid.
            phaseLabel (CapeString): Phase label, must be one of
                GetPhaseList's values to be valid.

        Returns:
            valid (CapeBoolean)

        Raises (per spec): ECapeNoImpl, ECapeInvalidArgument, ECapeUnknown.
        """
        return co_property in _SINGLE_PHASE_PROPS and phaseLabel in _PHASE_LABELS

    def ICapeThermoPropertyRoutine_CheckTwoPhasePropSpec(
        self, co_property, phaseLabels
    ):
        """
        Checks whether CalcTwoPhaseProp can calculate the given property for
        the given pair of Phases. Depends only on this component's
        capabilities and configuration, not on any Material Object state.

        Args:
            co_property (CapeString): identifier to check, must be one of
                GetTwoPhasePropList's values to be valid.
            phaseLabels (CapeArrayString): the two Phase labels to check,
                must be from GetPhaseList's values.

        Returns:
            valid (CapeBoolean)

        Raises (per spec): ECapeNoImpl, ECapeInvalidArgument, ECapeUnknown.
        """
        _co_phase_labels = self._as_list(phaseLabels.value)
        return (
            str(co_property) in _TWO_PHASE_PROPS
            and len(_co_phase_labels) == 2
            and all(label in _PHASE_LABELS for label in _co_phase_labels)
        )

    def ICapeThermoPropertyRoutine_GetSinglePhasePropList(self):
        """
        Returns the list of supported non-constant single-phase properties
        (i.e. those calculable by CalcSinglePhaseProp), including derivatives.

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """
        return self.bstr_array_variant(list(_SINGLE_PHASE_PROPS))

    def ICapeThermoPropertyRoutine_GetTwoPhasePropList(self):
        """
        Returns the list of supported non-constant two-phase properties
        (i.e. those calculable by CalcTwoPhaseProp), including derivatives.

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """
        return self.bstr_array_variant(list(_TWO_PHASE_PROPS))

    def _compute_single_phase_property(self, prop, state) -> List[float]:
        pcsaft_parameters = copy.copy(self.pcsaft_parameters)
        _kij_matrix = copy.copy(self._kij_matrix)
        assert pcsaft_parameters is not None

        if prop == "activityCoefficient":
            return np.exp(
                mix_ln_activity_coefficient(
                    parameters=pcsaft_parameters, state=state, kij_matrix=_kij_matrix
                )
            ).tolist()
        if prop == "density":
            return [
                mix_den_feos(
                    parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=_kij_matrix,
                )
            ]
        if prop == "logFugacityCoefficient":
            return mix_ln_fugacity_coefficient(pcsaft_parameters, state, _kij_matrix)
        if prop == "molecularWeight":
            return [
                sum(
                    frac * params[8]
                    for frac, params in zip(state[1:], pcsaft_parameters)
                )
            ]
        if prop in ("dewPressure", "bubblePressure"):
            bp, dp = mix_vp_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=_kij_matrix
            )
            if prop == "bubblePressure":
                return [bp]
            return [dp]
        if prop == "dewTemperature":
            return [
                mix_dp_at_fixed_pressure_feos(
                    parameters=pcsaft_parameters, state=state, kij_matrix=_kij_matrix
                )
            ]
        if prop == "bubbleTemperature":
            return [
                mix_bp_at_fixed_pressure_feos(
                    parameters=pcsaft_parameters, state=state, kij_matrix=_kij_matrix
                )
            ]

        return []

    def _require_phase_label(self, phaseLabel):
        if phaseLabel not in _PHASE_LABELS:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeInvalidArgument,
                description=f"Unrecognised phase label: {phaseLabel!r}",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcSinglePhaseProp/CalcTwoPhaseProp/CalcAndGetLnPhi",
                moreInfo="Only Liquid (1) OR Vapor (2) are valid",
            )
