"""
CAPE-OPEN Thermo 1.1 property package server for GNN-PC-SAFT.

This implements a CAPE-OPEN 1.1 "Property Package" component, late-bound over
pywin32 COM (no CAPE-OPEN type library needed at build time, so different
CAPE-OPEN hosts -- COCO, Aspen Plus, gPROMS, etc. -- can all use it).

CAPE-OPEN 1.1 Thermo architecture in one paragraph, for context: a host
(the "PME") creates a Material Object to describe a stream/mixture, and
hands it to this Property Package via ICapeThermoMaterialContext.SetMaterial.
From then on the Property Package pulls temperature/pressure/composition out
of the Material Object (it is never passed as plain method arguments) and
writes calculated properties back into it. Property calculations
(ICapeThermoPropertyRoutine) and phase-equilibrium calculations
(ICapeThermoEquilibriumRoutine) are two separate, optional interfaces; a
Property Package is expected to implement both.
"""

import sys
import winreg
from typing import Iterable, Sequence

from comtypes import (
    CLSCTX_INPROC_SERVER,
    GUID,
    COMObject,
    IUnknown,
)
from comtypes.client import GetModule
from comtypes.server.register import UseCommandLine

# 1. Importar/Gerar as interfaces do CAPE-OPEN v1.1 a partir do TypeLib oficial
try:

    GetModule("CAPE-OPENv1-1-0.tlb")
    from comtypes.gen import CAPEOPEN110
except Exception as e:
    raise RuntimeError(
        "Type Library do CAPE-OPEN v1.1 não encontrada no sistema."
    ) from e

from gnnepcsaft_mcp_server.utils import predict_pcsaft_parameters

import interfaces
from interfaces.ICapeExceptions import ECapeInvalidArgument

CLSID = "{A3F10E65-3852-4C10-9D45-6B9A8C110001}"
PROGID = "wildsonbbl.gnnpcsaftPP"
CATEGORY_ID = "{CF51E384-0110-4ed8-ACB7-B50CFDE6908E}"


# 2. Definir o Property Package
class GNNPCSAFTPropertyPackage(
    COMObject,
    interfaces.PropertyPackage,
):
    "GNNPCSAFTPropertyPackage"

    _reg_clsid_ = GUID(CLSID)
    _reg_progid_ = PROGID
    _reg_desc_ = "GNNPCSAFT Property Package"
    _reg_clsctx_ = CLSCTX_INPROC_SERVER

    _com_interfaces_ = [
        CAPEOPEN110.ICapeIdentification,
        CAPEOPEN110.ICapeThermoPropertyRoutine,
        CAPEOPEN110.ICapeThermoMaterialContext,
        CAPEOPEN110.ICapeThermoCompounds,
        CAPEOPEN110.ICapeThermoPhases,
        CAPEOPEN110.ICapeThermoEquilibriumRoutine,
        CAPEOPEN110.ICapeThermoUniversalConstant,
        CAPEOPEN110.ECapeUser,
        CAPEOPEN110.ICapeUtilities,
        IUnknown,
    ]

    # def __init__(self) -> None:
    #     super().__init__()
    #     self.SetComponents(["O", "CCO"])

    def SetComponents(self, components_smiles: Iterable[str]):
        """Configure the fixed set of compounds this Property Package supports.

        Call this once, before registering/using the object as a CAPE-OPEN
        server. It plays the role that a proper ICapeUtilities-driven
        compound-selection dialog would play in a full implementation.
        """
        components_smiles = [str(smiles) for smiles in components_smiles]
        if not components_smiles:
            raise ECapeInvalidArgument("At least one component is required")
        self.components_smiles = components_smiles
        self.pcsaft_parameters = [
            predict_pcsaft_parameters(smiles) for smiles in components_smiles
        ]
        self._kij_matrix = [[0.0] * len(components_smiles) for _ in components_smiles]

    def SetKijMatrix(self, kij_matrix: Sequence[Sequence[float]]):
        "Set kij matrix"
        self._require_components()
        matrix = [list(map(float, row)) for row in kij_matrix]
        size = len(self.pcsaft_parameters)
        if len(matrix) != size or any(len(row) != size for row in matrix):
            raise ECapeInvalidArgument(
                "kij_matrix must be a square matrix matching the components"
            )
        self._kij_matrix = matrix


# 3. Função para registar a Categoria CAPE-OPEN v1.1 no Windows Registry
def register_capeopen_category():
    "Register CO ProgId, Category and Metadata"
    # CAPE-OPEN v1.1 Thermo Property Package Category

    # 1. Register ProgID -> CLSID mapping explicitly
    progid_key_path = f"{PROGID}\\CLSID"
    with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, progid_key_path) as key:
        winreg.SetValue(key, "", winreg.REG_SZ, CLSID)

    # 2. Register CAPE-OPEN Implemented Category
    cat_key_path = f"CLSID\\{CLSID}\\Implemented Categories\\{CATEGORY_ID}"
    winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, cat_key_path)

    # 3. Write CAPE-OPEN Metadata Strings
    clsid_key_path = f"CLSID\\{CLSID}\\CapeDescription"
    with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, clsid_key_path) as key:
        winreg.SetValueEx(key, "About", 0, winreg.REG_SZ, "GNNPCSAFT")
        winreg.SetValueEx(key, "CapeVersion", 0, winreg.REG_SZ, "1.1")
        winreg.SetValueEx(key, "ComponentVersion", 0, winreg.REG_SZ, "0.1")
        winreg.SetValueEx(
            key,
            "Description",
            0,
            winreg.REG_SZ,
            "PC-SAFT Thermodynamic Property Package with Graph Neural Network estimated parameters",
        )
        winreg.SetValueEx(key, "Name", 0, winreg.REG_SZ, "GNNPCSAFT")
        winreg.SetValueEx(key, "VendorURL", 0, winreg.REG_SZ, "wildsonbbl.com")


def unregister_capeopen_category():
    "Unregister CO ProgId, Category and Metadata"
    try:
        winreg.DeleteKey(
            winreg.HKEY_CLASSES_ROOT,
            f"CLSID\\{CLSID}\\Implemented Categories\\{CATEGORY_ID}",
        )
        winreg.DeleteKey(
            winreg.HKEY_CLASSES_ROOT,
            f"{PROGID}\\CLSID",
        )
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, PROGID)
    except FileNotFoundError:
        pass


if __name__ == "__main__":

    if "-regserver" in sys.argv:
        UseCommandLine(GNNPCSAFTPropertyPackage)
        register_capeopen_category()
        print("Successfully registered GNNPCSAFTPropertyPackage.")
    elif "-unregserver" in sys.argv:
        unregister_capeopen_category()
        UseCommandLine(GNNPCSAFTPropertyPackage)
        print("Successfully unregistered GNNPCSAFTPropertyPackage.")
    else:
        UseCommandLine(GNNPCSAFTPropertyPackage)
