"ICapeThermoMaterialContext"


class ICapeThermoMaterialContext:

    # --- ICapeThermoMaterialContext ---
    def ICapeThermoMaterialContext_SetMaterial(self, material):
        self.material = material

    def ICapeThermoMaterialContext_UnsetMaterial(self):
        self.material = None
