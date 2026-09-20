"Utilities common to all interfaces"

from ctypes import c_double
from typing import List

from comtypes import BSTR
from comtypes.automation import VARIANT
from comtypes.safearray import _midlSAFEARRAY


def bstr_array_variant(values: List):
    "make array with type VT_ARRAY | VT_BSTR"
    sa = _midlSAFEARRAY(BSTR).create(values)
    return VARIANT(sa)


def r8_array_variant(values: List):
    "make array with type VT_ARRAY | VT_R8"
    sa = _midlSAFEARRAY(c_double).create(values)
    return VARIANT(sa)
