"Utilities common to all interfaces"

import array
from ctypes import c_double
from typing import List

from comtypes import BSTR
from comtypes.automation import VARIANT
from comtypes.safearray import _midlSAFEARRAY

from .ICapeExceptions import ECapeBadInvOrder


def bstr_array_variant(values: List):
    "make array with type VT_ARRAY | VT_BSTR"
    sa = _midlSAFEARRAY(BSTR).from_param(values)
    bstr_array = VARIANT(sa)
    return bstr_array


def r8_array_variant(values: List):
    "make array with type VT_ARRAY | VT_R8"
    sa = array.array("d", values)
    r8_array = VARIANT(sa)
    return r8_array


def _require_components(self):
    if not self.pcsaft_parameters:
        raise ECapeBadInvOrder("Call SetComponents before using this Property Package")


def _require_material(self):
    _require_components(self)
    if self.material is None:
        raise ECapeBadInvOrder(
            "SetMaterial (ICapeThermoMaterialContext) must be called before"
            " requesting a calculation"
        )
