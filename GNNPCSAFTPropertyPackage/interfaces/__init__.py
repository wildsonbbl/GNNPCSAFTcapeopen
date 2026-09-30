"Module with all interfaces class with implemented methods"

from .ICapeIdentification import ICapeIdentification
from .ICapeThermoCompounds import ICapeThermoCompounds
from .ICapeThermoEquilibriumRoutine import ICapeThermoEquilibriumRoutine
from .ICapeThermoMaterialContext import ICapeThermoMaterialContext
from .ICapeThermoPhases import ICapeThermoPhases
from .ICapeThermoUniversalConstant import ICapeThermoUniversalConstant
from .ICapeUtilities import ICapeUtilities


class PropertyPackage(
    ICapeIdentification,
    ICapeThermoMaterialContext,
    ICapeThermoCompounds,
    ICapeThermoEquilibriumRoutine,
    ICapeThermoPhases,
    ICapeThermoUniversalConstant,
    ICapeUtilities,
):
    """Cape-Open Property Package"""


__all__ = [
    "PropertyPackage",
]
