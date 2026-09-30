"""
IPersistStreamInit implementation for a CAPE-OPEN Property Package built
with comtypes.

Why this exists
----------------
Per the CAPE-OPEN "Persistence Common Interface" specification (section
4.1) and its Errata/Clarifications document (clarification 3), a PMC that
wants a PME to save/restore its configuration instead of re-asking the
user for it every session must implement IPersistStream or
IPersistStreamInit. IPersistStreamInit is preferred because it also gets
an InitNew() call when the PMC is created fresh (as opposed to reloaded),
which VB6-era PMEs rely on -- the Errata explicitly says PMCs "should not
raise an error if both the InitNew and Load methods are called".

Crucially, both InitNew and Load are guaranteed by the COM middleware
life-cycle to be called *before* ICapeUtilities.Initialize() (see the main
spec, section 4.1: "even Initialize method ... will be called after
invoking the methods InitNew and Load"). So Initialize() just needs to
check whether Load() already gave it a component list, and skip the
SMILES-entry dialog if so.

What gets persisted
--------------------
Per the Errata (clarification 4, "What should be saved and restored?"):
"There is no need to persist data that can be reconstructed by the PMC to
the same state it was in at the time the PMC was saved." PC-SAFT
parameters are a deterministic function of a SMILES string, so we do NOT
persist self.pcsaft_parameters -- we recompute it from the restored SMILES
list via the existing _config_gnnpcsaft() helper, same as Initialize()
does for a freshly-entered component list. We DO persist:
  - self.components_smiles (cannot be reconstructed -- it's user input)
  - the kij values (cannot be reconstructed -- also user input)

Stream format
-------------
A small versioned, self-describing binary blob (little-endian):
    4 bytes   magic       b"GPS1"
    int32     version     format version, currently 1
    int32     n_components
    per component:
        int32   len(utf8 bytes)
        bytes   utf8-encoded SMILES string
    int32     n_kij_values   (== n*(n-1)/2 for n components)
    n_kij_values * float64   kij values, in the same flat upper-triangle
                             order (i<j, i outer loop) that
                             ICapeUtilities._config_gnnpcsaft expects.
"""

import ctypes
import logging
import struct
from ctypes import c_ubyte

from comtypes import COMMETHOD, GUID, HRESULT, IUnknown
from comtypes.stream import ISequentialStream

from .ecape_errors import ECapeUnknown
from .utils_common import GNNPCSAFTPPbase

_FORMAT_MAGIC = b"GPS1"
_FORMAT_VERSION = 1
_READ_CHUNK = 65536


class IStream(ISequentialStream):
    """Minimal binding for the standard OLE IStream interface.

    IStream's vtable is IUnknown (3 slots) + ISequentialStream's Read/
    Write (2 slots) + Seek/SetSize/CopyTo/Commit/Revert/LockRegion/
    UnlockRegion/Stat/Clone. We only ever call Read/Write, and those sit
    at the same vtable offset in IStream as they do in ISequentialStream
    (right after IUnknown), so inheriting ISequentialStream without
    redeclaring the rest of IStream's methods is enough to call them
    safely -- we simply never reach the undeclared slots.
    """

    _iid_ = GUID("{0000000C-0000-0000-C000-000000000046}")  # IID_IStream


class IPersistStreamInit(IUnknown):
    "IPersistStreamInit implementation"

    _iid_ = GUID("{7FD52380-4E07-101B-AE2D-08002B2EC713}")
    _methods_ = [
        # IPersist method
        COMMETHOD(
            [], HRESULT, "GetClassID", (["out"], ctypes.POINTER(GUID), "pClassID")
        ),
        # IPersistStream / IPersistStreamInit methods
        COMMETHOD([], HRESULT, "IsDirty"),
        COMMETHOD([], HRESULT, "Load", (["in"], ctypes.POINTER(IStream), "pStm")),
        COMMETHOD(
            [],
            HRESULT,
            "Save",
            (["in"], ctypes.POINTER(IStream), "pStm"),
            (["in"], ctypes.c_int, "fClearDirty"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetSizeMax",
            (["out"], ctypes.POINTER(ctypes.c_ulonglong), "pcbSize"),
        ),
        COMMETHOD([], HRESULT, "InitNew"),
    ]


class ICapePersistence(GNNPCSAFTPPbase):
    """Implements IPersistStreamInit so a PME can save/restore the
    component (SMILES) list and kij matrix without re-prompting the user
    on every load.
    """

    def __init__(self):
        super().__init__()
        self._dirty = False

    # -- IPersist ------------------------------------------------------
    def GetClassID(self):
        """Return this PMC's registered CLSID."""
        logging.debug("---> TRYING TO GetClassID <---")
        clsid = getattr(type(self), "_reg_clsid_", None)
        if clsid is None:
            self.raise_cape_error(
                ECapeUnknown,
                "No CLSID registered for this Property Package.",
                interfaceName="IPersistStreamInit",
                operation="GetClassID",
            )
        return GUID(clsid)

    # -- IPersistStreamInit ---------------------------------------------
    def IsDirty(self):
        """
        S_OK (0) means dirty, S_FALSE (1) means unchanged since last
        Save()/Load()/InitNew().

        Default S_OK: always "dirty"; the payload is tiny, so saving unconditionally is cheap
        """
        logging.debug("---> TRYING TO IsDirty <---")
        return 0

    def InitNew(self):
        """Called by the PME when creating a brand-new (not restored)
        instance. Reset to an empty, unconfigured state so
        ICapeUtilities.Initialize() knows to prompt the user, per the
        Errata's note that InitNew and Load may both be called and a PMC
        should not error out over that.
        """
        logging.debug("---> TRYING TO InitNew <---")
        self.components_smiles = None
        self.pcsaft_parameters = None
        self._kij_matrix = None
        self._dirty = False
        return 0

    def Load(self, stream):
        """Restore components_smiles / kij from a previously Save()'d
        stream, then rebuild pcsaft_parameters and _kij_matrix via the
        same path Initialize()/Edit() use for freshly-entered data.
        """
        logging.debug("---> TRYING TO LOAD <---")
        try:
            data = self._stream_read_all(stream)
            smiles_list, kij_values = self._deserialize(data)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.raise_cape_error(
                ECapeUnknown,
                f"Could not restore persisted component data: {exc}",
                interfaceName="IPersistStreamInit",
                operation="Load",
            )

        if smiles_list:
            self._config_gnnpcsaft(smiles_list, kij_values)
        else:
            self.components_smiles = None
            self.pcsaft_parameters = None
            self._kij_matrix = None

        self._dirty = False
        return 0

    def Save(self, stream, clear_dirty):
        """Persist components_smiles and the kij values. pcsaft_parameters
        is intentionally NOT persisted -- it's reconstructed on Load()."""
        logging.debug("---> TRYING TO SAVE <---")
        try:
            data = self._serialize(self.components_smiles, self._flatten_kij())
            self._stream_write_all(stream, data)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.raise_cape_error(
                ECapeUnknown,
                f"Could not save component data: {exc}",
                interfaceName="IPersistStreamInit",
                operation="Save",
            )

        if clear_dirty:
            self._dirty = False
        return 0

    def GetSizeMax(self):
        """Upper bound (here, exact size) in bytes of the stream Save()
        would produce right now."""
        logging.debug("---> TRYING TO GetSizeMax <---")
        data = self._serialize(self.components_smiles, self._flatten_kij())
        return len(data)

    # -- call this from Initialize()/Edit() after _config_gnnpcsaft -----
    def _mark_dirty(self):
        self._dirty = True

    # -- serialization helpers -------------------------------------------
    def _flatten_kij(self):
        """Flatten self._kij_matrix back into the (i<j) upper-triangle
        list that _config_gnnpcsaft's kij_values parameter expects, i.e.
        the inverse of the matrix-building loop in ICapeUtilities."""
        matrix = getattr(self, "_kij_matrix", None) or []
        n = len(matrix)
        values = []
        for i in range(n):
            for j in range(i + 1, n):
                values.append(matrix[i][j])
        return values

    @staticmethod
    def _serialize(smiles_list, kij_values):
        buf = bytearray()
        buf += _FORMAT_MAGIC
        buf += struct.pack("<i", _FORMAT_VERSION)
        buf += struct.pack("<i", len(smiles_list))
        for smiles in smiles_list:
            encoded = smiles.encode("utf-8")
            buf += struct.pack("<i", len(encoded))
            buf += encoded
        buf += struct.pack("<i", len(kij_values))
        for value in kij_values:
            buf += struct.pack("<d", value)
        return bytes(buf)

    @staticmethod
    def _deserialize(data):
        offset = 0
        magic = data[offset : offset + 4]
        offset += 4
        if magic != _FORMAT_MAGIC:
            raise ValueError("Unrecognised persistence stream format.")

        (version,) = struct.unpack_from("<i", data, offset)
        offset += 4
        if version != _FORMAT_VERSION:
            raise ValueError(f"Unsupported persistence format version: {version}")

        (n_components,) = struct.unpack_from("<i", data, offset)
        offset += 4
        smiles_list = []
        for _ in range(n_components):
            (str_len,) = struct.unpack_from("<i", data, offset)
            offset += 4
            smiles_list.append(data[offset : offset + str_len].decode("utf-8"))
            offset += str_len

        (n_kij,) = struct.unpack_from("<i", data, offset)
        offset += 4
        kij_values = list(struct.unpack_from(f"<{n_kij}d", data, offset))
        offset += n_kij * 8

        return smiles_list, kij_values

    # -- raw IStream I/O ---------------------------------------------------
    @staticmethod
    def _stream_read_all(istream):
        chunks = []
        while True:
            pv, bytes_read = istream.RemoteRead(_READ_CHUNK)
            if bytes_read == 0:
                break
            chunks.append(bytes(bytearray(pv)[:bytes_read]))
            if bytes_read < _READ_CHUNK:
                break
        return b"".join(chunks)

    @staticmethod
    def _stream_write_all(istream, data):
        buf = (c_ubyte * len(data)).from_buffer_copy(data)
        istream.RemoteWrite(buf, len(data))
