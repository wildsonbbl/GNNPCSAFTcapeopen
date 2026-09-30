"ICapeThermoUniversalConstant"

from comtypes.gen import CAPEOPEN110

from .ecape_errors import ECapeInvalidArgument
from .utils_common import GNNPCSAFTPPbase

_UNIVERSAL_CONSTANTS = {
    "avogadroConstant": 6.0221419947e23,
    "boltzmannConstant": 1.380650324e-23,
    "idealGasStateReferencePressure": 101325.0,
    "molarGasConstant": 8.31447215,
    "speedOfLightInVacuum": 2.99792458e8,
    "standardAccelerationOfGravity": 9.80665,
}


class ICapeThermoUniversalConstant(
    GNNPCSAFTPPbase, CAPEOPEN110.ICapeThermoUniversalConstant
):
    "ICapeThermoUniversalConstant Class with methods implemented"

    # --- ICapeThermoUniversalConstant ---
    def GetUniversalConstant(self, constantId):
        """
        Retrieves the value of a Universal Constant (e.g. avogadroConstant,
        boltzmannConstant, idealGasStateReferencePressure, molarGasConstant,
        speedOfLightInVacuum, standardAccelerationOfGravity -- section
        7.5.1).

        Args:
            constantId (CapeString): identifier of the Universal Constant,
                one of GetUniversalConstantList's values.

        Returns:
            constantValue (CapeVariant): numeric (Double) or string value.

        Raises (per spec): ECapeNoImpl, ECapeInvalidArgument, ECapeUnknown.
        """
        if constantId in _UNIVERSAL_CONSTANTS:
            return _UNIVERSAL_CONSTANTS[constantId]
        return self.raise_cape_error(
            error_cls=ECapeInvalidArgument,
            description=f"Unknown universal constant identifier: {constantId!r}",
            interfaceName="ICapeThermoUniversalConstant",
            operation="GetUniversalConstant",
        )

    def GetUniversalConstantList(self):
        """
        Returns the identifiers of the supported Universal Constants.

        Returns:
            constantIds (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """
        return self.bstr_array_variant(list(_UNIVERSAL_CONSTANTS))
