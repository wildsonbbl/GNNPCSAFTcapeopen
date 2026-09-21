"Module with all interfaces class with implemented methods"

from .ecape_user import ECapeUserImpl
from .ICapeIdentification import ICapeIdentification
from .ICapeThermoCompounds import ICapeThermoCompounds
from .ICapeThermoEquilibriumRoutine import ICapeThermoEquilibriumRoutine
from .ICapeThermoMaterialContext import ICapeThermoMaterialContext
from .ICapeThermoPhases import ICapeThermoPhases
from .ICapeThermoPropertyRoutine import ICapeThermoPropertyRoutine
from .ICapeThermoUniversalConstant import ICapeThermoUniversalConstant


class PropertyPackage(
    ICapeIdentification,
    ICapeThermoMaterialContext,
    ICapeThermoCompounds,
    ICapeThermoPropertyRoutine,
    ICapeThermoEquilibriumRoutine,
    ICapeThermoPhases,
    ICapeThermoUniversalConstant,
    ECapeUserImpl,
):
    """Cape-Open Property Package"""


__all__ = [
    "ICapeIdentification",
    "ICapeThermoCompounds",
    "ICapeThermoEquilibriumRoutine",
    "ICapeThermoMaterialContext",
    "ICapeThermoPhases",
    "ICapeThermoPropertyRoutine",
    "ICapeThermoUniversalConstant",
    "PropertyPackage",
]
