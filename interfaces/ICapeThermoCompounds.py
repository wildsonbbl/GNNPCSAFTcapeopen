"ICapeThermoCompounds"

from typing import List

from .ICapeExceptions import (
    ECapeInvalidArgument,
    ECapeThrmPropertyNotAvailable,
)
from .utils_common import _require_components, bstr_array_variant, r8_array_variant


class ICapeThermoCompounds:
    "ICapeThermoCompounds Class with methods implemented"

    components_smiles: List[str]
    pcsaft_parameters: List[List[float]]
    _kij_matrix = List[List[float]]

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

        _require_components(self)
        requested_props = [str(p) for p in self._as_list(props)]
        indices = self._compound_indices(compIds)
        missing = False
        propvals: List[float] = []
        for prop in requested_props:
            key = prop.strip().lower()
            for idx in indices:
                if key == "molecularweight":
                    propvals.append(self.pcsaft_parameters[idx][8])
                else:
                    propvals.append(float("nan"))
                    missing = True
        if missing:
            # Still return what we have, but flag it as CAPE-OPEN requires.
            raise ECapeThrmPropertyNotAvailable(
                "One or more requested compound constants are not available;"
                " only 'molecularWeight' is supported by this Property Package"
            )
        return propvals

    def ICapeThermoCompounds_GetCompoundList(
        self, compIds, formulae, names, boilTemps, molwts, casnos
    ):
        """
        Returns the list of all Compounds, with identifiers and additional
        identifying information.

        Returns (all ACTUALLYout, CapeArrayString/CapeArrayDouble):
            compIds, formulae, names, boilTemps, molwts, casnos

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: set up formulae, boiltemps and casnos...

        _require_components(self)

        compIds, formulae, names, boilTemps, molwts, casnos = (
            bstr_array_variant(self.components_smiles),
            bstr_array_variant(["UNDEFINED"] * len(self.components_smiles)),
            bstr_array_variant(self.components_smiles),
            r8_array_variant([float("nan")] * len(self.components_smiles)),
            r8_array_variant([parameters[8] for parameters in self.pcsaft_parameters]),
            bstr_array_variant(["UNDEFINED"] * len(self.components_smiles)),
        )

        return compIds, formulae, names, boilTemps, molwts, casnos

    def ICapeThermoCompounds_GetConstPropList(self):
        """
        Returns the list of supported constant Physical Properties (i.e.
        those retrievable via GetCompoundConstant).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: listar mais propriedades constantes suportadas aqui...
        _require_components(self)
        return bstr_array_variant(["molecularWeight"])

    def ICapeThermoCompounds_GetNumCompounds(self):
        """
        Returns the number of Compounds supported.

        Returns:
            num (CapeLong)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        _require_components(self)
        return len(self.components_smiles)

    def ICapeThermoCompounds_GetPDependentProperty(self, props, pressure, compIds):
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

        return r8_array_variant(
            [float("nan")] * len(self.components_smiles * len(props))
        )

    def ICapeThermoCompounds_GetPDependentPropList(self):
        """
        Returns the list of supported pressure-dependent properties (i.e.
        those retrievable via GetPDependentProperty).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: listar as propriedades dependentes de pressão suportadas aqui...

        return bstr_array_variant(["UNDEFINED"])

    def ICapeThermoCompounds_GetTDependentProperty(self, props, temperature, compIds):
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
        return r8_array_variant(
            [float("nan")] * len(self.components_smiles * len(props))
        )

    def ICapeThermoCompounds_GetTDependentPropList(self):
        """
        Returns the list of supported temperature-dependent properties (i.e.
        those retrievable via GetTDependentProperty).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: listar as propriedades dependentes de temperatura suportadas aqui...

        return bstr_array_variant(["UNDEFINED"])

    def _compound_indices(self, compIds):
        if compIds is None:
            return list(range(len(self.components_smiles)))
        lower_names = [n.lower() for n in self.components_smiles]
        indices = []
        for cid in self._as_list(compIds):
            try:
                indices.append(lower_names.index(str(cid).lower()))
            except ValueError as exc:
                raise ECapeInvalidArgument(
                    f"Unrecognised compound identifier: {cid!r}"
                ) from exc
        return indices

    @staticmethod
    def _as_list(value):
        if value is None:
            return []
        return list(value) if isinstance(value, (list, tuple)) else [value]
