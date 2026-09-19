"ICapeIdentification"


class ICapeIdentification:

    # --- ICapeIdentification ---
    def ICapeIdentification_GetComponentName(self):
        return self.name

    def ICapeIdentification_SetComponentName(self, name):
        self.name = name

    def ICapeIdentification_GetComponentDescription(self):
        return self.description

    def ICapeIdentification_SetComponentDescription(self, desc):
        self.description = desc
