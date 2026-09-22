"""
ICapeUtilities implementation for a CAPE-OPEN Property Package built with
comtypes.

Usage
-----
    from comtypes.gen import CAPEOPEN110
    from cape_utilities import CapeUtilitiesMixin

    class MyPropertyPackage(CapeUtilitiesMixin, COMObject):
        _com_interfaces_ = [
            CAPEOPEN110.ICapeUtilities,
            CAPEOPEN110.ICapeIdentification,
            CAPEOPEN110.ICapeThermoPropertyPackage,
            # ... your other CO interfaces ...
        ]

        def __init__(self):
            super().__init__()
            CapeUtilitiesMixin.__init__(self)   # sets up state + components_smiles

After Initialize() succeeds, self.components_smiles is a list[str] of the
SMILES strings the user entered, ready to be consumed by the rest of your
Property Package (building the component list, calling RDKit, etc.).
"""

try:
    from comtypes.gen import CAPEOPEN110 as _CO
except ImportError:
    # Fall back name if your generated wrapper module is called differently
    # (e.g. CAPEOPEN100). Adjust the import above to match your environment.
    _CO = None


from gnnepcsaft_mcp_server.utils import predict_pcsaft_parameters

from .ecape_errors import (
    ECapeBadInvOrder,
    ECapeFailedInitialisation,
    ECapeInvalidArgument,
    ECapeNoImpl,
    ECapeUnknown,
)
from .utils_common import GNNPCSAFTPPbase, PMCState

# ---------------------------------------------------------------------------
# ICapeUtilities
# ---------------------------------------------------------------------------


class ICapeUtilities(GNNPCSAFTPPbase):
    "ICapeUtilities Class with methods implemented"

    def __init__(self):
        super().__init__()
        self._pmc_state = PMCState.NON_INITIALIZED
        self.simulation_context = None
        self.components_smiles = []

    # -- GetParameters -----------------------------------------------------
    def _get_parameters(self):
        """
        This Property Package does not expose CO public parameters.
        Per spec section 3.6.1, raising ECapeNoImpl is the correct behaviour
        for a PMC that supports the concept in general but has nothing to
        expose (as opposed to returning an empty ICapeCollection, which is
        also legal if you'd rather build a real, empty collection object —
        see the spec's note under 5.1 if you need that variant instead).
        """
        self.raise_cape_error(
            error_cls=ECapeNoImpl,
            description="This Property Package does not expose parameters.",
            interfaceName="ICapeUtilities",
            operation="GetParameters",
        )

    # -- SetSimulationContext ----------------------------------------------
    def _set_simulationContext(self, simContext):
        """
        Store the reference to the PME's simulation context so it can be
        used later (e.g. to create thermo material objects, report
        diagnostics, or use unit conversion services).
        """
        if simContext is None:
            self.raise_cape_error(
                ECapeInvalidArgument,
                "simContext must not be NULL.",
                interfaceName="ICapeUtilities",
                operation="SetSimulationContext",
            )
        self.simulation_context = simContext

    # -- Initialize ----------------------------------------------------------
    def Initialize(self):
        """
        First method the PME is guaranteed to call (besides low-level
        construction). Here we collect the list of components as SMILES
        strings from the user and store them in self.components_smiles.

        On any failure we free whatever we allocated and raise
        ECapeFailedInitialisation, per spec: after this, the PME must not
        call Terminate() and may only release us via native COM mechanisms.
        """
if self.components_smiles is not None and self.pcsaft_parameters is not None:
            self._pmc_state = PMCState.EXECUTING
            return

        if self._pmc_state != PMCState.NON_INITIALIZED:
            self.raise_cape_error(
                ECapeBadInvOrder,
                "Initialize() must be called exactly once, before any other method.",
                interfaceName="ICapeUtilities",
                operation="Initialize",
                moreInfo="Tried to `Initialize` twice. Restart the GNNPCSAFT Property Package and"
                " make sure it's initialized only the first time.",
            )

        self._pmc_state = PMCState.INITIALIZING

        try:
            smiles_list = self._prompt_for_smiles_list()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._pmc_state = PMCState.NON_INITIALIZED
            self.raise_cape_error(
                ECapeFailedInitialisation,
                f"Could not display the component-input dialog: {exc}",
                interfaceName="ICapeUtilities",
                operation="Initialize",
            )

        if smiles_list is None:
            # User cancelled: this counts as a failed initialization.
            self._pmc_state = PMCState.NON_INITIALIZED
            self.raise_cape_error(
                ECapeFailedInitialisation,
                "Component definition was cancelled by the user.",
                interfaceName="ICapeUtilities",
                operation="Initialize",
            )

        self.components_smiles = smiles_list
        self.pcsaft_parameters = [
            predict_pcsaft_parameters(smiles) for smiles in self.components_smiles
        ]
        self._pmc_state = PMCState.EXECUTING

    # -- Terminate -----------------------------------------------------------
    def Terminate(self):
        """
        Last method the client is guaranteed to call (besides low-level
        destruction). May only be called once, and only after a successful
        Initialize().
        """
        if self._pmc_state == PMCState.NON_INITIALIZED:
            self.raise_cape_error(
                ECapeBadInvOrder,
                "Terminate() called before a successful Initialize().",
                interfaceName="ICapeUtilities",
                operation="Terminate",
                moreInfo="The GNNPCSAFT Property Package requires initialization"
                " to receive SMILES strings to estimate PC-SAFT parameters.",
            )
        if self._pmc_state in (PMCState.TERMINATING, PMCState.TERMINATED):
            self.raise_cape_error(
                ECapeBadInvOrder,
                "Terminate() called more than once.",
                interfaceName="ICapeUtilities",
                operation="Terminate",
            )

        self._pmc_state = PMCState.TERMINATING
        try:
            # Free/release secondary objects, caches, external handles, etc.
            self.simulation_context = None
            self.components_smiles = []
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.raise_cape_error(
                ECapeUnknown,
                f"Error while terminating: {exc}",
                interfaceName="ICapeUtilities",
                operation="Terminate",
            )
        finally:
            self._pmc_state = PMCState.TERMINATED

    # -- Edit ------------------------------------------------------------
    def Edit(self):
        """
        Show a custom GUI. Here we simply re-open the same SMILES editor,
        pre-filled with the current component list, and update
        self.components_smiles if the user confirms changes.

        Note: per spec 5.2, Edit is not expected to be supported over
        CORBA (host/UI coupling); raise ECapeUnknown there if needed.
        """
        if self._pmc_state != PMCState.EXECUTING:
            self.raise_cape_error(
                ECapeUnknown,
                "Edit() is only available once the PMC is initialized.",
                interfaceName="ICapeUtilities",
                operation="Edit",
            )

        try:
            new_smiles = self._prompt_for_smiles_list()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.raise_cape_error(
                ECapeUnknown,
                f"Could not display the editor: {exc}",
                interfaceName="ICapeUtilities",
                operation="Edit",
            )
            return

        if new_smiles is not None:
            self.components_smiles = new_smiles
            # NOTE: per UC-004, the PME is responsible for detecting that
            # PMC state (component list) changed after Edit() returns and
            # re-integrating it (e.g. re-checking ports/connections).
