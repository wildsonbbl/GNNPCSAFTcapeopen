"ICapeThermoCompounds"


class ICapeThermoCompounds:

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

    def ICapeThermoCompounds_GetCompoundList(self):
        """
        Returns the list of all Compounds, with identifiers and additional
        identifying information.

        Returns (all ACTUALLYout, CapeArrayString/CapeArrayDouble):
            compIds, formulae, names, boilTemps, molwts, casnos

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: montar a lista de compostos suportados aqui...

    def ICapeThermoCompounds_GetConstPropList(self):
        """
        Returns the list of supported constant Physical Properties (i.e.
        those retrievable via GetCompoundConstant).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: listar as propriedades constantes suportadas aqui...

    def ICapeThermoCompounds_GetNumCompounds(self):
        """
        Returns the number of Compounds supported.

        Returns:
            num (CapeLong)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: retornar o número de compostos suportados aqui...

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

    def ICapeThermoCompounds_GetPDependentPropList(self):
        """
        Returns the list of supported pressure-dependent properties (i.e.
        those retrievable via GetPDependentProperty).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: listar as propriedades dependentes de pressão suportadas aqui...

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

    def ICapeThermoCompounds_GetTDependentPropList(self):
        """
        Returns the list of supported temperature-dependent properties (i.e.
        those retrievable via GetTDependentProperty).

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown, ECapeBadInvOrder.
        """
        # TODO: listar as propriedades dependentes de temperatura suportadas aqui...
