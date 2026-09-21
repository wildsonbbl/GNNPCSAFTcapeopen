"Module with all interfaces class with implemented methods"

from .ecape_user import ECapeUser
from .ICapeIdentification import ICapeIdentification
from .ICapeThermoCompounds import ICapeThermoCompounds
from .ICapeThermoEquilibriumRoutine import ICapeThermoEquilibriumRoutine
from .ICapeThermoMaterialContext import ICapeThermoMaterialContext
from .ICapeThermoPhases import ICapeThermoPhases
from .ICapeThermoPropertyRoutine import ICapeThermoPropertyRoutine
from .ICapeThermoUniversalConstant import ICapeThermoUniversalConstant
from .ICapeUtilities import ICapeUtilities


class PropertyPackage(
    ICapeIdentification,
    ICapeThermoMaterialContext,
    ICapeThermoCompounds,
    ICapeThermoPropertyRoutine,
    ICapeThermoEquilibriumRoutine,
    ICapeThermoPhases,
    ICapeThermoUniversalConstant,
    ECapeUser,
    ICapeUtilities,
):
    """Cape-Open Property Package"""


__all__ = [
    "PropertyPackage",
]
