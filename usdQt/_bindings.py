from . import _usdQt
from pxr import Tf
Tf.PrepareModule(_usdQt, locals())
del _usdQt, Tf

try:
    import __DOC
    __DOC.Execute(locals())
    del __DOC
except Exception:
    try:
        import __tmpDoc
        __tmpDoc.Execute(locals())
        del __tmpDoc
    except:
        pass