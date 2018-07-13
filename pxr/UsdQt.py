from pkgutil import extend_path
import imp
import sys
_usdQt = imp.load_module('pxr.UsdQt._usdQt',
                         *imp.find_module('_usdQt',
                                          extend_path([], 'pxr.UsdQt')))
sys.modules['pxr'].UsdQt = sys.modules['pxr.UsdQt']
import pxr.usdQt
# make this module proxy the usdQt package
globals().update(pxr.usdQt.__dict__)

del sys, imp, extend_path
