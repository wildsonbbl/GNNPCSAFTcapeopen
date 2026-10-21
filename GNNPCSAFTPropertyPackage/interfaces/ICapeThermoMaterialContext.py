"ICapeThermoMaterialContext"

from comtypes.gen import CAPEOPEN110

from .utils_common import GNNPCSAFTPPbase


class ICapeThermoMaterialContext(
    GNNPCSAFTPPbase, CAPEOPEN110.ICapeThermoMaterialContext
):
    """Attach and detach the CAPE-OPEN Material Object used by this package."""

    # --- ICapeThermoMaterialContext ---
    def SetMaterial(self, material):
        """Attach an ``ICapeThermoMaterial`` to the property package."""
        self.material = material.QueryInterface(CAPEOPEN110.ICapeThermoMaterial)
        return 0

    def UnsetMaterial(self):
        """Detach the current Material Object."""
        self.material = None
        return 0
