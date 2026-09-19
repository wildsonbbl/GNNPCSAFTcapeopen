"ICapeThermoPhases"


class ICapeThermoPhases:

    # --- ICapeThermoPhases ---
    def ICapeThermoPhases_GetNumPhases(self):
        """
        Returns the number of Phases supported.

        Returns:
            num (CapeLong)

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """
        # TODO: retornar o número de fases suportadas aqui...

    def ICapeThermoPhases_GetPhaseInfo(self, phaseLabel, phaseAttribute):
        """
        Returns information on an attribute associated with a Phase (e.g.
        StateOfAggregation, KeyCompoundId, ExcludedCompoundId,
        DensityDescription, UserDescription, TypeOfSolid).

        Args:
            phaseLabel (CapeString): a single Phase label, one of the
                values returned by GetPhaseList.
            phaseAttribute (CapeString): one of the Phase attribute
                identifiers defined in the spec.

        Returns:
            value (CapeVariant)

        Raises (per spec): ECapeNoImpl, ECapeInvalidArgument, ECapeUnknown.
        """
        # TODO: retornar o atributo solicitado da fase aqui...

    def ICapeThermoPhases_GetPhaseList(self):
        """
        Returns Phase labels and other important descriptive information for
        all the Phases supported.

        Returns (all ACTUALLYout, CapeArrayString):
            phaseLabels, stateOfAggregation, keyCompoundId

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """
        # TODO: montar a lista de fases suportadas aqui...
