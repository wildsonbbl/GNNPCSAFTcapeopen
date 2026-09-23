"ICapeThermoEquilibriumRoutine"

import copy
import logging

from comtypes.gen import CAPEOPEN110
from gnnepcsaft.pcsaft.pcsaft_feos import (
    is_stable_feos,
    mix_tp_flash_feos,
)

from . import ecape_errors
from .ICapeThermoPropertyRoutine import (
    ICapeThermoPropertyRoutine,
)


class ICapeThermoEquilibriumRoutine(
    ICapeThermoPropertyRoutine, CAPEOPEN110.ICapeThermoEquilibriumRoutine
):
    "ICapeThermoEquilibriumRoutine Class with methods implemented"

    # --- ICapeThermoEquilibriumRoutine ---
    def CalcEquilibrium(
        self,
        specification1,
        specification2,
        solutionType,
    ):
        """
        Calculates the amounts, compositions, temperature and pressure of
        the Phases present in the Material Object (as set via
        SetPresentPhases) at equilibrium, given two specifications read
        from the Material Object.

        Args:
            specification1 (CapeArrayString): first specification, as a
                sequence [property identifier, basis, phase label,
                (compound identifier)] -- see spec section 6.6 for details
                and examples (e.g. fixed T/P, fixed P/H, fixed T/vapour
                phase fraction, etc.).
            specification2 (CapeArrayString): second specification, same
                format as specification1.
            solutionType (CapeString): "Unspecified", "Normal" or
                "Retrograde".

        Returns: - (results are written back into the Material Object via
            SetPresentPhases / SetSinglePhaseProp, not returned directly)

        Raises (per spec): ECapeNoImpl, ECapeBadInvOrder, ECapeSolvingError,
            ECapeLimitedImpl, ECapeInvalidArgument,
            ECapeFailedInitialisation, ECapeUnknown.
        """
        self._require_material(
            interfaceName="ICapeThermoEquilibriumRoutine",
            operation="CalcEquilibrium",
        )
        assert self.material is not None
        pcsaft_parameters = copy.copy(self.pcsaft_parameters)
        _kij_matrix = copy.copy(self._kij_matrix)
        assert pcsaft_parameters is not None

        if not self.CheckEquilibriumSpec(specification1, specification2, solutionType):
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeLimitedImpl,
                description="Only a Temperature/Pressure (TP) flash specification is "
                "implemented by this Property Package",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
            )

        temperature = self._get_overall_scalar("temperature")
        pressure = self._get_overall_scalar("pressure")
        fractions = self._get_overall_fractions()
        if 0.0 in fractions:
            return 0
        state = [temperature, pressure, *fractions]
        logging.debug("Passed getting state: %s", state)

        try:
            if is_stable_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=_kij_matrix
            ):
                phaseLabel = "Liquid"
                self.material.SetPresentPhases(
                    phaseLabels=self.bstr_array_variant([phaseLabel]),
                    phaseStatus=self.i4_array_variant([CAPEOPEN110.CAPE_ATEQUILIBRIUM]),
                )
                self.material.SetSinglePhaseProp(
                    "temperature",
                    phaseLabel,
                    None,
                    self.r8_array_variant([temperature]),
                )
                self.material.SetSinglePhaseProp(
                    "pressure", phaseLabel, None, self.r8_array_variant([pressure])
                )
                self.material.SetSinglePhaseProp(
                    "fraction", phaseLabel, "Mole", self.r8_array_variant(fractions)
                )
                self.material.SetSinglePhaseProp(
                    "phaseFraction", phaseLabel, "Mole", self.r8_array_variant([1.0])
                )
                logging.debug("STABLE PHASE FINISHED")
                single_phase_prop_list = self.GetSinglePhasePropList()
                self.CalcSinglePhaseProp(
                    props=single_phase_prop_list,
                    phaseLabel=phaseLabel,
                )
                logging.debug("SINGLE PHASE PROP FINISHED")
                return 0
            result = mix_tp_flash_feos(pcsaft_parameters, state, _kij_matrix)
        except Exception as exc:  # pylint:disable=broad-exception-caught
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeSolvingError,
                description=f"TP flash failed to converge: {exc}",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CalcEquilibrium",
            )

        liquid_fractions = result.liquid.molefracs
        vapor_fractions = result.vapor.molefracs
        liquid_beta = self._phase_attr(result.liquid, ("phase_fraction", "beta"))
        vapor_beta = self._phase_attr(result.vapor, ("phase_fraction", "beta"))
        logging.debug(
            "IN CalcEquilibrium ---> [liquid_fractions, vapor_fractions] == %s",
            [liquid_fractions, vapor_fractions],
        )

        self.material.SetPresentPhases(
            self.bstr_array_variant(["Vapor", "Liquid"]),
            self.i4_array_variant(
                [
                    CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                    CAPEOPEN110.CAPE_ATEQUILIBRIUM,
                ]
            ),
        )
        self.material.SetSinglePhaseProp(
            "temperature",
            "Vapor",
            None,
            self.r8_array_variant([temperature]),
        )
        self.material.SetSinglePhaseProp(
            "temperature",
            "Liquid",
            None,
            self.r8_array_variant([temperature]),
        )
        self.material.SetSinglePhaseProp(
            "pressure",
            "Vapor",
            None,
            self.r8_array_variant([pressure]),
        )
        self.material.SetSinglePhaseProp(
            "pressure",
            "Liquid",
            None,
            self.r8_array_variant([pressure]),
        )
        self.material.SetSinglePhaseProp(
            "fraction",
            "Vapor",
            "Mole",
            self.r8_array_variant(vapor_fractions),
        )
        self.material.SetSinglePhaseProp(
            "fraction",
            "Liquid",
            "Mole",
            self.r8_array_variant(liquid_fractions),
        )
        if vapor_beta is not None:
            self.material.SetSinglePhaseProp(
                "phaseFraction",
                "Vapor",
                "Mole",
                self.r8_array_variant([vapor_beta]),
            )
        if liquid_beta is not None:
            self.material.SetSinglePhaseProp(
                "phaseFraction",
                "Liquid",
                "Mole",
                self.r8_array_variant([liquid_beta]),
            )

        two_phase_prop_list = self.GetTwoPhasePropList()
        self.CalcTwoPhaseProp(
            props=two_phase_prop_list,
            phaseLabels=self.bstr_array_variant(["Vapor", "Liquid"]),
        )
        logging.debug("SINGLE PHASE PROP FINISHED")
        return 0

    def CheckEquilibriumSpec(
        self,
        specification1,
        specification2,
        solutionType,
    ):
        """
        Checks whether this component can perform the Equilibrium
        Calculation implied by the given specifications and solution type,
        for the combination of Phases currently present in the Material
        Object (SetPresentPhases must have been called first).

        Args:
            specification1 (CapeArrayString): first specification, same
                format as in CalcEquilibrium.
            specification2 (CapeArrayString): second specification, same
                format as in CalcEquilibrium.
            solutionType (CapeString): "Unspecified", "Normal" or
                "Retrograde".

        Returns:
            isSupported (CapeBoolean)

        Raises (per spec): ECapeNoImpl, ECapeInvalidArgument,
            ECapeBadInvOrder, ECapeUnknown.
        """
        spec1 = self._as_list(specification1.value)
        spec2 = self._as_list(specification2.value)
        soltype = str(solutionType)
        if not spec1 or not spec2:
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeInvalidArgument,
                description="Missing equilibrium specifications",
                interfaceName="ICapeThermoEquilibriumRoutine",
                operation="CheckEquilibriumSpec",
                moreInfo="Both equilibrium specifications are required",
            )
        names = {str(spec1[0]).strip().lower(), str(spec2[0]).strip().lower()}
        return names == {"temperature", "pressure"} and soltype in (
            "Unspecified",
            "Normal",
        )
