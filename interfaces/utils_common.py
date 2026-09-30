"Utilities common to all interfaces"

import array
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import psutil
from comtypes import BSTR, COMError
from comtypes.automation import VARIANT, _VariantClear
from comtypes.gen import CAPEOPEN110
from comtypes.safearray import _midlSAFEARRAY
from gnnepcsaft.data.rdkit_util import smilestoinchi
from gnnepcsaft_mcp_server.utils import predict_pcsaft_parameters

from . import ecape_errors
from .ecape_user import ECapeUser

_SMILES_CHAR_RE = re.compile(r"^[A-Za-z0-9@+\-\[\]\(\)=#\\/%.:*$]+$")

proc = psutil.Process()


class OutboundVARIANT(VARIANT):
    """
    Comtypes original VARIANT tries to call oleaut32.VariantClear on all
    VARIANTs, including the ones received by the Property Package. This
    results in a silent crash for trying to clear a memory twice.

    To solve this, _VariantClear needs to be disabled on the comtypes side and
    reactivated here so that it's used only on python-created VARIANTs.
    """

    def __del__(self):
        if self._b_needsfree_:  # pylint: disable = using-constant-test
            _VariantClear(self)


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


class GNNPCSAFTPPbase(ECapeUser):
    "ICapeIdentification Class with methods implemented"

    material: Optional[CAPEOPEN110.ICapeThermoMaterial] = None
    components_smiles: Optional[List[str]] = None
    pcsaft_parameters: Optional[List[List[float]]] = None
    _kij_matrix: Optional[List[List[float]]] = None
    _pmc_state: str = PMCState.NON_INITIALIZED
    simulation_context: Optional[CAPEOPEN110.ICapeSimulationContext] = None

    @staticmethod
    def rss_mb():
        "check process memory"
        return proc.memory_info().rss / (1024 * 1024)

    @staticmethod
    def bstr_array_variant(values: List[str]):
        "make array with type VT_ARRAY | VT_BSTR"
        sa = _midlSAFEARRAY(BSTR).from_param(list(values))
        bstr_array = OutboundVARIANT(sa)
        return bstr_array

    @staticmethod
    def r8_array_variant(values: List[float]):
        "make array with type VT_ARRAY | VT_R8"
        sa = array.array("d", list(values))
        r8_array = OutboundVARIANT(sa)
        return r8_array

    @staticmethod
    def i4_array_variant(values: List[int]):
        "make array with type VT_ARRAY | VT_I4"
        sa = array.array("l", list(values))
        i4_array = OutboundVARIANT(sa)
        return i4_array

    @staticmethod
    def empty_array_variant():
        "make empty array"
        empty_array = OutboundVARIANT()
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

    @staticmethod
    def _validate_smiles_syntax(smiles):
        """Cheap sanity check; raises ValueError with a human-readable reason."""
        s = smiles.strip()
        if not s:
            raise ValueError("empty SMILES string")
        if not _SMILES_CHAR_RE.match(s):
            raise ValueError(f"'{s}' contains characters not valid in SMILES")
        smilestoinchi(smiles=smiles)
        return s

    def _prompt_for_smiles_list(
        self,
    ) -> Tuple[Optional[List[str]], Optional[List[float]]]:
        """
        Blocking, modal dialog asking the user for one SMILES strings in the
        first line and kij values in the second line.

        Returns a list[str] of cleaned SMILES and list[float] of kij,
        or None if the user cancelled.
        """
        import tkinter as tk  # pylint: disable=import-outside-toplevel
        from tkinter import (  # pylint: disable=import-outside-toplevel
            messagebox,
            scrolledtext,
        )

        result = {}
        result["smiles"] = None
        result["kij_values"] = None

        root = tk.Tk()
        root.title("Property Package — Component Definition")
        root.attributes("-topmost", True)

        tk.Label(
            root,
            text="The first line is for SMILES strings separated by empty space"
            " in sequence (SMILES_1 SMILES_2 ...).\n"
            "The second line is for kij values separated by empty space"
            " in sequence (k12 k13 k14 k23 k24 ...).",
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
            smiles_strings = raw_lines[0].split(" ")
            for i, smiles in enumerate(smiles_strings, start=1):
                smiles = smiles.strip()
                if not smiles:
                    continue
                try:
                    cleaned.append(self._validate_smiles_syntax(smiles))
                except ValueError as exc:
                    errors.append(f"Split {i}: {exc}")

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

            cleaned = []
            errors = []
            try:
                kij_values = raw_lines[1].split(" ")
            except IndexError:
                messagebox.showerror(
                    "Invalid kij value",
                    "Enter kij values in the second line",
                )
                return

            for i, kij in enumerate(kij_values, start=1):
                kij = kij.strip()
                if not kij:
                    continue
                try:
                    cleaned.append(float(kij))
                except ValueError as exc:
                    errors.append(f"Split {i}: {exc}")

            if errors:
                messagebox.showerror(
                    "Invalid kij value",
                    "Please fix the following before continuing:\n\n"
                    + "\n".join(errors),
                )
                return

            result["kij_values"] = cleaned
            size = len(result["smiles"])
            expected = (size * (size - 1)) // 2
            if len(result["kij_values"]) != expected:
                messagebox.showerror(
                    "Invalid number of kij values",
                    f"kij values should match the number of SMILES strings"
                    f" to make the {size}x{size} kij matrix.\n\n"
                    f"Expected {expected} kij values (k12 k13 ...),"
                    f" got {len(result["kij_values"])}",
                )
                return

            root.destroy()

        def on_cancel():
            result["smiles"] = None
            result["kij_values"] = None
            root.destroy()

        tk.Button(button_frame, text="OK", width=12, command=on_ok).pack(
            side="left", padx=5
        )
        tk.Button(button_frame, text="Cancel", width=12, command=on_cancel).pack(
            side="left", padx=5
        )

        root.protocol("WM_DELETE_WINDOW", on_cancel)
        root.mainloop()

        return result["smiles"], result["kij_values"]

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
        assert self.components_smiles is not None

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

    def _get_overall_scalar(self, prop, basis=None):
        values = self.material.GetOverallProp(prop, basis)  # type: ignore
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

    def _config_gnnpcsaft(self, smiles_list, kij_values):
        self.components_smiles = smiles_list
        assert self.components_smiles is not None
        self.pcsaft_parameters = [
            predict_pcsaft_parameters(smiles) for smiles in self.components_smiles
        ]
        n = len(smiles_list)
        kij_matrix = [[0.0] * n for _ in range(n)]
        k_idx = 0
        for i in range(n):
            for j in range(i + 1, n):
                kij_matrix[i][j] = kij_values[k_idx]
                kij_matrix[j][i] = kij_values[k_idx]
                k_idx += 1
        self._kij_matrix = kij_matrix
