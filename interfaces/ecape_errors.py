"""
Concrete CAPE-OPEN error interfaces from the "Error Common Interface" spec, section 3.3,
built on top of ECapeUser (see ecape_user.py).

Each class below mirrors one box in the error class diagram (Figure 6). Since COM has no
interface inheritance, section 5.1.2 requires every component to implement, itself, every
error interface (ancestor and concrete) that it is capable of raising -- Python's normal
multiple inheritance takes care of that for you here: mix the *concrete* error class(es)
you need into your COMObject and all of its ancestors' getters come along for free.

HRESULT values below come straight from the table in section 5.1.2 ("Resulting design").
FIRST_E_INTERFACE_HR (0x80040500) is CO-LaN's chosen offset into the FACILITY_ITF range;
ECapeRoot, ECapeUser and ECapeBoundaries are abstract and have no HRESULT of their own.

Usage sketch:

    from ecape_errors import ECapeInvalidArgument, ECapeInvalidArgumentHR, ECapeSolvingError

    class MyPropertyPackage(ECapeInvalidArgument, ECapeSolvingError, ..., comtypes.COMObject):
        _com_interfaces_ = [
            CAPEOPENXXX.ECapeUser,
            CAPEOPENXXX.ECapeInvalidArgument,
            CAPEOPENXXX.ECapeSolvingError,
        ...]

        def CalcEquilibrium(self, matObj, flashType, props):
            if flashType not in KNOWN_FLASH_TYPES:
                self._set_co_error(
                    name="ECapeInvalidArgument",
                    code=1,
                    description=f"Unknown flash type '{flashType}'",
                    scope="CapeOpen::Common::Error",
                    interfaceName="ICapeThermoPropertyPackage",
                    operation="CalcEquilibrium",
                )
                return ECapeInvalidArgumentHR
            ...

NOTE ON METHOD NAMES: as in ecape_user.py, rename the get_xxx stubs below to match
whatever comtypes actually generated for your typelib if it had to disambiguate
same-named attributes across several of your implemented interfaces.
"""

from .ecape_user import ECapeUser

# pylint: disable=missing-function-docstring

# ---------------------------------------------------------------------------
# HRESULT table (section 5.1.2)
# ---------------------------------------------------------------------------
FIRST_E_INTERFACE_HR = 0x80040500

ECapeUnknownHR = FIRST_E_INTERFACE_HR + 1
ECapeDataHR = FIRST_E_INTERFACE_HR + 2
ECapeLicenceErrorHR = FIRST_E_INTERFACE_HR + 3
ECapeBadCOParameterHR = FIRST_E_INTERFACE_HR + 4
ECapeBadArgumentHR = FIRST_E_INTERFACE_HR + 5
ECapeInvalidArgumentHR = FIRST_E_INTERFACE_HR + 6
ECapeOutOfBoundsHR = FIRST_E_INTERFACE_HR + 7
ECapeImplementationHR = FIRST_E_INTERFACE_HR + 8
ECapeNoImplHR = FIRST_E_INTERFACE_HR + 9
ECapeLimitedImplHR = FIRST_E_INTERFACE_HR + 10
ECapeComputationHR = FIRST_E_INTERFACE_HR + 11
ECapeOutOfResourcesHR = FIRST_E_INTERFACE_HR + 12
ECapeNoMemoryHR = FIRST_E_INTERFACE_HR + 13
ECapeTimeOutHR = FIRST_E_INTERFACE_HR + 14
ECapeFailedInitialisationHR = FIRST_E_INTERFACE_HR + 15
ECapeSolvingErrorHR = FIRST_E_INTERFACE_HR + 16
ECapeBadInvOrderHR = FIRST_E_INTERFACE_HR + 17
ECapeInvalidOperationHR = FIRST_E_INTERFACE_HR + 18
ECapePersistenceHR = FIRST_E_INTERFACE_HR + 19
ECapeIllegalAccessHR = FIRST_E_INTERFACE_HR + 20
ECapePersistenceNotFoundHR = FIRST_E_INTERFACE_HR + 21
ECapePersistenceSystemErrorHR = FIRST_E_INTERFACE_HR + 22
ECapePersistenceOverflowHR = FIRST_E_INTERFACE_HR + 23

LAST_USED_E_INTERFACE_HR = FIRST_E_INTERFACE_HR + 0x17  # 0x80040517, per spec
LAST_E_INTERFACE_HR = 0x8004FFFF


# ---------------------------------------------------------------------------
# ECapeBoundaries (3.3.3) -- abstract "utility" mixin, not raised on its own
# ---------------------------------------------------------------------------
class ECapeBoundaries:
    """
    Factors out value/type/bounds state. Per the diagram this is pulled in by
    ECapeOutOfBounds, which needs to report the offending value and its legal range
    in addition to the argument position it inherits from ECapeBadArgument.
    """

    def __init__(self):
        self._co_lowerBound = 0.0
        self._co_upperBound = 0.0
        self._co_value = 0.0
        self._co_type = ""

    def _set_co_boundaries(self, LowerBound=0.0, UpperBound=0.0, value=0.0, Type=""):
        self._co_lowerBound = LowerBound
        self._co_upperBound = UpperBound
        self._co_value = value
        self._co_type = Type

    def _get_LowerBound(self):
        return self._co_lowerBound

    def _get_UpperBound(self):
        return self._co_upperBound

    def _get_value(self):
        return self._co_value

    def _get_Type(self):
        return self._co_type


# ---------------------------------------------------------------------------
# ECapeUnknown (3.3.4)
# ---------------------------------------------------------------------------
class ECapeUnknown(ECapeUser):
    """Raised when no other error specified by the operation applies. No extra state."""

    HR = ECapeUnknownHR
    name = "ECapeUnknown"


# ---------------------------------------------------------------------------
# ECapeData hierarchy (3.3.5 - 3.3.10)
# ---------------------------------------------------------------------------
class ECapeData(ECapeUser):
    """Base of the data-related errors: bad arguments, parameters, licence issues."""

    HR = ECapeDataHR
    name = "ECapeData"


class ECapeLicenceError(ECapeData):
    """The licence agreement is not respected. No extra state."""

    HR = ECapeLicenceErrorHR
    name = "ECapeLicenceError"


class ECapeBadCOParameter(ECapeData):
    """A Parameter Common Interface object has an invalid status."""

    HR = ECapeBadCOParameterHR
    name = "ECapeBadCOParameter"

    def __init__(self):
        super().__init__()
        self._co_parameterName = ""
        self._co_parameter = None  # ICapeParameter reference

    def _set_co_bad_parameter(self, parameterName="", parameter=None):
        self._co_parameterName = parameterName
        self._co_parameter = parameter

    def get_parameterName(self):
        return self._co_parameterName

    def get_parameter(self):
        return self._co_parameter


class ECapeBadArgument(ECapeData):
    """An argument value of the operation is not correct."""

    HR = ECapeBadArgumentHR
    name = "ECapeBadArgument"

    def __init__(self):
        super().__init__()
        self._co_position = 0  # 1-based position in the operation signature

    def _set_co_position(self, position=0):
        self._co_position = position

    def get_position(self):
        return self._co_position


class ECapeInvalidArgument(ECapeBadArgument):
    """An invalid argument value was passed (e.g. a phase name not in the CO Phase List)."""

    HR = ECapeInvalidArgumentHR
    name = "ECapeInvalidArgument"


class ECapeOutOfBounds(ECapeBadArgument, ECapeBoundaries):
    """An argument value is outside of its bounds. Carries both position and bounds state."""

    HR = ECapeOutOfBoundsHR
    name = "ECapeOutOfBounds"

    def __init__(self):
        ECapeBadArgument.__init__(self)
        ECapeBoundaries.__init__(self)


# ---------------------------------------------------------------------------
# ECapeImplementation hierarchy (3.3.11 - 3.3.13)
# ---------------------------------------------------------------------------
class ECapeImplementation(ECapeUser):
    """Base of the errors related to the current implementation."""

    HR = ECapeImplementationHR
    name = "ECapeImplementation"


class ECapeNoImpl(ECapeImplementation):
    """The operation exists per the CO standard but is not implemented/supported."""

    HR = ECapeNoImplHR
    name = "ECapeNoImpl"


class ECapeLimitedImpl(ECapeImplementation):
    """The limit of a partial implementation has been violated (e.g. TP flash only)."""

    HR = ECapeLimitedImplHR
    name = "ECapeLimitedImpl"


# ---------------------------------------------------------------------------
# ECapeComputation hierarchy (3.3.14 - 3.3.21)
# ---------------------------------------------------------------------------
class ECapeComputation(ECapeUser):
    """Base of the errors related to a calculation."""

    HR = ECapeComputationHR
    name = "ECapeComputation"


class ECapeOutOfResources(ECapeComputation):
    """The physical resources necessary to execute the operation are out of limits."""

    HR = ECapeOutOfResourcesHR
    name = "ECapeOutOfResources"


class ECapeNoMemory(ECapeOutOfResources):
    """The physical memory necessary to execute the operation is out of limit."""

    HR = ECapeNoMemoryHR
    name = "ECapeNoMemory"


class ECapeTimeOut(ECapeOutOfResources):
    """The time-out criterion is reached."""

    HR = ECapeTimeOutHR
    name = "ECapeTimeOut"


class ECapeFailedInitialisation(ECapeComputation):
    """A necessary pre-requisite/initialisation has not been performed or has failed."""

    HR = ECapeFailedInitialisationHR
    name = "ECapeFailedInitialisation"


class ECapeSolvingError(ECapeComputation):
    """A numerical algorithm fails for any reason."""

    HR = ECapeSolvingErrorHR
    name = "ECapeSolvingError"


class ECapeBadInvOrder(ECapeComputation):
    """A necessary pre-requisite operation was not called before this one."""

    HR = ECapeBadInvOrderHR
    name = "ECapeBadInvOrder"

    def __init__(self):
        super().__init__()
        self._co_requestedOperation = ""

    def _set_co_requested_operation(self, requestedOperation=""):
        self._co_requestedOperation = requestedOperation

    def get_requestedOperation(self):
        return self._co_requestedOperation


class ECapeInvalidOperation(ECapeComputation):
    """This operation is not valid in the current context. No extra state."""

    HR = ECapeInvalidOperationHR
    name = "ECapeInvalidOperation"


# ---------------------------------------------------------------------------
# ECapePersistence hierarchy (3.3.22 - 3.3.26)
# ---------------------------------------------------------------------------
class ECapePersistence(ECapeUser):
    """Base of the errors related to persistence."""

    HR = ECapePersistenceHR
    name = "ECapePersistence"


class ECapePersistenceOverflow(ECapePersistence):
    """There is an overflow of the internal persistence system. No extra state."""

    HR = ECapePersistenceOverflowHR
    name = "ECapePersistenceOverflow"


class ECapeIllegalAccess(ECapePersistence):
    """Access to something within the persistence system is not authorised."""

    HR = ECapeIllegalAccessHR
    name = "ECapeIllegalAccess"


class ECapePersistenceNotFound(ECapePersistence):
    """The requested object/table/item within the persistence system was not found."""

    HR = ECapePersistenceNotFoundHR
    name = "ECapePersistenceNotFound"

    def __init__(self):
        super().__init__()
        self._co_itemName = ""

    def _set_co_item_name(self, itemName=""):
        self._co_itemName = itemName

    def get_itemName(self):
        return self._co_itemName


class ECapePersistenceSystemError(ECapePersistence):
    """A severe error occurred within the persistence system. No extra state."""

    HR = ECapePersistenceSystemErrorHR
    name = "ECapePersistenceSystemError"


# ---------------------------------------------------------------------------
# Convenience: HRESULT -> class, useful on the client side (section 6.1.1 pattern):
# cast the failing component's pointer to the interface matching the returned HRESULT.
# ---------------------------------------------------------------------------
HRESULT_TO_ERROR_CLASS = {
    ECapeUnknownHR: ECapeUnknown,
    ECapeDataHR: ECapeData,
    ECapeLicenceErrorHR: ECapeLicenceError,
    ECapeBadCOParameterHR: ECapeBadCOParameter,
    ECapeBadArgumentHR: ECapeBadArgument,
    ECapeInvalidArgumentHR: ECapeInvalidArgument,
    ECapeOutOfBoundsHR: ECapeOutOfBounds,
    ECapeImplementationHR: ECapeImplementation,
    ECapeNoImplHR: ECapeNoImpl,
    ECapeLimitedImplHR: ECapeLimitedImpl,
    ECapeComputationHR: ECapeComputation,
    ECapeOutOfResourcesHR: ECapeOutOfResources,
    ECapeNoMemoryHR: ECapeNoMemory,
    ECapeTimeOutHR: ECapeTimeOut,
    ECapeFailedInitialisationHR: ECapeFailedInitialisation,
    ECapeSolvingErrorHR: ECapeSolvingError,
    ECapeBadInvOrderHR: ECapeBadInvOrder,
    ECapeInvalidOperationHR: ECapeInvalidOperation,
    ECapePersistenceHR: ECapePersistence,
    ECapeIllegalAccessHR: ECapeIllegalAccess,
    ECapePersistenceNotFoundHR: ECapePersistenceNotFound,
    ECapePersistenceSystemErrorHR: ECapePersistenceSystemError,
    ECapePersistenceOverflowHR: ECapePersistenceOverflow,
}
