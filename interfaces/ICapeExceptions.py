"Module for ICape Exceptions"

# pylint: disable=missing-class-docstring


class CapeError(Exception):
    """Base class for the standard CAPE-OPEN error identifiers."""

    name = "ECapeUnknown"


class ECapeNoImpl(CapeError):
    name = "ECapeNoImpl"


class ECapeLimitedImpl(CapeError):
    name = "ECapeLimitedImpl"


class ECapeBadInvOrder(CapeError):
    name = "ECapeBadInvOrder"


class ECapeFailedInitialisation(CapeError):
    name = "ECapeFailedInitialisation"


class ECapeThrmPropertyNotAvailable(CapeError):
    name = "ECapeThrmPropertyNotAvailable"


class ECapeSolvingError(CapeError):
    name = "ECapeSolvingError"


class ECapeInvalidArgument(CapeError):
    name = "ECapeInvalidArgument"


class ECapeOutOfBounds(CapeError):
    name = "ECapeOutOfBounds"


class ECapeUnknown(CapeError):
    name = "ECapeUnknown"
