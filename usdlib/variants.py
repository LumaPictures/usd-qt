'''
Module for setting variants on usd stages.
'''
from abc import abstractmethod, ABCMeta
from collections import OrderedDict, deque

import pxr.Sdf as Sdf
import pxr.Usd as Usd
import pxr.Pcp as Pcp
import pxr.Kind as Kind

import usdlib.utils

from typing import (Any, Dict, Iterable, Iterator, List, Optional, NamedTuple,
                    Tuple, Union)

MULTIPLE_VALUES = '< multiple values >'

PrimVariant = NamedTuple('PrimVariant',
                         [('setName', str),
                          ('variantName', str)])


def iterPrimIndexVariantNodes(prim):
    '''
    Return an iterator over the variant nodes in the given prim's index.

    Parameters
    ----------
    prim : Usd.Prim

    Returns
    -------
    Iterator[Pcp.NodeRef]
    '''
    # Note: The prim index will not include variants that have no selection.
    # consider switching to the new ComputeExpandedPrimIndex() when available
    index = prim.GetPrimIndex()
    stack = deque(index.rootNode.children)
    while stack:
        child = stack.popleft()
        if child.arcType == Pcp.ArcTypeVariant \
                and not child.IsDueToAncestor():
            yield child
        stack.extend(child.children)


def getPrimVariants(prim):
    '''
    Returns a list of tuples representing a prim's variant set names and active
    values, sorted by their opinion "strength" in the prim's index.

    Parameters
    ----------
    prim : Usd.Prim

    Returns
    -------
    List[PrimVariant]
        (setName, variantName) pairs
    '''
    results = []
    seen = set()
    for node in iterPrimIndexVariantNodes(prim):
        setName, setValue = node.path.GetVariantSelection()
        if setName not in seen:
            results.append(PrimVariant(setName, setValue))
            seen.add(setName)
    return results


def getPrimDefaultVariants(prim, sessionLayer):
    '''
    Get the variant selections for a prim if the sessionlayer was muted.

    Note that nested variant defaults are still affected by the choices in
    the sessionLayer.

    Parameters
    ----------
    prim : Usd.Prim
    sessionLayer : Sdf.Layer

    Returns
    -------
    Dict[str, str]
    '''
    defaults = {}
    variantSets = prim.GetVariantSets()
    left = set(variantSets.GetNames())
    for spec in prim.GetPrimStack():
        if not left:
            break
        if spec.layer == sessionLayer or sessionLayer is None:
            sessionSpecified = spec.variantSelections.items()
            for name in left:
                if name not in sessionSpecified:
                    defaults[name] = variantSets.GetVariantSelection(name)
            # we only have to keep searching for ones specified in session
            left.intersection(sessionSpecified)
        else:
            for name, variant in spec.variantSelections.iteritems():
                if name in left:
                    defaults[name] = variant
                    left.remove(name)
    return defaults


def getSelectedVariants(rootPrim):
    '''
    Returns a mapping of all the currently selected variants below a certain
    prim in the stage.

    Parameters
    ----------
    rootPrim : Usd.Prim

    Returns
    -------
    Dict[str, Dict[str, str]]
        { primPath : { variantSetName : selectedVariantName }}
    '''
    selections = {}
    it = iter(Usd.PrimRange(rootPrim))
    for prim in it:
        if prim.HasVariantSets():
            variants = getPrimVariants(prim)
            selections[str(prim.GetPath())] = dict(variants)
        # we shouldn't need to travel below component level.
        if Usd.ModelAPI(prim).GetKind() == Kind.Tokens.component:
            it.PruneChildren()
    return selections


def getStageSelectedVariants(stage, overrides=None):
    '''
    Return all variants selected on a stage with any overrides set on top
    of the defaults.

    Parameters
    ----------
    stage : Usd.Stage
    overrides : Optional[Dict[str, Dict[str, str]]]

    Returns
    -------
    Dict[str, Dict[str, str]]
    '''
    root = stage.GetPseudoRoot()
    defaults = getSelectedVariants(root)
    if overrides:
        for primPath, variants in overrides.iteritems():
            defaults.setdefault(primPath, {}).update(variants)
    return defaults


def layerHasVariantSelection(layer, selection, prim=None):
    """Queries the given layer (or path to a layer) to see if the given prim
    has the given variant selection.

    Uses a layer instead of a stage for efficiency - in order for this check to
    work, all the variant sets / variants you care about must be contained
    within the single layer

    Parameters
    ----------
    layer : Union[str, Sdf.Layer]
    selection : Dict[str, str]
        the variant selection we wish to check for existence, in the form of
        'variantSetName': 'variantSetValue'. Note that the selection does not
        have to be "complete" - you can specify only 2 variant sets, when 3 are
        available (though checking this may be slower than if all variant sets
        are supplied)
    prim : Optional[str]
        the root prim to query - if not given, the default prim is used; if not
        given and there is no default prim, a ValueError is raised

    Returns
    -------
    bool
    """
    if not isinstance(layer, Sdf.Layer):
        layer = Sdf.Layer.FindOrOpen(layer)

    if prim is None:
        prim = layer.defaultPrim
        if not prim:
            raise ValueError("no prim specified, and layer {!r} had no default"
                             " prim".format(layer.identifier))

    return layerPrimHasVariantSelection(layer.rootPrims[prim], selection)


def layerPrimHasVariantSelection(primSpec, selection):
    """Queries the given layer PrimSpec to see if it has the given variant
    selection.

    Parameters
    ----------
    primSpec : Sdf.PrimSpec
        the primSpec to query for the variants
    selection : Dict[str, str]
        the variant selection we wish to check for existence, in the form of
        'variantSetName': 'variantSetValue'. Note that the selection does not
        have to be "complete" - you can specify only 2 variant sets, when 3 are
        available (though checking this may be slower than if all variant sets
        are supplied). Note that any entries whose value is None will b
        silently ignored (ie, filtered out of the dict)

    Returns
    -------
    bool

    Notes
    -----
    Note that for efficiency, this function assumes that selection "order" will
    not change the answer. Ie, suppose you are looking for {"teeth": "large",
    "legs": 2} - and both "teeth" and "legs" variant sets are available at the
    top level. However, suppose that if you pick "teeth" == "large" first, then
    "legs" == "2" is NOT available, but if you pick "legs" == "2" first, then
    "teeth" == "large" IS available. In such a situation, what answer this
    function would give is indeterminate.  However, I'm not even certain if
    such order-dependent composition arcs are possible. Also, it DOES deal with
    situations where selections sets are hierarchical - ie, the "legs" variant
    set only becomes available once the "teeth" selection is made.
    """
    selection = dict((key, val) for key, val in selection.iteritems()
                     if val is not None)

    if not selection:
        return True

    variantSets = primSpec.variantSets
    if not variantSets:
        return False

    # first, find all variant sets that intersect at this "selection level"
    intersectedSets = set(variantSets.iterkeys()).intersection(selection)

    if intersectedSets:
        # see if there's a valid value for any intersected set
        for intersectedSet in intersectedSets:
            intersectedValues = variantSets[intersectedSet].variants
            desiredValue = selection[intersectedSet]
            if desiredValue not in intersectedValues:
                continue
            newPrim = intersectedValues[desiredValue]

            # make a copy of the selection, and pop the "fixed" value
            selection = dict(selection)
            selection.pop(intersectedSet)
            return layerPrimHasVariantSelection(newPrim, selection)

        # if we didn't find any intersections with a valid value, then we
        # deem this selection not found!
        return False

    # ok, there were no shared variantSets at this level, but there ARE
    # variant sets... we randomly pick one variantSet, then iterate through
    # all it's possible values

    chosenVariantSet = variantSets.itervalues().next()
    for newPrim in chosenVariantSet.variants.itervalues():
        if layerPrimHasVariantSelection(newPrim, selection):
            return True

    # we tried all the variant selections of one variant set - we deem it not
    # found!
    return False


def iterVariantSetKeys(variantSetPairs):
    '''
    Given an iterable of (setName, variantName) pairs, yield a set of
    hierarchical cache keys for the sets in the same order.

    >>> primVariants = [
    ... PrimVariant(setName='elem', variantName='anim'),
    ... PrimVariant(setName='color', variantName='blue'),
    ... PrimVariant(setName='version', variantName='A02')
    ... ]
    >>> print list(iterVariantSetKeys(primVariants))
    ... ['elem', '{elem=anim}color', '{elem=anim}{color=blue}version']

    Parameters
    ----------
    variantSetPairs : Iterable[PrimVariant]
        (setName, variantName) pairs

    Returns
    -------
    Iterator[str]
        unique key for a distinct variant set on a prim
    '''
    key = ''
    for setName, variant in variantSetPairs:
        yield '%s%s' % (key, setName)
        key = '%s{%s=%s}' % (key, setName, variant)


def variantsByKey(primVariants, cacheKeys=None):
    '''Replace the name of a variant set tuple with its distinct key.

    >>> primVariants = [
    ... PrimVariant(setName='elem', variantName='anim'),
    ... PrimVariant(setName='color', variantName='blue'),
    ... PrimVariant(setName='version', variantName='A02')
    ... ]
    >>> print variantsByKey(primVariants)
    ... [('elem', 'anim'),
    ...  ('{elem=anim}color', 'blue'),
    ...  ('{elem=anim}{color=blue}version', 'A02')]

    Parameters
    ----------
    primVariants : Iterable[PrimVariant]
        (setName, variantName) pairs
    cacheKeys : Optional[Iterable[str]]

    Returns
    -------
    List[Tuple[str, str]]
        (cacheKey, variantName) pairs
    '''
    if not cacheKeys:
        cacheKeys = iterVariantSetKeys(primVariants)
    return [(cacheKey, activeValue) for cacheKey, (_, activeValue)
            in zip(cacheKeys, primVariants)]


def applySelection(primVariants, selection):
    '''Given prim variants and defaults return ordered primVariants with the
    new selection.

    Parameters
    ----------
    primVariants : Iterable[PrimVariant]
    selection : Dict[str, str]

    Returns
    -------
    List[PrimVariant]
        setName, variantName pairs
    '''
    result = []
    for var in primVariants:
        setName = var[0]
        if setName in selection:
            var = PrimVariant(setName, selection[setName])
        result.append(var)
    return result


class EditTargetContext(object):
    '''
    A Helper context that sets a stage's edit target, but then returns it
    to its original value on exit.
    '''
    def __init__(self, stage, target):
        self.stage = stage
        self.target = target
        self.originalEditTarget = None

    def __enter__(self):
        self.originalEditTarget = self.stage.GetEditTarget()
        self.stage.SetEditTarget(self.target)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stage.SetEditTarget(self.originalEditTarget)


class VariantContext(object):
    '''
    A Helper context that uses pixar's VariantEditContext to target edits
    to a variant but will also:
     - create missing variant sets and variants
     - set multiple variants for a hierarchical variant sets
     - optionally, restore selections after editing variant
    '''
    def __init__(self, prim, variantTuples, setAsDefaults=True):
        '''
        Create variant sets and variants that don't exist and get the
        variant contexts.

        Parameters
        ----------
        prim : Usd.Prim
        variantTuples: Iterable[Tuple[str, str]]
            iterable of tuples mapping variantSetName to variantName that can
            represent a hierarchy of nested variants.
        setAsDefaults : bool
            Set the variants in variantTuples as the default variant 
            in the editContext layer
        '''
        self.contexts = []
        self.setAsDefaults = setAsDefaults
        self.originalSelections = []
        self.prim = prim
        self.variantTuples = variantTuples

        self.stage = self.prim.GetStage()
        self.sessionLayer = self.stage.GetSessionLayer()
        self.spec = self.stage.GetEditTarget().GetLayer().GetPrimAtPath(prim.GetPath())
        if not self.spec:
            self.spec = Sdf.CreatePrimInLayer(
                self.stage.GetEditTarget().GetLayer(),
                prim.GetPrimPath())

    def __enter__(self):
        for variantSetName, variantName in self.variantTuples:
            variantSet = self.prim.GetVariantSets().AppendVariantSet(variantSetName)
            variantSet.AppendVariant(variantName)

            original = variantSet.GetVariantSelection()
            self.originalSelections.append((variantSet, original))

            # make the selection on the session layer so that it will be the
            # selected variant in the context.
            with EditTargetContext(self.stage, self.sessionLayer):
                status = variantSet.SetVariantSelection(variantName)
                assert status is True, 'variant selection failed'
                assert variantSet.GetVariantSelection() ==  variantName

            if self.setAsDefaults:
                self.spec.variantSelections.update({variantSetName: variantName})

            context = variantSet.GetVariantEditContext()
            context.__enter__()
            self.contexts.append(context)

        # FIXME: this shows all variants instead of just the ones in the context
        # _logger.debug('In variant context: %s'
        #               % usdlib.variants.getPrimVariants(self.prim))

    def __exit__(self, type, value, traceback):
        for context, original in reversed(zip(self.contexts,
                                              self.originalSelections)):
            context.__exit__(type, value, traceback)
            with EditTargetContext(self.stage, self.sessionLayer):
                for variantSet, original in self.originalSelections:
                    variantSet.SetVariantSelection(original)


class PrimInterfaceBase(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def getVariantSetInfo(self):
        '''
        Yields variant set dicts with information about a particular variant
        set.

        Returns
        -------
        Iterator[Dict[str, Any]]
           Information about a variant set like its current selection,
           available variants, and previous values
        '''
        raise NotImplementedError

    @abstractmethod
    def setNewDefaultVariants(self, refresh=True):
        raise NotImplementedError

    @abstractmethod
    def setInitialVariants(self, refresh=True):
        raise NotImplementedError

    @abstractmethod
    def pinCurrentVariants(self, refresh=True):
        raise NotImplementedError


class VariablePrimHelper(PrimInterfaceBase):
    '''
    A Helper class for gathering information on a prim's variant selections and
    making changes.
    '''

    def __init__(self, prim, assetName, sessionPrimSpec,
                 oldDefaultVariants=None, initialSelections=None):
        '''
        Parameters
        ----------
        prim : Usd.Prim
        assetName : str
        sessionPrimSpec : Sdf.PrimSpec
        oldDefaultVariants : Optional[Dict[str, str]]
        initialSelections
        '''
        assert prim.HasVariantSets(), 'Prim does not have any variant sets'
        self.assetName = assetName
        self.sessionPrimSpec = sessionPrimSpec
        self.prim = prim
        self.path = str(prim.GetPath())
        # FIXME: mapping setName to ?
        self.initialSelections = initialSelections or {}
        # mapping cacheKey to default variant
        self.oldDefaultVariants = oldDefaultVariants or {}  # type: Dict[str, str]

        # tuples of setName, value
        self.activeVariants = None  # type: List[PrimVariant]
        # mapping cacheKey to list of variant name choices
        self.variants = None  # type: Dict[str, List[str]]
        # mapping cacheKey to active variant value
        self.activeVariantsDict = None  # type: Dict[str, str]
        # mapping cacheKey to default variant value
        self.defaultVariantsDict = {}  # type: Dict[str, str]
        # mapping cacheKey to variant set name
        self.variantSetNameDict = None  # type: OrderedDict[str, str]
        # list of status info dictionary per variant
        self.status = None  # type: List[Dict[str, str]]

        self._refreshVariantInfo()

    def __repr__(self):
        # add useful info of primPath and assetName
        return '<%s.%s(path=%s, assetName=%s) object at %s>' \
               % (self.__class__.__module__, self.__class__.__name__,
                  self.path, self.assetName, hex(id(self)))

    def _getVariantStatuses(self):
        '''
        Get a status dictionary for each variant.
        '''
        status = []
        for varKey in self.variantSetNameDict.keys():
            selection = self.activeVariantsDict[varKey]
            default = self.defaultVariantsDict[varKey]
            oldDefault = self.oldDefaultVariants.get(varKey)
            isNew = oldDefault is not None and default != oldDefault
            isDefault = default == selection
            isValid = selection in self.variants[varKey]
            status.append(
                {
                    'isNew': isNew,
                    'isDefault': isDefault,
                    'isValid': isValid
                })
        return status

    def _getVariantChoices(self):
        # FIXME: variant names are not required by the UI until a row has been
        # selected, so this would be a good candidate for lazily computing,
        # however, self.variants is used by self._refreshStatus()
        allVariants = {}
        for cacheKey, setName in self.variantSetNameDict.items():
            variantSet = self.prim.GetVariantSet(setName)
            variantNames = variantSet.GetVariantNames()
            allVariants[cacheKey] = variantNames
        return allVariants

    def _getDefaultVariants(self):
        sessionLayer = self.prim.GetStage().GetSessionLayer()
        defaults = getPrimDefaultVariants(self.prim, sessionLayer)
        return dict(variantsByKey(applySelection(self.activeVariants, defaults),
                                  cacheKeys=self.variantSetNameDict.keys()))

    # FIXME: write tests, and cleanup this population code
    # FIXME: Restore previous selection for sub-variants or not: just restore pinned values
    def _refreshVariantInfo(self, changedSet=None):
        # query prim for active variants
        self.activeVariants = getPrimVariants(self.prim)

        # transform and cache data based on activeVariants
        self.activeVariantsDict = dict(variantsByKey(self.activeVariants))
        variantSets = [x[0] for x in self.activeVariants]
        self.variantSetNameDict = OrderedDict(
            zip(iterVariantSetKeys(self.activeVariants), variantSets))

        # query the prim for variant choices
        self.variants = self._getVariantChoices()

        # query the prim for variant defaults
        # NOTE: we update self.defaultVariantsDict rather than overwrite it
        # because we want to aggregate values from all calls to
        # _refreshVariantInfo.  This allows us to converge on a (more) complete
        # picture of all the default values without incurring the cost of
        # cycling through all variants up front.
        self.defaultVariantsDict.update(self._getDefaultVariants())
        self.status = self._getVariantStatuses()

    def getVariantSetInfo(self):
        '''
        Yields variant set dicts with information about a particular variant
        set.

        Returns
        -------
        Iterator[Dict[str, Any]]
           Information about a variant set like its current selection,
           available variants, and previous values that can be used to
           construct a ``usdman.VariantSetWidget``.
        '''
        for cacheKey, setName in self.variantSetNameDict.items():
            isPinned = setName in self.sessionPrimSpec.variantSelections
            yield dict(setName=setName,
                       cacheKey=cacheKey,
                       variantNames=self.variants.get(cacheKey),
                       initialValue=self.activeVariantsDict.get(cacheKey),
                       isPinnedValue=isPinned,
                       oldDefault=self.oldDefaultVariants.get(cacheKey),
                       defaultVariant=self.defaultVariantsDict.get(cacheKey),
                       oldSelection=self.initialSelections.get(setName))

    def setVariantSelection(self, setName, newValue):
        '''
        Set the selection on the prims variant set in the session layer, and
        refresh the prim items data.

        Parameters
        ----------
        setName : str
        newValue : str
        '''
        variantSet = self.prim.GetVariantSet(setName)
        if newValue is None:
            variantSet.ClearVariantSelection()
        else:
            variantSet.SetVariantSelection(newValue)
        self._refreshVariantInfo(changedSet=setName)

    def refresh(self):
        '''Refresh the prim items data with the latest variants.'''
        self._refreshVariantInfo(changedSet=None)

    def setNewDefaultVariants(self, refresh=True):
        '''Sets variants on a prim to their default values

        Parameters
        ----------
        refresh : bool
            Wether to refresh the data on this item if changes are made. Set
            false if caller will handle refreshing later.

        Returns
        -------
        bool
            whether item was modified
        '''
        oldDefaults = self.oldDefaultVariants
        defaults = self.defaultVariantsDict
        actives = self.activeVariantsDict
        setNames = self.variantSetNameDict
        updates = {}
        for varKey, selection in actives.iteritems():
            defaultVariant = defaults[varKey]
            isNew = defaultVariant != oldDefaults.get(varKey) is not None
            isDefault = defaultVariant == selection
            if isNew and not isDefault:
                updates[setNames[varKey]] = defaultVariant
        if updates:
            self.sessionPrimSpec.variantSelections.update(updates)
            if refresh:
                self._refreshVariantInfo()
            return True
        return False

    def setInitialVariants(self, refresh=True):
        '''
        Sets variants on a prim to their initial values

        Parameters
        ----------
        refresh : bool
            Wether to refresh the data on this item if changes are made. Set
            false if caller will handle refreshing later.

        Returns
        -------
        bool
            whether item was modified
        '''
        updates = {}
        for varKey, selection in self.activeVariantsDict.iteritems():
            initialSelection = self.initialSelections.get(
                self.variantSetNameDict[varKey])
            if initialSelection and initialSelection != selection:
                updates[self.variantSetNameDict[varKey]] = initialSelection
        if updates:
            self.sessionPrimSpec.variantSelections.update(updates)
            if refresh:
                self._refreshVariantInfo()
            return True
        return False

    def pinCurrentVariants(self, refresh=True):
        self.sessionPrimSpec.variantSelections.update(self.activeVariants)
        if refresh:
            # the pinned status is gathered live in getVariantSetInfo, so we
            # don't need to refresh all the data.
            pass
        return True

    @property
    def invalidSelections(self):
        return [variant for x, variant in zip(self.status, self.activeVariants)
                if not x['isValid']]

    @property
    def defaultSelections(self):
        return [variant for x, variant in zip(self.status, self.activeVariants)
                if x['isDefault']]

    @property
    def newSelections(self):
        return [variant for x, variant in zip(self.status, self.activeVariants)
                if x['isNew']]


class MultipleVariablePrimHelper(PrimInterfaceBase):
    '''A helper class for gathering information on multiple prim's 
    variant selections at once and making bulk changes to them.'''

    def __init__(self, prims):
        '''
        Parameters
        ----------
        prims : Iterable[VariablePrimHelper]
        '''
        self.primHelpers = list(prims)
        # variant infos by cache key
        self.data = OrderedDict()

    def getVariantSetInfo(self):
        '''
        Find the intersecting variant sets and variants that apply to all
        primItems.

        Returns
        -------
        Iterator[Dict[str, Any]]
        '''
        # for now we are rebuilding this every time
        self.data = OrderedDict()
        for i, helper in enumerate(self.primHelpers):
            variantSetDicts = list(helper.getVariantSetInfo())
            if i == 0:
                # grab all the variant sets from the first helper as is
                for j, variantSetDict in enumerate(variantSetDicts):
                    self.data[variantSetDict['setName']] = variantSetDict
            else:
                primVariantKeys = []
                for j, variantSetDict in enumerate(variantSetDicts):
                    setName = variantSetDict['setName']
                    try:
                        currentDict = self.data[setName]
                    except KeyError:
                        # variant set missing from previous prims
                        continue
                    primVariantKeys.append(setName)

                    for key, value in variantSetDict.iteritems():
                        currentValue = currentDict[key]
                        if currentValue == value:
                            # match! do nothing, just keep current value
                            continue

                        new = None
                        if currentValue is not None and value is not None:
                            if type(currentValue) != type(value):
                                raise ValueError('mismatching type')
                            elif isinstance(currentValue, basestring):
                                new = None
                            elif isinstance(currentValue, list):
                                new = sorted(list(
                                    set(currentValue).intersection(value)))
                                if MULTIPLE_VALUES in currentValue:
                                    # make sure this special value is not lost
                                    new.insert(0, MULTIPLE_VALUES)

                        # dont allow these to mismatch
                        if key in ('setName',):
                            self.data.pop(setName)
                            continue
                        # these must not be empty
                        if not new and key in ('variantNames',):
                            self.data.pop(setName)
                            continue
                        # multiple values can not be the only available choice,
                        # because then there is nothing to switch to.
                        if key == 'variantNames' and new == [MULTIPLE_VALUES]:
                            self.data.pop(setName)
                            continue

                        # if we've gotten this far, we have different values
                        # and we need to set a new "merged" value
                        if key in ('initialValue',):
                            new = MULTIPLE_VALUES
                            variantNames = currentDict['variantNames']
                            if MULTIPLE_VALUES not in variantNames:
                                variantNames.insert(0, MULTIPLE_VALUES)

                        currentDict[key] = new

                # if this helper didn't have a variant set, it cant be common
                notPresent = set(self.data.keys()).difference(primVariantKeys)
                for setName in notPresent:
                    self.data.pop(setName)

        for info in self.data.values():
            yield info

    def _modifyPrimItems(self, methodName, refresh=True):
        '''
        Perform the same modification action on an iterable of primItems
        as a single stage transaction.

        Parameters
        ----------
        methodName : str
            modifying method of VariablePrimHelper

        Returns
        -------
        List[VariablePrimHelper]
            modified items
        '''
        # TODO: include, exclude
        updatedItems = []
        with Sdf.ChangeBlock():
            for item in self.primHelpers:
                if getattr(item, methodName)(refresh=False):
                    updatedItems.append(item)
        if refresh:
            for item in updatedItems:
                item.refresh()

        return updatedItems

    def setNewDefaultVariants(self, refresh=True):
        return self._modifyPrimItems('setNewDefaultVariants', refresh)

    def setInitialVariants(self, refresh=True):
        return self._modifyPrimItems('setInitialVariants', refresh)

    # Note: refresh is False, because pinning is gathered live.
    def pinCurrentVariants(self, refresh=False):
        return self._modifyPrimItems('pinCurrentVariants', refresh)


def iterVariablePrims(stage, root=None, lastRunData=None):
    '''
    Populate and yield a ``VariablePrimHelper`` for every asset prim with
    variants on a stage.

    Parameters
    ----------
    stage : Usd.Stage
        A Valid stage with a session layer. May be modified.
    root : Optional[Usd.Prim]
        only yield helpers for prims that are children of this prim
    lastRunData : Optional[Dict[str, Dict[str, str]]]
        The last known defaults for prim variant selections as returned by
        `getLastRunData()`.
        This is external data that cannot be gathered from the stage, but allows
        us to make decisions about likely types of updates.

    Returns
    -------
    Iterator[VariablePrimHelper]
        initialized data structure for prim information.
    '''
    lastRunData = lastRunData or {}  # type: Dict[str, Dict[str, str]]
    sessionLayer = stage.GetSessionLayer()

    if not root:
        root = stage.GetPseudoRoot()

    # Could pass UsdPrimIsModel predicate as an optimization if we are
    # confident that this will only be acting upon assets
    for prim in Usd.PrimRange(root):

        if not prim.HasVariantSets():
            continue
        # before checking asset name, we author a variant selection for prims
        # that have variants but are missing a selection so that it we at
        # least get a version of what exists under each variant
        varSets = prim.GetVariantSets()
        for varSetName in varSets.GetNames():
            varSet = varSets.GetVariantSet(varSetName)
            if not varSet.GetVariantSelection() and varSet.GetVariantNames():
                varSet.SetVariantSelection(varSet.GetVariantNames()[0])

        assetName = usdlib.utils.getAssetName(prim)
        if assetName is None:
            continue

        # This may not be the best long-term solution, but we want every
        # prim we're managing to have a PrimSpec in the session layer so we
        # can easily manage the "pinned" state of a variant selection.
        primPath = prim.GetPath()
        sessionPrimSpec = sessionLayer.GetPrimAtPath(primPath)
        if sessionPrimSpec is None:
            sessionPrimSpec = Sdf.CreatePrimInLayer(sessionLayer,
                                                    primPath)

        item = VariablePrimHelper(
            prim,
            assetName=assetName,
            sessionPrimSpec=sessionPrimSpec,
            oldDefaultVariants=lastRunData.get(str(primPath), {}),
            initialSelections=dict(sessionPrimSpec.variantSelections))
        yield item


def getVariantSelectionData(variablePrims):
    '''
    Return a dict of variant selections on the given prims, mapping prim paths
    to dicts mapping variant set names to selected values.

    Parameters
    ----------
    variablePrims : Iterable[VariablePrimHelper]

    Returns
    -------
    Dict[str, Dict[str, str]]
        Sparse dict of variant selections authored in the session layer,
        in the form of:
            Dict[primPath, Dict[variantSetName, selectedVariant]]
    '''
    results = {}
    for item in variablePrims:
        variantSelections = item.sessionPrimSpec.variantSelections.items()
        if variantSelections:
            results[str(item.prim.GetPath())] = dict(variantSelections)
    return results
