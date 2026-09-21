"ICapeThermoPropertyRoutine"

from .utils_common import GNNPCSAFTPPbase


class ICapeThermoPropertyRoutine(GNNPCSAFTPPbase):
    "ICapeThermoPropertyRoutine Class with methods implemented"

    # --- ICapeThermoPropertyRoutine ---
    def ICapeThermoPropertyRoutine_CalcAndGetLnPhi(
        self,
        phaseLabel,
        temperature,
        pressure,
        moleNumbers,
        fFlags,
    ):
        """
        Calculates the natural logarithm of the fugacity coefficients (and
        optionally their T/P/mole-number derivatives) for a single-Phase
        mixture, from T/P/composition given directly as arguments (not
        pulled from the Material Object). Does not affect the state of the
        Material Object.

        Args:
            phaseLabel (CapeString): Phase label, one of GetPhaseList's
                values.
            temperature (CapeDouble): temperature (K).
            pressure (CapeDouble): pressure (Pa).
            moleNumbers (CapeArrayDouble): mole fractions of the Compounds
                (name is a historical misnomer -- these are fractions).
            fFlags (CapeInteger): eCapeCalculationCode bit flags selecting
                which of {value, dT, dP, dn} to compute.

        Returns (all ACTUALLYout, CapeArrayDouble):
            lnPhi, lnPhiDT, lnPhiDP, lnPhiDn

        Raises (per spec): ECapeNoImpl, ECapeLimitedImpl, ECapeBadInvOrder,
            ECapeFailedInitialisation, ECapeThrmPropertyNotAvailable,
            ECapeSolvingError, ECapeInvalidArgument, ECapeUnknown.
        """

        # TODO: Cálculo do ln(phi) e derivadas via PC-SAFT aqui...

    def ICapeThermoPropertyRoutine_CalcSinglePhaseProp(self, props, phaseLabel):
        """Calculates properties/derivatives that depend on one phase"""

        # TODO: Cálculo das propriedades de uma fase aqui...

    def ICapeThermoPropertyRoutine_CalcTwoPhaseProp(self, props, phaseLabels):
        """
        Calculates mixture properties/derivatives that depend on two Phases
        (e.g. surface tension, K-values) at the current T/P/composition of
        the Material Object. Does not perform an Equilibrium Calculation.

        Args:
            props (CapeArrayString): two-phase property identifiers
                (sections 7.5.6 and 7.6).
            phaseLabels (CapeArrayString): the two Phase labels, both from
                GetPhaseList and both present in the Material Object.

        Returns: -  (values are written back into the Material Object via
            SetTwoPhaseProp, not returned directly)

        Raises (per spec): ECapeNoImpl, ECapeLimitedImpl, ECapeBadInvOrder,
            ECapeFailedInitialisation, ECapeThrmPropertyNotAvailable,
            ECapeSolvingError, ECapeInvalidArgument, ECapeUnknown.
        """

        # TODO: Cálculo das propriedades de duas fases aqui...

    def ICapeThermoPropertyRoutine_CheckSinglePhasePropSpec(
        self, co_property, phaseLabel
    ):
        """
        Checks whether CalcSinglePhaseProp can calculate the given property
        for the given Phase. Depends only on this component's capabilities
        and configuration, not on any Material Object state.

        Args:
            property (CapeString): identifier to check, must be one of
                GetSinglePhasePropList's values to be valid.
            phaseLabel (CapeString): Phase label, must be one of
                GetPhaseList's values to be valid.

        Returns:
            valid (CapeBoolean)

        Raises (per spec): ECapeNoImpl, ECapeInvalidArgument, ECapeUnknown.
        """
        # TODO: verificar suporte à propriedade/fase solicitada aqui...

    def ICapeThermoPropertyRoutine_CheckTwoPhasePropSpec(
        self, co_property, phaseLabels
    ):
        """
        Checks whether CalcTwoPhaseProp can calculate the given property for
        the given pair of Phases. Depends only on this component's
        capabilities and configuration, not on any Material Object state.

        Args:
            co_property (CapeString): identifier to check, must be one of
                GetTwoPhasePropList's values to be valid.
            phaseLabels (CapeArrayString): the two Phase labels to check,
                must be from GetPhaseList's values.

        Returns:
            valid (CapeBoolean)

        Raises (per spec): ECapeNoImpl, ECapeInvalidArgument, ECapeUnknown.
        """
        # TODO: verificar suporte à propriedade/par de fases solicitado aqui...

    def ICapeThermoPropertyRoutine_GetSinglePhasePropList(self):
        """
        Returns the list of supported non-constant single-phase properties
        (i.e. those calculable by CalcSinglePhaseProp), including derivatives.

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """

        # TODO: listar as propriedades de uma fase suportadas aqui...
        return self.bstr_array_variant(["UNDEFINED"])

    def ICapeThermoPropertyRoutine_GetTwoPhasePropList(self):
        """
        Returns the list of supported non-constant two-phase properties
        (i.e. those calculable by CalcTwoPhaseProp), including derivatives.

        Returns:
            props (CapeArrayString)

        Raises (per spec): ECapeNoImpl, ECapeUnknown.
        """
        # TODO: listar as propriedades de duas fases suportadas aqui...
        return self.bstr_array_variant(["UNDEFINED"])
