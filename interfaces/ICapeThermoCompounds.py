"ICapeThermoCompounds"

import copy
from typing import List

from comtypes.safearray import safearray_as_ndarray

from . import ecape_errors
from .utils_common import GNNPCSAFTPPbase


class ICapeThermoCompounds(GNNPCSAFTPPbase):
    "ICapeThermoCompounds Class with methods implemented"

    # --- ICapeThermoCompounds ---
    def ICapeThermoCompounds_GetCompoundConstant(self, props, compIds):
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
        # TODO: buscar/calcular as constantes dos compostos aqui...

        with safearray_as_ndarray:
            props = copy.copy(props.value)
            compIds = copy.copy(compIds.value)

        requested_props = [str(p) for p in self._as_list(props)]
        indices = self._compound_indices(compIds)
        pcsaft_parameters = copy.copy(self.pcsaft_parameters)
        propvals: List[float] = []
        for prop in requested_props:
            key = prop.strip().lower()
            for idx in indices:
                if (key == "molecularweight") and (pcsaft_parameters is not None):
                    propvals.append(pcsaft_parameters[idx][8])
                else:

                    self.raise_cape_error(
                        error_cls=ecape_errors.ECapeThrmPropertyNotAvailable,
                        description=(
                            f"Requested compound constant ({key}) are not available;"
                            " only 'molecularWeight' is supported by this Property Package"
                        ),
                        interfaceName="ICapeThermoCompounds",
                        operation="GetCompoundConstant",
                    )
        return propvals

    def ICapeThermoCompounds_GetCompoundList(
        self, _compIds, _formulae, _names, _boilTemps, _molwts, _casnos
    ):
        """
        Returns the list of all Compounds, with identifiers and additional
        identifying information.

        Returns (all ACTUALLYout, CapeArrayString/CapeArrayDouble):
            compIds, formulae, names, boilTemps, molwts, casnos

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: set up formulae, boiltemps and casnos...

        self._require_components(
            interfaceName="ICapeThermoCompounds",
            operation="GetCompoundList",
        )
        pcsaft_parameters = copy.copy(self.pcsaft_parameters)

        return (
            self.bstr_array_variant(self.components_smiles),
            self.bstr_array_variant([""] * len(self.components_smiles)),
            self.bstr_array_variant(self.components_smiles),
            self.r8_array_variant([float("nan")] * len(self.components_smiles)),
            self.r8_array_variant(
                [parameters[8] for parameters in pcsaft_parameters]
                if pcsaft_parameters is not None
                else [float("nan")] * len(self.components_smiles)
            ),
            self.bstr_array_variant([""] * len(self.components_smiles)),
        )

    def ICapeThermoCompounds_GetConstPropList(self):
        """
        Returns the list of supported constant Physical Properties (i.e.
        those retrievable via GetCompoundConstant).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: listar mais propriedades constantes suportadas aqui...
        self._require_components(
            interfaceName="ICapeThermoCompounds",
            operation="GetConstPropList",
        )
        return self.bstr_array_variant(["molecularWeight"])

    def ICapeThermoCompounds_GetNumCompounds(self):
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

    def ICapeThermoCompounds_GetPDependentProperty(
        self, props, pressure, compIds, propvals_ptr
    ):
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
        # TODO: calcular as propriedades dependentes de pressão aqui...

        with safearray_as_ndarray:
            _props = copy.copy(props.value)
            _compIds = copy.copy(compIds.value)

        _propvals = self.r8_array_variant([float("nan")] * len(_compIds) * len(_props))
        return _propvals

    def ICapeThermoCompounds_GetPDependentPropList(self):
        """
        Returns the list of supported pressure-dependent properties (i.e.
        those retrievable via GetPDependentProperty).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: listar as propriedades dependentes de pressão suportadas aqui...

        return self.bstr_array_variant(["UNDEFINED"])

    def ICapeThermoCompounds_GetTDependentProperty(
        self, props, temperature, compIds, propvals_ptr
    ):
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
        # TODO: calcular as propriedades dependentes de temperatura aqui...

        with safearray_as_ndarray:
            _props = copy.copy(props.value)
            _compIds = copy.copy(compIds.value)

        _propvals = self.r8_array_variant([float("nan")] * len(_compIds) * len(_props))
        return _propvals

    def ICapeThermoCompounds_GetTDependentPropList(self):
        """
        Returns the list of supported temperature-dependent properties (i.e.
        those retrievable via GetTDependentProperty).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: listar as propriedades dependentes de temperatura suportadas aqui...

        return self.bstr_array_variant(["UNDEFINED"])

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
