'''
AL USDMaya utility scripts. 

This should eventually move into the AL_usdmaya plugin.
'''
import pymel.core as pm


AL_MAYA_PLUGIN = 'AL_USDMayaPlugin'


class NoProxyShapeError(ValueError):
    pass


def loadAndImportALUsdMaya():
    if not pm.pluginInfo(AL_MAYA_PLUGIN, q=1, loaded=1):
        pm.loadPlugin(AL_MAYA_PLUGIN)
    import AL.usdmaya
    return AL


def getProxyShape(error=True):
    '''Return a proxyShape to use for a ui given the current maya context
    
    Will first attempt to find the first proxy shape within the current
    selection, and if none are found there, will check to see if exactly one
    exists in the scene.
    
    Parameters
    ----------
    error : bool
        if False, and we can't find a (singular) proxyShape, return None;
        otherwise, a NoProxyShapeError will be raised
    '''
    proxyShape = None
    if pm.pluginInfo(AL_MAYA_PLUGIN, q=1, loaded=1):
        for node in pm.ls(orderedSelection=True):
            if type(node) == pm.nt.Transform:
                node = node.getShape()
            if node and isinstance(node, pm.nt.AL_usdmaya_ProxyShape):
                proxyShape = node
                break
        if proxyShape is None:
            shapes = pm.ls(type='AL_usdmaya_ProxyShape')
            if len(shapes) == 1:
                proxyShape = shapes[0]
    if proxyShape is None and error:
        raise NoProxyShapeError(
            'Could not resolve a single AL_usdmaya_ProxyShape node in the '
            'current selection / selection.')
    return proxyShape


def getProxyShapeStage(proxyShape):
    '''
    Get the python stage used by a proxyShape.

    Parameters
    ----------
    proxyShape : pm.nt.AL_usdmaya_ProxyShape

    Returns
    -------
    Usd.Stage
    '''
    import AL.usdmaya
    shapeObj = AL.usdmaya.ProxyShape.getByName(proxyShape.name())
    stage = None
    if shapeObj:
        stage = shapeObj.getUsdStage()
    if not stage:
        raise ValueError('Could not find stage for node {0}'.format(proxyShape))
    return stage
