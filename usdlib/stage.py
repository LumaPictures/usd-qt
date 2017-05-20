'''Generic (non-luma) usd utilities'''

from pxr import Usd, Sdf, Kind

from typing import Dict, Iterator, List, NamedTuple, Optional, Tuple, Union


def getStage(usdFile, variantOverrides=None, loadAll=False, stageCache=None):
    '''
    Open a stage from a USD file path, optionally populating the session layer
    with variant overrides.

    Parameters
    ----------
    usdFile : str
    variantOverrides : Optional[Dict[str, Dict[str, str]]]
        Dict[primPath, Dict[variantSetName, selectedVariant]] as returned
        by `getVariantSelections()`
    loadAll : Optional[bool]
    stageCache : Optional[Usd.StageCache]

    Returns
    -------
    Usd.Stage
    '''
    # TODO: Implement PopulationMask support
    if stageCache is not None:
        assert isinstance(stageCache, Usd.StageCache)
        ctxArg = stageCache
    else:
        ctxArg = Usd.BlockStageCaches

    with Usd.StageCacheContext(ctxArg):
        loadSet = Usd.Stage.LoadAll if loadAll else Usd.Stage.LoadNone
        if variantOverrides:
            rootLayer = Sdf.Layer.FindOrOpen(usdFile)
            assert rootLayer
            sessionLayer = Sdf.Layer.CreateAnonymous()
            for primPath, variantSelections in variantOverrides.iteritems():
                sdfPath = Sdf.Path(primPath)
                primSpec = Sdf.CreatePrimInLayer(sessionLayer,
                                                 sdfPath.GetPrimPath())
                # FIXME: If any of these selections no longer exists or is
                # invalid it could result in a prim not being found when we
                # populate the asset manager. Either take performance hit to
                # check, or add a way to clean out stale selections.
                primSpec.variantSelections.update(variantSelections)
            stage = Usd.Stage.Open(rootLayer, sessionLayer, loadSet)
            stage.SetEditTarget(sessionLayer)
        else:
            stage = Usd.Stage.Open(usdFile, loadSet)
            assert stage
            stage.SetEditTarget(stage.GetSessionLayer())
    return stage


def iterPrimReferencesOnLayer(layer):
    '''
    Yields references defined in a layer.

    Parameters
    ----------
    layer : Union[str, Sdf.Layer]

    Returns
    -------
    Iterator[Tuple[Sdf.PrimSpec, Sdf.Reference]]
    '''
    if isinstance(layer, basestring):
        layer = Sdf.Layer.FindOrOpen(layer)

    if not layer:
        return

    stack = [layer.pseudoRoot]
    while stack:
        primSpec = stack.pop()
        refs = primSpec.referenceList.addedOrExplicitItems
        if refs:
            yield (primSpec, refs)

        if primSpec.variantSets:
            # follow selected variants down and add those prim specs to be
            # inspected.
            for variantSet, selection in primSpec.variantSelections.iteritems():
                path = '%s{%s=%s}' % (primSpec.path, variantSet, selection)
                prim = layer.GetPrimAtPath(path)
                if prim:
                    stack.append(prim)

        # TODO: Payloads also need special handling. See the function this
        # is based on: _GatherPrimAssetReferences in sdf/layer.cpp

        stack.extend(primSpec.nameChildren)


def defineParentXforms(stage, primPath):
    '''
    Ensure parent group prims are built.

    Parameters
    ----------
    stage : Sdf.Stage
    primPath : str
    '''
    # this is from the usd tutorial...
    from pxr import UsdGeom
    path = ''
    parentPrims = primPath.strip('/').split('/')[:-1]
    for nextPrim in parentPrims:
        path += ('/' + nextPrim)
        # Make sure the model-parents we need are well-specified
        Usd.ModelAPI(UsdGeom.Xform.Define(stage, path)).SetKind(
            Kind.Tokens.group)
