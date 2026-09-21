"ICapeThermoMaterialContext"

from .utils_common import GNNPCSAFTPPbase


class ICapeThermoMaterialContext(GNNPCSAFTPPbase):
    "ICapeThermoMaterialContext Class with methods implemented"

    # --- ICapeThermoMaterialContext ---
    def ICapeThermoMaterialContext_SetMaterial(self, material):
        "Receives a ICapeThermoMaterial and set up Material Context"
        self._require_components(
            interfaceName="ICapeThermoMaterialContext", operation="SetMaterial"
        )
        self.material = material

    def ICapeThermoMaterialContext_UnsetMaterial(self):
        "Unset Material Context"
        self.material = None
