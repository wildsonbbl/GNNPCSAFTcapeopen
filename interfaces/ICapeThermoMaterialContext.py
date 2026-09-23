"ICapeThermoMaterialContext"

from comtypes.gen import CAPEOPEN110

from .utils_common import GNNPCSAFTPPbase


class ICapeThermoMaterialContext(
    GNNPCSAFTPPbase, CAPEOPEN110.ICapeThermoMaterialContext
):
    "ICapeThermoMaterialContext Class with methods implemented"

    # --- ICapeThermoMaterialContext ---
    def SetMaterial(self, material):
        "Receives a ICapeThermoMaterial and set up Material Context"
        self._require_components(
            interfaceName="ICapeThermoMaterialContext", operation="SetMaterial"
        )
        self.material = material.QueryInterface(CAPEOPEN110.ICapeThermoMaterial)
        return 0

    def UnsetMaterial(self):
        "Unset Material Context"
        self.material = None
        return 0
