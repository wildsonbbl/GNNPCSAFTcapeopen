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

import re
from typing import List, Optional

from comtypes import COMError

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
from .utils_common import GNNPCSAFTPPbase

# ---------------------------------------------------------------------------
# CAPE-OPEN error handling
# ---------------------------------------------------------------------------
# CAPE-OPEN errors are communicated on the COM side through IErrorInfo.
# We assign each named CAPE-OPEN error from the spec a distinct HRESULT
# (any value with the top "severity" bit set works; these are arbitrary but
# stable, in the vendor-defined range) and set the description text via
# ReportError so a PME reading IErrorInfo.GetDescription() sees the message.


def raise_cape_error(error_cls, message):
    """
    Set rich COM error info (name + description) and raise the matching
    COMError so the calling PME sees an HRESULT it can map back to the
    CAPE-OPEN error named in `error_cls`.
    """
    # ReportError(f"{error_cls.name}: {message}")
    raise COMError(error_cls.HR, message, (error_cls.name, message, None, 0, None))


# ---------------------------------------------------------------------------
# PMC lifecycle states (see spec section 3.4, State diagram)
# ---------------------------------------------------------------------------


class PMCState:
    "PMC lifecycle states"

    NON_INITIALIZED = "non_initialized"
    INITIALIZING = "initializing"
    EXECUTING = "executing"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


# ---------------------------------------------------------------------------
# SMILES collection dialog
# ---------------------------------------------------------------------------

# A conservative SMILES-character check. This is NOT a validity parser for
# SMILES grammar (that's RDKit's job) — it only rejects obviously-wrong
# input (empty strings, stray whitespace-only lines) before you hand the
# list off to your chemistry backend.
_SMILES_CHAR_RE = re.compile(r"^[A-Za-z0-9@+\-\[\]\(\)=#\\/%.:*$]+$")


def _validate_smiles_syntax(smiles):
    """Cheap sanity check; raises ValueError with a human-readable reason."""
    s = smiles.strip()
    if not s:
        raise ValueError("empty SMILES string")
    if not _SMILES_CHAR_RE.match(s):
        raise ValueError(f"'{s}' contains characters not valid in SMILES")
    return s


def _prompt_for_smiles_list() -> Optional[List[str]]:
    """
    Blocking, modal dialog asking the user for one SMILES string per line.
    Returns a list[str] of cleaned SMILES, or None if the user cancelled.

    Implemented with Tkinter (stdlib, no extra dependency). Swap this out
    for a Qt/wx dialog if your PME's host process already has one of those
    GUI toolkits running an event loop.
    """
    import tkinter as tk  # pylint: disable=import-outside-toplevel
    from tkinter import (  # pylint: disable=import-outside-toplevel
        messagebox,
        scrolledtext,
    )

    result = {}
    result["smiles"] = None

    root = tk.Tk()
    root.title("Property Package — Component Definition")
    root.attributes("-topmost", True)

    tk.Label(
        root,
        text="Enter one SMILES string per line for each component\n"
        "this Property Package instance should handle:",
        justify="left",
        padx=10,
        pady=10,
    ).pack(anchor="w")

    text_box = scrolledtext.ScrolledText(root, width=50, height=12)
    text_box.pack(padx=10, pady=(0, 10))
    text_box.focus_set()

    button_frame = tk.Frame(root)
    button_frame.pack(pady=(0, 10))

    def on_ok():
        raw_lines = text_box.get("1.0", "end").splitlines()
        cleaned = []
        errors = []
        for i, line in enumerate(raw_lines, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                cleaned.append(_validate_smiles_syntax(line))
            except ValueError as exc:
                errors.append(f"Line {i}: {exc}")

        if errors:
            messagebox.showerror(
                "Invalid SMILES",
                "Please fix the following before continuing:\n\n" + "\n".join(errors),
            )
            return

        if not cleaned:
            messagebox.showerror(
                "No components entered",
                "Enter at least one SMILES string.",
            )
            return

        result["smiles"] = cleaned
        root.destroy()

    def on_cancel():
        result["smiles"] = None
        root.destroy()

    tk.Button(button_frame, text="OK", width=12, command=on_ok).pack(
        side="left", padx=5
    )
    tk.Button(button_frame, text="Cancel", width=12, command=on_cancel).pack(
        side="left", padx=5
    )

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()

    return result["smiles"]


# ---------------------------------------------------------------------------
# ICapeUtilities
# ---------------------------------------------------------------------------


class ICapeUtilities(GNNPCSAFTPPbase):
    "ICapeUtilities Class with methods implemented"

    def __init__(self):
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
        raise_cape_error(
            ECapeNoImpl, "This Property Package does not expose parameters."
        )

    # -- SetSimulationContext ----------------------------------------------
    def _set_simulationContext(self, simContext):
        """
        Store the reference to the PME's simulation context so it can be
        used later (e.g. to create thermo material objects, report
        diagnostics, or use unit conversion services).
        """
        if simContext is None:
            raise_cape_error(ECapeInvalidArgument, "simContext must not be NULL.")
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
        if self._pmc_state != PMCState.NON_INITIALIZED:
            raise_cape_error(
                ECapeBadInvOrder,
                "Initialize() must be called exactly once, before any other method.",
            )

        self._pmc_state = PMCState.INITIALIZING

        try:
            smiles_list = _prompt_for_smiles_list()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._pmc_state = PMCState.NON_INITIALIZED
            raise_cape_error(
                ECapeFailedInitialisation,
                f"Could not display the component-input dialog: {exc}",
            )
            return  # unreachable, raise_cape_error always raises

        if smiles_list is None:
            # User cancelled: this counts as a failed initialization.
            self._pmc_state = PMCState.NON_INITIALIZED
            raise_cape_error(
                ECapeFailedInitialisation,
                "Component definition was cancelled by the user.",
            )
            return

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
            raise_cape_error(
                ECapeBadInvOrder,
                "Terminate() called before a successful Initialize().",
            )
        if self._pmc_state in (PMCState.TERMINATING, PMCState.TERMINATED):
            raise_cape_error(ECapeBadInvOrder, "Terminate() called more than once.")

        self._pmc_state = PMCState.TERMINATING
        try:
            # Free/release secondary objects, caches, external handles, etc.
            self.simulation_context = None
            self.components_smiles = []
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise_cape_error(ECapeUnknown, f"Error while terminating: {exc}")
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
            raise_cape_error(
                ECapeUnknown, "Edit() is only available once the PMC is initialized."
            )

        try:
            new_smiles = _prompt_for_smiles_list()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise_cape_error(ECapeUnknown, f"Could not display the editor: {exc}")
            return

        if new_smiles is not None:
            self.components_smiles = new_smiles
            # NOTE: per UC-004, the PME is responsible for detecting that
            # PMC state (component list) changed after Edit() returns and
            # re-integrating it (e.g. re-checking ports/connections).
