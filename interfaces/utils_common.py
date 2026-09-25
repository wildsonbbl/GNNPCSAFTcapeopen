"Utilities common to all interfaces"

import array
import re
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import psutil
from comtypes import BSTR, COMError
from comtypes.automation import VARIANT, VT_EMPTY
from comtypes.gen import CAPEOPEN110
from comtypes.safearray import _midlSAFEARRAY

from . import ecape_errors
from .ecape_user import ECapeUser

_SMILES_CHAR_RE = re.compile(r"^[A-Za-z0-9@+\-\[\]\(\)=#\\/%.:*$]+$")

proc = psutil.Process()


class GNNPCSAFTPPbase(ECapeUser):
    "ICapeIdentification Class with methods implemented"

    material: Optional[CAPEOPEN110.ICapeThermoMaterial] = None
    components_smiles: List[str]
    pcsaft_parameters: Optional[List[List[float]]] = None
    _kij_matrix: Optional[List[List[float]]] = None
    _pmc_state: str = "non_initialized"
    simulation_context: Optional[CAPEOPEN110.ICapeSimulationContext] = None

    def rss_mb(self):
        "check process memory"
        return proc.memory_info().rss / (1024 * 1024)

    def bstr_array_variant(self, values: List[str]):
        "make array with type VT_ARRAY | VT_BSTR"
        sa = _midlSAFEARRAY(BSTR).from_param(list(values))
        bstr_array = VARIANT(sa)
        return bstr_array

    def r8_array_variant(self, values: List[float]):
        "make array with type VT_ARRAY | VT_R8"
        sa = array.array("d", list(values))
        r8_array = VARIANT(sa)
        return r8_array

    def i4_array_variant(self, values: List[int]):
        "make array with type VT_ARRAY | VT_I4"
        sa = array.array("l", list(values))
        i4_array = VARIANT(sa)
        return i4_array

    def empty_array_variant(self):
        "make empty array"
        empty_array = VARIANT()
        empty_array.vt = VT_EMPTY
        return empty_array

    def _require_components(self, interfaceName, operation):
        if self.pcsaft_parameters is None:
            error_message = (
                "The GNNPCSAFT Property Package requires initialization"
                " to receive SMILES strings to estimate PC-SAFT parameters."
            )
            self.raise_cape_error(
                ecape_errors.ECapeBadInvOrder,
                error_message,
                interfaceName=interfaceName,
                operation=operation,
            )

    def _require_material(self, interfaceName, operation):
        self._require_components(
            interfaceName=interfaceName,
            operation=operation,
        )
        if self.material is None:
            error_message = (
                "SetMaterial (ICapeThermoMaterialContext) must be called before"
                " requesting a calculation"
            )
            self.raise_cape_error(
                ecape_errors.ECapeBadInvOrder,
                error_message,
                interfaceName=interfaceName,
                operation=operation,
            )

    # ---------------------------------------------------------------------------
    # SMILES collection dialog
    # ---------------------------------------------------------------------------

    # A conservative SMILES-character check. This is NOT a validity parser for
    # SMILES grammar (that's RDKit's job) — it only rejects obviously-wrong
    # input (empty strings, stray whitespace-only lines) before you hand the
    # list off to your chemistry backend.

    def _validate_smiles_syntax(self, smiles):
        """Cheap sanity check; raises ValueError with a human-readable reason."""
        s = smiles.strip()
        if not s:
            raise ValueError("empty SMILES string")
        if not _SMILES_CHAR_RE.match(s):
            raise ValueError(f"'{s}' contains characters not valid in SMILES")
        return s

    def _prompt_for_smiles_list(self) -> Optional[List[str]]:
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
                    cleaned.append(self._validate_smiles_syntax(line))
                except ValueError as exc:
                    errors.append(f"Line {i}: {exc}")

            if errors:
                messagebox.showerror(
                    "Invalid SMILES",
                    "Please fix the following before continuing:\n\n"
                    + "\n".join(errors),
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
        # CAPE-OPEN error handling
        # ---------------------------------------------------------------------------
        # CAPE-OPEN errors are communicated on the COM side through IErrorInfo.
        # We assign each named CAPE-OPEN error from the spec a distinct HRESULT
        # (any value with the top "severity" bit set works; these are arbitrary but
        # stable, in the vendor-defined range) and set the description text via
        # ReportError so a PME reading IErrorInfo.GetDescription() sees the message.

    def raise_cape_error(
        self,
        error_cls,
        description="N/A",
        scope="N/A",
        interfaceName="N/A",
        operation="N/A",
        moreInfo="N/A",
    ):
        """
        Set rich COM error info (name + description) and raise the matching
        COMError so the calling PME sees an HRESULT it can map back to the
        CAPE-OPEN error named in `error_cls`.
        """
        self._set_co_error(
            name=error_cls.name,
            code=1,
            description=description,
            scope=scope,
            interfaceName=interfaceName,
            operation=operation,
            moreInfo=moreInfo,
        )
        raise COMError(
            error_cls.HR, description, (error_cls.name, description, None, 0, None)
        )

    @staticmethod
    def _as_list(value):
        if value is None:
            return []
        return (
            list(value)
            if isinstance(value, (list, tuple))
            else value.tolist() if isinstance(value, np.ndarray) else [value]
        )

    def _get_tp_fraction(self, phaseLabel):
        temperature, pressure, fractions = self.material.GetTPFraction(  # type: ignore
            phaseLabel,
        )
        return (
            float(temperature),
            float(pressure),
            self._reorder_to_internal(list(fractions)),
        )

    def _compound_order(self):
        """Map the Material Object's compound order onto our own, so calls
        that pull composition data from the Material line up with the order
        self.pcsaft_parameters/self._kij_matrix were built in."""

        material_ids = list(self.components_smiles)
        if len(material_ids) != len(self.components_smiles):
            self.raise_cape_error(
                error_cls=ecape_errors.ECapeInvalidArgument,
                description="The Material Object's compound list does not match the "
                "compounds configured on this Property Package",
                interfaceName="ICapeThermoPropertyRoutine",
                operation="CalcSinglePhaseProp",
            )
        lower_names = [n.lower() for n in self.components_smiles]
        order = []
        for cid in material_ids:
            try:
                order.append(lower_names.index(str(cid).lower()))
            except ValueError:
                self.raise_cape_error(
                    error_cls=ecape_errors.ECapeInvalidArgument,
                    description=f"Material compound {cid!r} is not configured on this "
                    "Property Package",
                    interfaceName="ICapeThermoPropertyRoutine",
                    operation="CalcSinglePhaseProp",
                )
        return order

    def _reorder_to_internal(self, material_values):
        order = self._compound_order()
        internal = [0.0] * len(order)
        for material_pos, internal_pos in enumerate(order):
            internal[internal_pos] = material_values[material_pos]
        return internal

    def _get_overall_scalar(self, prop):
        values = self.material.GetOverallProp(prop, None)  # type: ignore
        values = self._as_list(values)
        return float(values[0])

    def _get_overall_fractions(self):
        values = self.material.GetOverallProp("fraction", "Mole")  # type: ignore
        values = self._as_list(values)
        return self._reorder_to_internal(values)

    @staticmethod
    def _phase_attr(phase, names):
        for name in names:
            value = getattr(phase, name, None)
            if value is not None:
                return float(value)
        return None


# ---------------------------------------------------------------------------
# PMC lifecycle states (see spec section 3.4, State diagram)
# ---------------------------------------------------------------------------


@dataclass
class PMCState:
    "PMC lifecycle states"

    NON_INITIALIZED = "non_initialized"
    INITIALIZING = "initializing"
    EXECUTING = "executing"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
