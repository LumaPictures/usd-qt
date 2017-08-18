'''
AL USDMaya utility scripts. 

This should eventually move into the AL_usdmaya plugin.
'''
import pymel.core as pm


AL_MAYA_PLUGIN = 'AL_USDMayaPlugin'


def loadAndImportALUsdMaya():
    if not pm.pluginInfo(AL_MAYA_PLUGIN, q=1, loaded=1):
        pm.loadPlugin(AL_MAYA_PLUGIN)
    import AL.usdmaya
    return AL


def getProxyShape(proxyShape=None):
    '''Return a proxyShape to use for a ui given the current maya context'''
    if proxyShape is None:
        sel = []
        for node in pm.ls(selection=True):
            if type(node) == pm.nt.Transform:
                node = node.getShape()
            if node.type() == 'AL_usdmaya_ProxyShape':
                sel.append(node)

        if sel:
            proxyShape = sel[0]
    if proxyShape is None:
        shapes = pm.ls(type='AL_usdmaya_ProxyShape')
        if len(shapes) == 1:
            proxyShape = shapes[0]
    if proxyShape is None:
        raise ValueError('Could not resolve a single AL_usdmaya_ProxyShape '
                         'node in the current scene.')
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
    shapeFilePath = proxyShape.getAttr('filePath')
    shapeFilePath = shapeFilePath.strip()
    stageCache = AL.usdmaya.StageCache.Get()
    for stage in stageCache.GetAllStages():
        if not stage.GetRootLayer():
            continue
        if stage.GetRootLayer().identifier == shapeFilePath:
            return stage
    raise ValueError('Could not find stage with root layer matching path '
                     '{0} in AL stage cache'.format(shapeFilePath))
