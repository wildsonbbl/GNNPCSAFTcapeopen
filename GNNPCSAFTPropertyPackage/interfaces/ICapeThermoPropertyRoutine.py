"ICapeThermoPropertyRoutine"

import copy
import logging
from typing import List

import numpy as np
import si_units as si
from comtypes.gen import CAPEOPEN110
from feos import Contributions  # pyright: ignore[reportAttributeAccessIssue]
from gnnepcsaft.pcsaft.feos.mixture import (
    mix_den_feos,
    mix_r_enthalpy_feos,
    mix_r_entropy_feos,
    mix_r_isobaric_heat_capacity_feos,
    state_npt_feos,
)
from gnnepcsaft.pcsaft.pcsaft_feos import (
    mix_ln_activity_coefficient,
    mix_ln_fugacity_coefficient,
)

from . import ecape_errors
from .utils_common import GNNPCSAFTPPbase

_SINGLE_PHASE_PROPS = (
    "activityCoefficient",
    "density",
    "logFugacityCoefficient",
    "molecularWeight",
    "enthalpy",
    "entropy",
    "compressibility",
    "compressibilityFactor",
    "Density",
    "Enthalpy",
    "Entropy",
    "heatCapacityCp",
    "heatCapacityCv",
)
_SINGLE_PHASE_PROPS_MOLE = (
    "density",
    "enthalpy",
    "entropy",
    "Density",
    "Enthalpy",
    "Entropy",
    "heatCapacityCp",
    "heatCapacityCv",
)
_TWO_PHASE_PROPS = ("kvalue", "logkvalue")
_PHASE_LABELS = ("Liquid", "Vapor", "Liquid 2")

# eCapeCalculationCode flags used by CalcAndGetLnPhi's fFlags argument
CAPE_NO_CALCULATION = 0
CAPE_LOG_FUGACITY_COEFFICIENTS = 1
CAPE_T_DERIVATIVE = 2
CAPE_P_DERIVATIVE = 4
CAPE_MOLE_NUMBERS_DERIVATIVES = 8


class ICapeThermoPropertyRoutine(
    GNNPCSAFTPPbase, CAPEOPEN110.ICapeThermoPropertyRoutine
):
    "ICapeThermoPropertyRoutine Class with methods implemented"

    # --- ICapeThermoPropertyRoutine ---
    def CalcAndGetLnPhi(
        self,
        phaseLabel,
        temperature,
        pressure,
        moleNumbers,
        fFlags,
        lnPhi,
        lnPhiDT,
        lnPhiDP,
        lnPhiDn,
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
        pcsaft_parameters = copy.deepcopy(self.pcsaft_parameters)
        _kij_matrix = copy.deepcopy(self._kij_matrix)
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
        if 0.0 == sum(fractions):
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeFailedInitialisation,
                description=f"Phase fractions wrongly set to {fractions}",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcAndGetLnPhi",
            )
        state = [float(temperature), float(pressure), *fractions]
        ln_phi = mix_ln_fugacity_coefficient(pcsaft_parameters, state, _kij_matrix)
        return (
            self.r8_array_variant(ln_phi),
            self.empty_array_variant(),
            self.empty_array_variant(),
            self.empty_array_variant(),
        )

    def CalcSinglePhaseProp(self, props, phaseLabel):
        """Calculates properties/derivatives that depend on one phase.

        COMMETHOD(
                [dispid(2), helpstring('method CalcSinglePhaseProp')],
                HRESULT,
                'CalcSinglePhaseProp',
                (['in'], VARIANT, 'props'),
                (['in'], BSTR, 'phaseLabel')
            )


        """
        _co_properties = self._as_list(props.value)
        for prop in _co_properties:
            if not self.CheckSinglePhasePropSpec(property=prop, phaseLabel=phaseLabel):
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeLimitedImpl,
                    description="Unsupported single-phase"
                    f" property ---> {prop} <---"
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

        temperature, pressure, fractions = self._get_tp_fraction(phaseLabel)
        if 0.0 == sum(fractions):
            return 0
        state = [temperature, pressure, *fractions]

        # Compute everything before writing anything back (a partial failure
        # must not leave partial results in the Material Object).
        computed = {}
        for prop in _co_properties:
            try:
                computed[prop] = self._compute_single_phase_property(
                    prop, state, phaseLabel
                )
            except Exception as exc:  # pylint:disable=broad-exception-caught
                logging.exception("IN CalcSinglePhaseProp ---> Exception", exc_info=exc)

        for prop, value in computed.items():
            logging.debug(
                "IN CalcSinglePhaseProp --->%r = %r for phaseLable = %r",
                prop,
                value,
                phaseLabel,
            )
            if prop in _SINGLE_PHASE_PROPS_MOLE:
                material.SetSinglePhaseProp(
                    prop, phaseLabel, "Mole", self.r8_array_variant(value)
                )
            else:
                material.SetSinglePhaseProp(
                    prop, phaseLabel, None, self.r8_array_variant(value)
                )
        rss_mb = self.rss_mb()
        logging.debug("PROCESS MEMORY: %r MB", rss_mb)
        return 0

    def CalcTwoPhaseProp(self, props, phaseLabels):
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
        pcsaft_parameters = copy.deepcopy(self.pcsaft_parameters)
        _kij_matrix = copy.deepcopy(self._kij_matrix)
        assert pcsaft_parameters is not None
        for prop in _co_properties:
            if not self.CheckTwoPhasePropSpec(property=prop, phaseLabels=phaseLabels):
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeLimitedImpl,
                    description=f"Unsupported two-phase"
                    f" property ---> {prop} <---"
                    f" with phaseLables ---> {_co_phase_labels} <---",
                    interfaceName="ICapeThermoPropertyRoutine",
                    operation="CalcTwoPhaseProp",
                )

        t1, p1, x1 = self._get_tp_fraction(_co_phase_labels[0])
        t2, p2, x2 = self._get_tp_fraction(_co_phase_labels[1])
        if abs(t1 - t2) > 1e-6 or abs(p1 - p2) > 1e-6:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeFailedInitialisation,
                description="CalcTwoPhaseProp requires both phases to share the same "
                "temperature and pressure",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcTwoPhaseProp",
            )
        if 0.0 == sum(x1) or 0.0 == sum(x2):
            return 0

        ln_phi_1 = mix_ln_fugacity_coefficient(
            pcsaft_parameters, [t1, p1, *x1], _kij_matrix
        )
        ln_phi_2 = mix_ln_fugacity_coefficient(
            pcsaft_parameters, [t1, p1, *x2], _kij_matrix
        )
        log_kvalue = np.asarray(ln_phi_2) - np.asarray(ln_phi_1)

        computed = {}
        for prop in _co_properties:
            if prop.lower() == "logkvalue":
                computed[prop] = log_kvalue.tolist()
            elif prop == "kvalue":
                computed[prop] = np.exp(log_kvalue).tolist()
        for prop, value in computed.items():
            logging.debug("IN CalcTwoPhaseProp ---> %r = %r", prop, value)
            material.SetTwoPhaseProp(
                prop,
                self.bstr_array_variant(_co_phase_labels),
                None,
                self.r8_array_variant(value),
            )
        rss_mb = self.rss_mb()
        logging.debug("PROCESS MEMORY: %r MB", rss_mb)
        return 0

    def CheckSinglePhasePropSpec(
        self, property, phaseLabel  # pylint: disable=redefined-builtin
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
        if property not in _SINGLE_PHASE_PROPS:
            return False
        self._require_phase_label(phaseLabel=phaseLabel)
        return True

    def CheckTwoPhasePropSpec(
        self, property, phaseLabels  # pylint: disable=redefined-builtin
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
        if len(_co_phase_labels) != 2:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeInvalidArgument,
                description="phaseLabels must contain exactly two labels",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcTwoPhaseProp",
            )
        if property not in _TWO_PHASE_PROPS:
            return False
        for label in _co_phase_labels:
            self._require_phase_label(label)
        return True

    def GetSinglePhasePropList(self):
        """
        Returns the list of supported non-constant single-phase properties
        (i.e. those calculable by CalcSinglePhaseProp), including derivatives.

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """
        return self.bstr_array_variant(list(_SINGLE_PHASE_PROPS))

    def GetTwoPhasePropList(self):
        """
        Returns the list of supported non-constant two-phase properties
        (i.e. those calculable by CalcTwoPhaseProp), including derivatives.

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """
        return self.bstr_array_variant(list(_TWO_PHASE_PROPS))

    def _compute_single_phase_property(
        self, prop: str, state: List[float], phaseLabel: str
    ) -> List[float]:
        pcsaft_parameters = copy.deepcopy(self.pcsaft_parameters)
        _kij_matrix = copy.deepcopy(self._kij_matrix)
        assert pcsaft_parameters is not None
        density_initialization = "vapor" if phaseLabel == "Vapor" else "liquid"
        logging.debug(
            "IN CalcSinglePhaseProp ---> requesting %r", (prop, state, phaseLabel)
        )

        if prop == "activityCoefficient":
            return np.exp(
                mix_ln_activity_coefficient(
                    parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=_kij_matrix,
                    density_initialization=density_initialization,
                )
            ).tolist()
        if prop.lower() == "density":
            return [
                mix_den_feos(
                    parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=_kij_matrix,
                    density_initialization=density_initialization,
                )
            ]
        if prop == "logFugacityCoefficient":
            return mix_ln_fugacity_coefficient(
                pcsaft_parameters,
                state,
                _kij_matrix,
                density_initialization=density_initialization,
            )
        if prop == "molecularWeight":
            return [
                sum(
                    frac * params[8]
                    for frac, params in zip(state[2:], pcsaft_parameters)
                )
            ]
        if prop.lower() == "enthalpy":
            return [
                mix_r_enthalpy_feos(
                    parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=_kij_matrix,
                    density_initialization=density_initialization,
                )
            ]
        if prop == "heatCapacityCp":
            return [
                mix_r_isobaric_heat_capacity_feos(
                    parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=_kij_matrix,
                    density_initialization=density_initialization,
                )
            ]
        if prop == "heatCapacityCv":
            state_npt = state_npt_feos(
                parameters=pcsaft_parameters,
                state=state,
                kij_matrix=_kij_matrix,
                density_initialization=density_initialization,
            )
            return [
                state_npt.molar_isochoric_heat_capacity(Contributions.Residual)
                / (si.JOULE / si.MOL / si.KELVIN)
            ]
        if prop.lower() == "entropy":
            return [
                mix_r_entropy_feos(
                    parameters=pcsaft_parameters,
                    state=state,
                    kij_matrix=_kij_matrix,
                    density_initialization=density_initialization,
                )
            ]
        if prop.lower() == "compressibility":
            state_npt = state_npt_feos(
                parameters=pcsaft_parameters,
                state=state,
                kij_matrix=_kij_matrix,
                density_initialization=density_initialization,
            )
            return [state_npt.isothermal_compressibility() / (1 / si.PASCAL)]
        if prop == "compressibilityFactor":
            state_npt = state_npt_feos(
                parameters=pcsaft_parameters,
                state=state,
                kij_matrix=_kij_matrix,
                density_initialization=density_initialization,
            )
            return [state_npt.compressibility()]

        return [float("nan")]

    def _require_phase_label(self, phaseLabel):
        if phaseLabel not in _PHASE_LABELS:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeInvalidArgument,
                description=f"Unrecognised phase label: {phaseLabel!r}",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcSinglePhaseProp/CalcTwoPhaseProp/CalcAndGetLnPhi",
                moreInfo="Only Liquid (1) OR Vapor (2) OR Liquid 2 (3) are valid",
            )
