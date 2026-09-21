"""
ECapeUser (+ ECapeRoot) implementation for a CAPE-OPEN component built with comtypes.

Per the CAPE-OPEN "Error Common Interface" spec (section 3.3.1 / 3.3.2), ECapeUser is
the base class of all CO user errors and defines the minimum state every CO error must
carry: code, description, scope, interfaceName, operation, moreInfo. It in turn derives
conceptually from ECapeRoot, which contributes a single "name" field.

Both ECapeRoot and ECapeUser are ABSTRACT in the conceptual model -- no component ever
raises "an ECapeUser" directly. Instead, concrete error interfaces (ECapeBadArgument,
ECapeInvalidArgument, ECapeTimeOut, ...) derive from it. Since COM/MIDL has no interface
inheritance, section 5.1.2 requires that any component supporting a concrete error
interface implement ALL of its ancestor interfaces itself -- so this class exists to be
mixed in wherever you implement one of those concrete error interfaces (and ultimately
into your property package COMObject, which is expected to support every error interface
it is capable of raising).

Usage:
    class ECapeInvalidArgument(ECapeUserImpl):
        # concrete error-specific state/methods go here
        ...

    class MyPropertyPackage(ECapeUserImpl, ECapeInvalidArgument, ..., comtypes.COMObject):
        _com_interfaces_ = [IECapeUser, IECapeInvalidArgument, ...]

        def SomeCOOperation(self, ...):
            if bad_thing:
                self._set_co_error(
                    name="ECapeInvalidArgument",
                    code=1,
                    description="phase name not in CO Phase List",
                    scope="CapeOpen::Common::Error",
                    interfaceName="ICapeThermoPropertyPackage",
                    operation="SomeCOOperation",
                )
                return ECapeInvalidArgumentHR   # HRESULT from the table in section 5.1.2

NOTE ON METHOD NAMES:
The method names below (get_name, get_code, ...) match how comtypes typically expects
a [propget] IDL attribute named "code" to be implemented when there's no naming clash.
If comtypes generated prefixed names for your typelib (e.g. because you implement several
interfaces that each declare a "code"-like attribute), comtypes will have named the stubs
something like `ECapeUser_code` instead -- check your comtypes.gen module for the exact
names it expects and rename the methods here to match.
"""


class ECapeUserImpl:
    """Mixin supplying the ECapeRoot/ECapeUser state and property getters."""

    def __init__(self):
        # ECapeRoot
        self._co_error_name = "N/A"
        # ECapeUser
        self._co_error_code = 0
        self._co_error_description = "N/A"
        self._co_error_scope = "N/A"
        self._co_error_interfaceName = "N/A"
        self._co_error_operation = "N/A"
        self._co_error_moreInfo = "N/A"

    def _set_co_error(
        self,
        name="N/A",
        code=0,
        description="N/A",
        scope="N/A",
        interfaceName="N/A",
        operation="N/A",
        moreInfo="N/A",
    ):
        """
        Populate the CO error state. Call this right before returning the failing
        HRESULT for the concrete error interface you're raising (interfaceName and
        operation are mandatory fields per the spec).
        """
        self._co_error_name = name
        self._co_error_code = code
        self._co_error_description = description
        self._co_error_scope = scope
        self._co_error_interfaceName = interfaceName
        self._co_error_operation = operation
        self._co_error_moreInfo = moreInfo

    # ------------------------------------------------------------------
    # ECapeRoot
    # ------------------------------------------------------------------
    def get_name(self):
        """A short description of the error. Mandatory field."""
        return self._co_error_name

    # ------------------------------------------------------------------
    # ECapeUser
    # ------------------------------------------------------------------
    def _get_code(self):
        """Implementation-specific subcategory code (proprietary)."""
        return self._co_error_code

    def _get_description(self):
        """The description of the error."""
        return self._co_error_description

    def _get_scope(self):
        """The scope of the error, e.g. 'CapeOpen::Common::Identification'."""
        return self._co_error_scope

    def _get_interfaceName(self):
        """The name of the interface where the error is thrown. Mandatory field."""
        return self._co_error_interfaceName

    def _get_operation(self):
        """The name of the operation where the error is thrown. Mandatory field."""
        return self._co_error_operation

    def _get_moreInfo(self):
        """URL to further information about the error (implementation dependent)."""
        return self._co_error_moreInfo
