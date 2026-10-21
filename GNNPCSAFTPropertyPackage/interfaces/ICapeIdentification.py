"ICapeIdentification"

from comtypes.gen import CAPEOPEN110


class ICapeIdentification(CAPEOPEN110.ICapeIdentification):
    """Expose the CAPE-OPEN component name and description."""

    ComponentName = "GNNPCSAFT Property Package"
    ComponentDescription = "PC-SAFT Property Package with GNN-estimated parameters"
