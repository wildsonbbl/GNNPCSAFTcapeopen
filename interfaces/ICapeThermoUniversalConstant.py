"ICapeThermoUniversalConstant"


class ICapeThermoUniversalConstant:

    # --- ICapeThermoUniversalConstant ---
    def ICapeThermoUniversalConstant_GetUniversalConstant(self, constantId):
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
        # TODO: retornar o valor da constante universal solicitada aqui...

    def ICapeThermoUniversalConstant_GetUniversalConstantList(self):
        """
        Returns the identifiers of the supported Universal Constants.

        Returns:
            constantIds (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """
        # TODO: listar as constantes universais suportadas aqui...
