"unit tests"

# pylint: disable=all

from types import SimpleNamespace

import pytest

from GNNPCSAFTPropertyPackage.interfaces import (
    ICapeThermoCompounds,
    ICapeThermoPhases,
    ICapeThermoUniversalConstant,
    ecape_errors,
)
from GNNPCSAFTPropertyPackage.interfaces.ICapePersistence import ICapePersistence
from GNNPCSAFTPropertyPackage.interfaces.ICapeThermoPropertyRoutine import (
    ICapeThermoPropertyRoutine,
)
from GNNPCSAFTPropertyPackage.interfaces.utils_common import PMCState


def variant(value):
    return SimpleNamespace(value=value)


class FakeMaterial:
    def __init__(self):
        self.single_phase_props = []

    def QueryInterface(self, _interface):
        return self

    def GetCompoundList(self, *_args):
        return (["O"], [], [], [], [], [])

    def GetTPFraction(self, _phase):
        return 300.0, 101325.0, [1.0]

    def SetSinglePhaseProp(self, prop, phase, basis, value):
        self.single_phase_props.append((prop, phase, basis, list(value)))


def test_phase_catalog_and_invalid_phase_info():
    phases = object.__new__(ICapeThermoPhases)

    labels, aggregations, key_ids = phases.GetPhaseList(None, None, None)

    assert tuple(labels)[0] == ("Liquid", "Vapor", "Liquid 2")
    assert tuple(aggregations)[0] == ("Liquid", "Vapor", "Liquid")
    assert tuple(key_ids)[0] == ("", "", "")
    assert phases.GetPhaseInfo("vapor", "stateofaggregation") == "Vapor"

    with pytest.raises(Exception):
        phases.GetPhaseInfo("Solid", "StateOfAggregation")


def test_universal_constants_are_exposed():
    constants = object.__new__(ICapeThermoUniversalConstant)

    identifiers = list(constants.GetUniversalConstantList())

    assert "molarGasConstant" in tuple(identifiers)[0]
    assert constants.GetUniversalConstant("IDEALGASSTATEREFERENCEPRESSURE") == 101325.0
    with pytest.raises(Exception):
        constants.GetUniversalConstant("notAConstant")


def test_pressure_dependent_properties_report_no_implementation():
    compounds = object.__new__(ICapeThermoCompounds)

    with pytest.raises(Exception):
        compounds.GetPDependentProperty(
            variant(["boilingPointTemperature"]),
            101325.0,
            variant(["O"]),
            None,
        )

    assert tuple(compounds.GetPDependentPropList())[0] == None


def test_single_phase_property_identifiers_are_case_insensitive(monkeypatch):
    routine = object.__new__(ICapeThermoPropertyRoutine)
    routine.material = FakeMaterial()
    routine.components_smiles = ["O"]
    routine.pcsaft_parameters = [[1.0] * 9]
    routine._kij_matrix = [[0.0]]
    called = []

    def fake_compute(prop, state, phase):
        called.append((prop, state, phase))
        return [1.0]

    monkeypatch.setattr(routine, "_compute_single_phase_property", fake_compute)

    assert routine.CalcSinglePhaseProp(variant(["Density"]), "Liquid") == 0
    assert called == [("density", [300.0, 101325.0, 1.0], "Liquid")]
    assert routine.material.single_phase_props[0][0] == "density"


def test_single_phase_calculation_errors_are_not_silently_discarded(monkeypatch):
    routine = object.__new__(ICapeThermoPropertyRoutine)
    routine.material = FakeMaterial()
    routine.components_smiles = ["O"]
    routine.pcsaft_parameters = [[1.0] * 9]
    routine._kij_matrix = [[0.0]]

    def fail(*_args):
        raise ValueError("thermodynamic solver failed")

    monkeypatch.setattr(routine, "_compute_single_phase_property", fail)

    with pytest.raises(ValueError, match="thermodynamic solver failed"):
        routine.CalcSinglePhaseProp(variant(["density"]), "Liquid")
    assert routine.material.single_phase_props == []


def test_persistence_round_trip_preserves_configuration():
    values = ["O", "CCCCO"]
    kij = [0.068]

    payload = ICapePersistence._serialize(values, kij)
    restored_values, restored_kij = ICapePersistence._deserialize(payload)

    assert restored_values == values
    assert restored_kij == pytest.approx(kij)


def test_pmc_state_constants_match_lifecycle():
    assert PMCState.NON_INITIALIZED != PMCState.EXECUTING
    assert PMCState.TERMINATED != PMCState.EXECUTING
    assert ecape_errors.ECapeInvalidArgument.name == "ECapeInvalidArgument"
