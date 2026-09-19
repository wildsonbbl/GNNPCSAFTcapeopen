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

from comtypes import (
    CLSCTX_INPROC_SERVER,
    GUID,
    COMObject,
    IUnknown,
)
from comtypes.automation import VARIANT, VT_ARRAY, VT_BSTR
from comtypes.client import GetModule

# 1. Importar/Gerar as interfaces do CAPE-OPEN v1.1 a partir do TypeLib oficial
try:

    GetModule("CAPE-OPENv1-1-0.tlb")
    from comtypes.gen.CAPEOPEN110 import (
        ICapeIdentification,
        ICapeThermoCompounds,
        ICapeThermoEquilibriumRoutine,
        ICapeThermoMaterialContext,
        ICapeThermoPhases,
        ICapeThermoPropertyRoutine,
        ICapeThermoUniversalConstant,
    )
except Exception as e:
    raise RuntimeError(
        "Type Library do CAPE-OPEN v1.1 não encontrada no sistema."
    ) from e

# pylint: disable=c0115,c0116,c0103

CLSID = "{A3F10E65-3852-4C10-9D45-6B9A8C110001}"
PROGID = "wildsonbbl.gnnpcsaftPP"
CATEGORY_ID = "{CF51E384-0110-4ed8-ACB7-B50CFDE6908E}"


# 2. Definir o Property Package
class GNNPCSAFTPropertyPackage(COMObject):
    _reg_clsid_ = GUID(CLSID)
    _reg_progid_ = PROGID
    _reg_desc_ = "GNNPCSAFT Property Package"
    _reg_clsctx_ = CLSCTX_INPROC_SERVER

    _com_interfaces_ = [
        ICapeIdentification,
        ICapeThermoPropertyRoutine,
        ICapeThermoMaterialContext,
        ICapeThermoCompounds,
        ICapeThermoPhases,
        ICapeThermoEquilibriumRoutine,
        ICapeThermoUniversalConstant,
        IUnknown,
    ]

    def __init__(self):
        super().__init__()
        self.name = "GNNPCSAFT Property Package"
        self.description = (
            "PC-SAFT Thermodynamic Property Package"
            " with Graph Neural Network estimated parameters"
        )
        self.material = None

    # --- ICapeIdentification ---
    def ICapeIdentification_get_ComponentName(self):
        return self.name

    def ICapeIdentification_put_ComponentName(self, name):
        self.name = name

    def ICapeIdentification_get_ComponentDescription(self):
        return self.description

    def ICapeIdentification_put_ComponentDescription(self, desc):
        self.description = desc

    # --- ICapeThermoMaterialContext ---
    def ICapeThermoMaterialContext_SetMaterial(self, material):
        self.material = material

    def ICapeThermoMaterialContext_UnsetMaterial(self):
        self.material = None

    # --- ICapeThermoPropertyRoutine ---
    def ICapeThermoPropertyRoutine_GetSinglePhasePropList(self):

        variant_array = VARIANT(
            VT_ARRAY | VT_BSTR, ["enthalpy", "compressibilityFactor", "density"]
        )
        return variant_array

    def ICapeThermoPropertyRoutine_CalcSinglePhaseProp(self, props, phaseLabel):
        if not self.material:
            raise Exception(
                f"Material não atribuído. props: {props}. phaseLable: {phaseLabel}"
            )
        # Cálculo das propriedades PC-SAFT aqui...


# 3. Função para registar a Categoria CAPE-OPEN v1.1 no Windows Registry
def register_capeopen_category():
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
    from comtypes.server.register import UseCommandLine

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
