"ICapeThermoCompounds"

import copy
import logging
import math
from typing import List

import si_units as si
from comtypes.gen import CAPEOPEN110
from feos import Contributions  # pyright: ignore[reportAttributeAccessIssue]
from feos import PhaseEquilibrium  # pyright: ignore[reportAttributeAccessIssue]
from gnnepcsaft.pcsaft.feos.pure import (
    critical_points_feos,
    pc_saft,
    pure_den_feos,
    pure_h_lv_feos,
    pure_surface_tension_at_t_feos,
    pure_vle_at_p_feos,
    pure_vle_at_t_feos,
    pure_vp_feos,
)

from . import ecape_errors
from .utils_common import GNNPCSAFTPPbase, OutboundVARIANT

_CONST_PROPS = [
    "molecularWeight",
    "SMILESformula",
    "criticalCompressibilityFactor",
    "criticalDensity",
    "criticalVolume",
    "criticalPressure",
    "criticalTemperature",
    "heatOfVaporizationAtNormalBoilingPoint",
    "liquidDensityAt25C",
    "liquidVolumeAt25C",
    "normalBoilingPoint",
]

T_PROP_LIST = [
    "heatCapacityOfLiquid",
    "heatOfVaporization",
    "vaporPressure",
    "volumeOfLiquid",
    "fugacityCoefficientOfVapor",
    "volumeChangeUponVaporization",
    "surfaceTensionSatLiquid",
]


class ICapeThermoCompounds(GNNPCSAFTPPbase, CAPEOPEN110.ICapeThermoCompounds):
    "ICapeThermoCompounds Class with methods implemented"

    # --- ICapeThermoCompounds ---
    def GetCompoundConstant(self, props, compIds):
        """
        Returns the values of constant Physical Properties for the specified
        Compounds.

        Args:
            props (CapeArrayString): list of constant Physical Property
                identifiers (section 7.5.2).
            compIds (CapeArrayString): list of Compound identifiers, or
                UNDEFINED for all Compounds.

        Returns:
            propvals (CapeArrayVariant): C*P values -- the first C values
                are for the first requested property (one per Compound),
                then C values for the second property, and so on.

        Raises (per spec): ECapeNoImpl, ECapeThrmPropertyNotAvailable,
            ECapeLimitedImpl, ECapeInvalidArgument, ECapeUnknown,
            ECapeBadInvOrder.
        """
        co_props = copy.deepcopy(props.value)
        co_compIds = copy.deepcopy(list(compIds.value))

        requested_props = [str(p) for p in self._as_list(co_props)]
        logging.debug("IN GetCompoundConstant ---> requesting %r", (props, compIds))
        indices = self._compound_indices(co_compIds)
        pcsaft_parameters = copy.deepcopy(self.pcsaft_parameters)
        components_smiles = copy.deepcopy(self.components_smiles)
        assert pcsaft_parameters is not None
        assert components_smiles is not None
        _propvals = []
        for prop in requested_props:
            key = prop.strip()
            if key not in _CONST_PROPS:
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeLimitedImpl,
                    description=(
                        f"Requested compound constant ({key}) is not available;"
                        f" only {_CONST_PROPS} are supported by this Property Package"
                    ),
                    interfaceName="ICapeThermoCompounds",
                    operation="GetCompoundConstant",
                )
            for idx in indices:
                val = self._get_compound_constant_value(
                    key, idx, pcsaft_parameters, components_smiles
                )
                _propvals.append(val)
                logging.debug("IN GetCompoundConstant ---> %r = %r", key, _propvals)
        return OutboundVARIANT(_propvals)

    def GetCompoundList(self, compIds, formulae, names, boilTemps, molwts, casnos):
        """
        Returns the list of all Compounds, with identifiers and additional
        identifying information.

        Returns (all ACTUALLYout, CapeArrayString/CapeArrayDouble):
            compIds, formulae, names, boilTemps, molwts, casnos

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        self._require_components(
            interfaceName="ICapeThermoCompounds",
            operation="GetCompoundList",
        )
        pcsaft_parameters = copy.deepcopy(self.pcsaft_parameters)
        assert pcsaft_parameters is not None
        assert self.components_smiles is not None

        return (
            self.bstr_array_variant(self.components_smiles),
            self.bstr_array_variant([""] * len(self.components_smiles)),
            self.bstr_array_variant(self.components_smiles),
            self.r8_array_variant([float("nan")] * len(self.components_smiles)),
            self.r8_array_variant([parameters[8] for parameters in pcsaft_parameters]),
            self.bstr_array_variant([""] * len(self.components_smiles)),
        )

    def GetConstPropList(self):
        """
        Returns the list of supported constant Physical Properties (i.e.
        those retrievable via GetCompoundConstant).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        self._require_components(
            interfaceName="ICapeThermoCompounds",
            operation="GetConstPropList",
        )
        return self.bstr_array_variant(_CONST_PROPS)

    def GetNumCompounds(self):
        """
        Returns the number of Compounds supported.

        Returns:
            num (CapeLong)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        self._require_components(
            interfaceName="ICapeThermoCompounds",
            operation="GetNumCompounds",
        )
        assert self.components_smiles is not None
        return len(self.components_smiles)

    def GetPDependentProperty(self, props, pressure, compIds, propVals):
        """
        Returns the values of pressure-dependent Physical Properties for the
        specified pure Compounds.

        Args:
            props (CapeArrayString): pressure-dependent property identifiers
                (section 7.5.4).
            pressure (CapeDouble): pressure (Pa) at which to evaluate.
            compIds (CapeArrayString): Compound identifiers, or UNDEFINED
                for all Compounds.

        Returns:
            propvals (CapeArrayDouble): C*P values, ordered property-major.

        Raises (per spec): ECapeNoImpl, ECapeLimitedImpl,
            ECapeInvalidArgument, ECapeOutOfBounds,
            ECapeThrmPropertyNotAvailable, ECapeUnknown, ECapeBadInvOrder.
        """

    def GetPDependentPropList(self):
        """
        Returns the list of supported pressure-dependent properties (i.e.
        those retrievable via GetPDependentProperty).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        return self.empty_array_variant()

    def GetTDependentProperty(self, props, temperature, compIds, propVals):
        """
        Returns the values of temperature-dependent Physical Properties for
        the specified pure Compounds.

        Args:
            props (CapeArrayString): temperature-dependent property
                identifiers (section 7.5.3).
            temperature (CapeDouble): temperature (K) at which to evaluate.
            compIds (CapeArrayString): Compound identifiers, or UNDEFINED
                for all Compounds.

        Returns:
            propvals (CapeArrayDouble): C*P values, ordered property-major.

        Raises (per spec): ECapeNoImpl, ECapeLimitedImpl,
            ECapeInvalidArgument, ECapeOutOfBounds,
            ECapeThrmPropertyNotAvailable, ECapeUnknown, ECapeBadInvOrder.
        """
        co_props = copy.deepcopy(props.value)
        co_compIds = copy.deepcopy(compIds.value)

        requested_props = [str(p) for p in self._as_list(co_props)]
        indices = self._compound_indices(co_compIds)
        pcsaft_parameters = copy.deepcopy(self.pcsaft_parameters)
        assert pcsaft_parameters is not None
        _propvals: List[float] = []
        for prop in requested_props:
            key = prop.strip()
            if key not in T_PROP_LIST:
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeLimitedImpl,
                    description=(
                        f"Requested temperature-dependent property ({key}) is not available;"
                        f" only {T_PROP_LIST} are supported by this Property Package"
                    ),
                    interfaceName="ICapeThermoCompounds",
                    operation="GetTDependentProperty",
                )
            for idx in indices:
                if key == "vaporPressure":
                    _propvals.append(
                        pure_vp_feos(pcsaft_parameters[idx], [temperature])
                    )
                if key == "volumeOfLiquid":
                    vp = pure_vp_feos(pcsaft_parameters[idx], [temperature])
                    _propvals.append(
                        1 / pure_den_feos(pcsaft_parameters[idx], [temperature, vp])
                    )
                if key == "heatOfVaporization":
                    h_lv = (
                        pure_h_lv_feos(pcsaft_parameters[idx], [temperature]) * 1000.0
                    )
                    _propvals.append(h_lv)

                if key == "heatCapacityOfLiquid":
                    vle = pure_vle_at_t_feos(
                        parameters=pcsaft_parameters[idx], temperature=temperature
                    )
                    cp = vle.liquid.molar_isobaric_heat_capacity(
                        Contributions.Residual
                    ) / (si.JOULE / si.MOL / si.KELVIN)
                    _propvals.append(cp)
                if key == "fugacityCoefficientOfVapor":
                    vle = pure_vle_at_t_feos(
                        parameters=pcsaft_parameters[idx], temperature=temperature
                    )
                    ln_phi = vle.vapor.ln_phi()
                    _propvals.append(math.exp(ln_phi[0]))
                if key == "volumeChangeUponVaporization":
                    vle = pure_vle_at_t_feos(
                        parameters=pcsaft_parameters[idx], temperature=temperature
                    )
                    volume_vapor = 1 / vle.vapor.density / (si.METER**3 / si.MOL)
                    volume_liquid = 1 / vle.liquid.density / (si.METER**3 / si.MOL)
                    _propvals.append(volume_vapor - volume_liquid)
                if key == "surfaceTensionSatLiquid":
                    st = (
                        pure_surface_tension_at_t_feos(
                            parameters=pcsaft_parameters[idx], temperature=temperature
                        )
                        * 1e-3
                    )
                    _propvals.append(st)

                logging.debug("IN GetTDependentProperty ---> %r = %r", key, _propvals)
        return self.r8_array_variant(_propvals)

    def GetTDependentPropList(self):
        """
        Returns the list of supported temperature-dependent properties (i.e.
        those retrievable via GetTDependentProperty).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        return self.bstr_array_variant(T_PROP_LIST)

    def _compound_indices(self, compIds):
        assert self.components_smiles is not None
        if compIds is None:
            return list(range(len(self.components_smiles)))
        lower_names = [n.lower() for n in self.components_smiles]
        indices = []
        for cid in self._as_list(compIds):
            try:
                indices.append(lower_names.index(str(cid).lower()))
            except ValueError:
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeInvalidArgument,
                    description=f"Unrecognised compound identifier: {cid!r}",
                    interfaceName="ICapeThermoCompounds",
                    operation="GetTDependentPropList",
                )
        return indices

    def _get_critical_property(self, key, parameter):
        """Helper to compute critical properties."""
        tc, pc, dc = critical_points_feos(parameter)
        if key == "criticalDensity":
            return dc
        if key == "criticalPressure":
            return pc
        if key == "criticalTemperature":
            return tc
        if key == "criticalVolume":
            return 1 / dc
        if key == "criticalCompressibilityFactor":
            return (
                pc
                * (1 / dc)
                / (si.RGAS / ((si.PASCAL * si.METER**3) / (si.KELVIN * si.MOL)) * tc)
            )
        return None

    def _get_compound_constant_value(
        self, key, idx, pcsaft_parameters, components_smiles
    ):
        """
        Helper to get a single compound constant value to reduce branch
        complexity in GetCompoundConstant.
        """
        if key == "molecularWeight":
            return pcsaft_parameters[idx][8]
        if key == "SMILESformula":
            return components_smiles[idx]
        if key in (
            "criticalDensity",
            "criticalVolume",
            "criticalPressure",
            "criticalTemperature",
            "criticalCompressibilityFactor",
        ):
            return self._get_critical_property(key, pcsaft_parameters[idx])
        if key == "heatOfVaporizationAtNormalBoilingPoint":
            vle = pure_vle_at_p_feos(
                parameters=pcsaft_parameters[idx], pressure=101325.0
            )
            return (
                vle.vapor.molar_enthalpy(Contributions.Residual)
                - vle.liquid.molar_enthalpy(Contributions.Residual)
            ) / (si.JOULE / si.MOL)
        if key == "liquidDensityAt25C":
            return pure_den_feos(pcsaft_parameters[idx], [298.15, 101325.0])
        if key == "liquidVolumeAt25C":
            return 1 / pure_den_feos(pcsaft_parameters[idx], [298.15, 101325.0])
        if key == "normalBoilingPoint":
            return (
                PhaseEquilibrium.boiling_temperature(
                    pc_saft(parameters=pcsaft_parameters[idx]),
                    101325.0 * si.PASCAL,
                )[0]
                / si.KELVIN
            )
        return None
