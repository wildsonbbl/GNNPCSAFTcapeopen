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
from GNNPCSAFTPropertyPackage.interfaces.pc_saft_feos import solve_entropy
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

    def SetTwoPhaseProp(self, prop, phases, basis, value):
        pass

    def GetOverallProp(self, prop, basis=None):
        if prop == "temperature":
            return [300.0]
        if prop == "pressure":
            return [101325.0]
        raise RuntimeError(prop)


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


def test_pressure_dependent_property_list_is_supported():
    compounds = object.__new__(ICapeThermoCompounds)

    assert tuple(compounds.GetPDependentPropList())[0] == ("boilingpointtemperature",)


def test_compound_ids_undefined_select_all_compounds():
    compounds = object.__new__(ICapeThermoCompounds)
    compounds.components_smiles = ["O", "CCCCO"]

    assert compounds._compound_indices(None) == [0, 1]
    assert compounds._compound_indices([]) == [0, 1]
    assert compounds._compound_indices(["ccccO"]) == [1]


def test_overall_scalar_only_uses_explicit_feos_defaults(monkeypatch):
    from comtypes import COMError

    from GNNPCSAFTPropertyPackage.interfaces.utils_common import GNNPCSAFTPPbase

    package = object.__new__(GNNPCSAFTPPbase)

    class MissingMaterial:
        def GetOverallProp(self, *_args):
            raise COMError(1, "missing", None)

    setattr(package, "material", MissingMaterial())
    assert package._get_overall_scalar("pressure", default=101325.0) == 101325.0
    with pytest.raises(COMError):
        package._get_overall_scalar("pressure")


def test_residual_entropy_solver_inverts_temperature():
    import si_units as si
    from feos import Contributions
    from gnnepcsaft.pcsaft.feos.mixture import state_npt_feos
    from gnnepcsaft_mcp_server.utils import predict_pcsaft_parameters

    parameters = [predict_pcsaft_parameters("O")]
    kij_matrix = [[0.0]]
    state = [300.0, 101325.0, 1.0]
    entropy = state_npt_feos(
        parameters=parameters, state=state, kij_matrix=kij_matrix
    ).molar_entropy(Contributions.Residual)
    entropy_value = float(entropy / (si.JOULE / si.MOL / si.KELVIN))

    assert solve_entropy(
        entropy=entropy_value,
        init_temp=300.0,
        pressure=101325.0,
        fractions=[1.0],
        parameters=parameters,
        kij_matrix=kij_matrix,
    ) == pytest.approx(300.0, abs=1e-6)


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


def test_vapor_volume_is_calculated_and_written_as_molar_property(monkeypatch):
    routine = object.__new__(ICapeThermoPropertyRoutine)
    routine.material = FakeMaterial()
    routine.components_smiles = ["O"]
    routine.pcsaft_parameters = [[1.0] * 9]
    routine._kij_matrix = [[0.0]]

    monkeypatch.setattr(
        "GNNPCSAFTPropertyPackage.interfaces.ICapeThermoPropertyRoutine.mix_den_feos",
        lambda **_kwargs: 2.0,
    )

    assert routine.CalcSinglePhaseProp(variant(["Volume"]), "Vapor") == 0
    prop, phase, basis, value = routine.material.single_phase_props[0]
    assert prop == "volume"
    assert phase == "Vapor"
    assert basis == "Mole"
    assert value[0][0] == pytest.approx(0.5)


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
