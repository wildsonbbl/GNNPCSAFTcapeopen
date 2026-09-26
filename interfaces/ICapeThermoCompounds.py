"ICapeThermoCompounds"

import copy
import logging
from typing import List

from comtypes.gen import CAPEOPEN110
from gnnepcsaft.pcsaft.feos import (
    critical_points_feos,
    pure_den_feos,
    pure_h_lv_feos,
    pure_vp_feos,
)

from . import ecape_errors
from .utils_common import GNNPCSAFTPPbase, OutboundVARIANT

_CONST_PROPS = [
    "molecularWeight",
    "SMILESformula",
    "criticalDensity",
    "criticalPressure",
    "criticalTemperature",
    "heatOfVaporizationAtNormalBoilingPoint",
    "liquidDensityAt25C",
    "normalBoilingPoint",
]

T_PROP_LIST = [
    "heatCapacityOfLiquid",
    "heatOfVaporization",
    "vaporPressure",
    "volumeOfLiquid",
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
        co_props = copy.copy(props.value)
        co_compIds = copy.copy(list(compIds.value))

        requested_props = [str(p) for p in self._as_list(co_props)]
        logging.debug("IN GetCompoundConstant ---> requesting %r", (props, compIds))
        indices = self._compound_indices(co_compIds)
        pcsaft_parameters = copy.copy(self.pcsaft_parameters)
        assert pcsaft_parameters is not None
        _propvals = []
        for prop in requested_props:
            key = prop.strip()
            for idx in indices:
                if key == "molecularWeight":
                    _propvals.append(pcsaft_parameters[idx][8])
                if key == "SMILESformula":
                    _propvals.append(co_compIds[idx])
                if key in (
                    "criticalDensity",
                    "criticalPressure",
                    "criticalTemperature",
                ):
                    tc, pc, dc = critical_points_feos(pcsaft_parameters[idx])
                    if key == "criticalDensity":
                        _propvals.append(dc)
                    if key == "criticalPressure":
                        _propvals.append(pc)
                    if key == "criticalTemperature":
                        _propvals.append(tc)
                if key == "heatOfVaporizationAtNormalBoilingPoint":
                    _propvals.append(
                        pure_h_lv_feos(
                            pcsaft_parameters[idx],
                            [298.15],
                        )
                        * 1000.0
                    )
                if key == "liquidDensityAt25C":
                    _propvals.append(
                        pure_den_feos(pcsaft_parameters[idx], [298.15, 101325.0])
                    )
                if key == "normalBoilingPoint":
                    _propvals.append(pure_vp_feos(pcsaft_parameters[idx], [298.15]))
                if key not in _CONST_PROPS:
                    self.raise_cape_error(
                        error_cls=ecape_errors.ECapeThrmPropertyNotAvailable,
                        description=(
                            f"Requested compound constant ({key}) are not available;"
                            f" only {_CONST_PROPS} are supported by this Property Package"
                        ),
                        interfaceName="ICapeThermoCompounds",
                        operation="GetCompoundConstant",
                    )
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
        pcsaft_parameters = copy.copy(self.pcsaft_parameters)
        assert pcsaft_parameters is not None

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
        co_props = copy.copy(props.value)
        co_compIds = copy.copy(compIds.value)

        requested_props = [str(p) for p in self._as_list(co_props)]
        indices = self._compound_indices(co_compIds)
        pcsaft_parameters = copy.copy(self.pcsaft_parameters)
        assert pcsaft_parameters is not None
        _propvals: List[float] = []
        for prop in requested_props:
            key = prop.strip()
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
                if key in (
                    "heatCapacityOfLiquid",
                    "heatOfVaporization",
                ):
                    h_lv = (
                        pure_h_lv_feos(pcsaft_parameters[idx], [temperature]) * 1000.0
                    )
                    if key == "heatCapacityOfLiquid":
                        _propvals.append(h_lv / temperature)
                    else:
                        _propvals.append(h_lv)
                logging.debug("IN TDependetProperty ---> %r = %r", key, _propvals)
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
