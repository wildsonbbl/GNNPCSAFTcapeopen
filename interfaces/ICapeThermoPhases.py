"ICapeThermoPhases"

from .utils_common import bstr_array_variant


class ICapeThermoPhases:
    "ICapeThermoPhases Class with methods implemented"

    # --- ICapeThermoPhases ---
    def ICapeThermoPhases_GetNumPhases(self):
        """
        Returns the number of Phases supported.

        Returns:
            num (CapeLong)

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """
        return 2

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

        result = {
            "1": {
                "StateOfAggregation": "Liquid",
                "KeyCompoundId": "UNDEFINED",
                "ExcludedCompoundId": "UNDEFINED",
                "DensityDescription": "Heavy",
                "UserDescription": "Liquid phase",
                "TypeOfSolid": "UNDEFINED",
            },
            "2": {
                "StateOfAggregation": "Vapor",
                "KeyCompoundId": "UNDEFINED",
                "ExcludedCompoundId": "UNDEFINED",
                "DensityDescription": "Light",
                "UserDescription": "Gas phase",
                "TypeOfSolid": "UNDEFINED",
            },
        }

        if phaseLabel in result and phaseAttribute in result[phaseLabel]:
            return result[phaseLabel][phaseAttribute]
        return "UNDEFINED"

    def ICapeThermoPhases_GetPhaseList(
        self, phaseLabels, stateOfAggregation, keyCompoundId
    ):
        """
        Returns Phase labels and other important descriptive information for
        all the Phases supported.

        Returns (all ACTUALLYout, CapeArrayString):
            phaseLabels, stateOfAggregation, keyCompoundId

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """

        phaseLabels, stateOfAggregation, keyCompoundId = (
            bstr_array_variant(["1", "2"]),
            bstr_array_variant(["Liquid", "Vapor"]),
            bstr_array_variant(["UNDEFINED", "UNDEFINED"]),
        )
        return phaseLabels, stateOfAggregation, keyCompoundId
