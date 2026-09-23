"ICapeThermoPhases"

from comtypes.gen import CAPEOPEN110

from .utils_common import GNNPCSAFTPPbase


class ICapeThermoPhases(GNNPCSAFTPPbase, CAPEOPEN110.ICapeThermoPhases):
    "ICapeThermoPhases Class with methods implemented"

    # --- ICapeThermoPhases ---
    def GetNumPhases(self):
        """
        Returns the number of Phases supported.

        Returns:
            num (CapeLong)

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """
        return 2

    def GetPhaseInfo(self, phaseLabel, phaseAttribute):
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
                "KeyCompoundId": "",
                "ExcludedCompoundId": "",
                "DensityDescription": "Heavy",
                "UserDescription": "Liquid phase",
                "TypeOfSolid": "",
            },
            "2": {
                "StateOfAggregation": "Vapor",
                "KeyCompoundId": "",
                "ExcludedCompoundId": "",
                "DensityDescription": "Light",
                "UserDescription": "Gas phase",
                "TypeOfSolid": "",
            },
        }

        if phaseLabel in result and phaseAttribute in result[phaseLabel]:
            return result[phaseLabel][phaseAttribute]
        return ""

    def GetPhaseList(self, phaseLabels, stateOfAggregation, keyCompoundId):
        """
        Returns Phase labels and other important descriptive information for
        all the Phases supported.

        Returns (all ACTUALLYout, CapeArrayString):
            phaseLabels, stateOfAggregation, keyCompoundId

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """

        phaseLabels, stateOfAggregation, keyCompoundId = (
            self.bstr_array_variant(["1", "2"]),
            self.bstr_array_variant(["Liquid", "Vapor"]),
            self.bstr_array_variant(["", ""]),
        )
        return phaseLabels, stateOfAggregation, keyCompoundId
