"ICapeThermoMaterialContext"


class ICapeThermoMaterialContext:
    "ICapeThermoMaterialContext Class with methods implemented"

    material = None

    # --- ICapeThermoMaterialContext ---
    def ICapeThermoMaterialContext_SetMaterial(self, material):
        "Receives a ICapeThermoMaterial and set up Material Context"
        self.material = material

    def ICapeThermoMaterialContext_UnsetMaterial(self):
        "Unset Material Context"
        self.material = None
