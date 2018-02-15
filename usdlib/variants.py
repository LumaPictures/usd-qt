#
# Copyright 2017 Luma Pictures
#
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification you may not use this file except in
# compliance with the Apache License and the following modification to it:
# Section 6. Trademarks. is deleted and replaced with:
#
# 6. Trademarks. This License does not grant permission to use the trade
#    names, trademarks, service marks, or product names of the Licensor
#    and its affiliates, except as required to comply with Section 4(c) of
#    the License and to reproduce the content of the NOTICE file.
#
# You may obtain a copy of the Apache License at
#
#     http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License with the above modification is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the Apache License for the specific
# language governing permissions and limitations under the Apache License.
#
'''
Module for setting variants on usd stages.
'''
import pxr.Sdf as Sdf
import pxr.Usd as Usd
import pxr.Pcp as Pcp
import pxr.Kind as Kind

from typing import NamedTuple

if False:
    from typing import *


if not hasattr(Usd.References, 'AddReference'):
    Usd.Relationship.AddTarget = Usd.Relationship.AppendTarget
    Usd.VariantSet.AddVariant = Usd.VariantSet.AppendVariant
    Usd.VariantSets.AddVariantSet = Usd.VariantSets.AppendVariantSet
    Usd.References.AddReference = Usd.References.AppendReference


class VariantSelectionError(Exception):
    pass


PrimVariant = NamedTuple('PrimVariant',
                         [('setName', str),
                          ('variantName', str)])


def makeValid(name):
    '''Return a valid variant name by replacing invalid characters'''
    import re
    # Valid identifiers allow [[:alnum:]_|\-]+ with an optional leading dot.
    # replace non leading dots with _
    if name.count('.'):
        name = name[0] + name[1:].replace('.', '_')
    # could also replace other any invalid characters with _, but that might be
    # too permissive.
    # name = re.sub(r'[^a-zA-Z0-9_|\-.]', r'_', name)
    if not re.match(r'[a-zA-Z0-9_|\-.][a-zA-Z0-9_|\-]*?$', name):
        raise ValueError('Could not conform \'%s\' to a valid variant name'
                         % name)
    return name


def iterPrimIndexVariantNodes(prim):
    '''
    Return an iterator over the variant nodes in the given prim's index.

    Parameters
    ----------
    prim : Usd.Prim

    Returns
    -------
    Iterator[Pcp.NodeRef, List[PrimVariants]]
    '''
    def walkVariants(currentNode, parentVariants):
        if currentNode.arcType == Pcp.ArcTypeVariant \
                and not currentNode.IsDueToAncestor():
            currentVariant = PrimVariant(*currentNode.path.GetVariantSelection())
            parentVariants.append(currentVariant)
            yield currentNode, parentVariants

        for childNode in currentNode.children:
            for x in walkVariants(childNode, list(parentVariants)):
                yield x

    # Note: The prim index will not include variants that have no selection.
    # ComputeExpandedPrimIndex() has the same problem
    index = prim.GetPrimIndex()
    for node, parentVariantNodes in walkVariants(index.rootNode, []):
        # yield node, variantSelectionKey(parentVariantNodes)
        yield node, parentVariantNodes


def getPrimVariantsWithPaths(prim):
    '''
    Returns a list of tuples representing a prim's variant set names and active
    values.

    "Sorted" depth first by variant opinion "strength" in the prim's index.

    Parameters
    ----------
    prim : Usd.Prim

    Returns
    -------
    List[Tuple[Sdf.Path, PrimVariant]]
        (setName, variantName) pairs and child lists
    '''
    # fixme: might need a strategy for duplicate variant sets that are found
    # under different variant hierarchies. These are possible, but aren't
    # practical as the selection on the composed stage is the same.
    results = []
    setNames = set(prim.GetVariantSets().GetNames())
    for node, parentVariants in iterPrimIndexVariantNodes(prim):
        variantSetName, variantName = node.path.GetVariantSelection()
        variant = PrimVariant(variantSetName, variantName)
        key = variantSetKey(parentVariants + [variant])
        try:
            setNames.remove(variant.setName)
        except KeyError:
            pass
        else:
            results.append((node.path, key, variant))

    # If a variant is not selected, it won't be included in the prim index. So
    # we need a way to get those variants. ComputeExpandedPrimIndex() seems
    # unstable and slow so far. Using the main api methods we can easily get
    # variant names. The problem is they are not ordered (by hierarchy)...
    # Variants with no selection hide subsequent variants so missing ones are
    # usually top level variants.
    for setName in setNames:
        setValue = prim.GetVariantSet(setName).GetVariantSelection()
        path = prim.GetPath().AppendVariantSelection(setName, setValue)
        variant = PrimVariant(setName, setValue)
        # fixme: this check doesnt work because even valid top ones aren't found.
        # # check that the variant is in fact a valid top level variant
        # if not prim.GetStage().GetPrimAtPath(path):
        #     continue
        results.append((path, variantSetKey([variant]), variant))

    return results


def getPrimVariants(prim):
    '''
    Returns a list of tuples representing a prim's variant set names and active
    values.

    Parameters
    ----------
    prim : Usd.Prim

    Returns
    -------
    List[Union[PrimVariant, List]]
        (setName, variantName) pairs and child lists
    '''
    return [variant for path, key, variant in getPrimVariantsWithPaths(prim)]


# def getStrengthSortedPrimVariants(prim):
#     '''
#     Returns a list of tuples representing a prim's variant set names and active
#     values.
#
#     Sorted by variant opinion "strength" in the prim's index. (Note that some
#     opinions have equal strength and will be sequential)
#
#     Parameters
#     ----------
#     prim : Usd.Prim
#
#     Returns
#     -------
#     List[Tuple[Sdf.Path, PrimVariant]]
#     '''
#     return sorted(getPrimVariantsWithPaths(prim),
#                   key=lambda x: (str(x).count('{'), str(x)))


def getPrimVariantsWithKey(prim):
    '''
    Returns a list of tuples representing a prim's variant set names and active
    values, sorted by their opinion "strength" in the prim's index.

    Parameters
    ----------
    prim : Usd.Prim

    Returns
    -------
    List[Tuple[(str, PrimVariant)]]
        (cacheKey, PrimVariant) pairs and child lists
    '''
    return [(key, variant)
            for path, key, variant in getPrimVariantsWithPaths(prim)]


def getPrimDefaultVariants(prim, sessionLayer):
    '''
    Get the variant selections for a prim if the sessionLayer was muted.

    Note that nested variant defaults are still affected by higher strength
    variant selections in the sessionLayer.

    Currently "mutes" session layer and its sublayers. (Note that this might
    return "defaults" that are indirectly set from the session layers but are
    not actually on the session layers and sublayer but instead were brought
    in by reference or some other arc on the session layer)

    Parameters
    ----------
    prim : Usd.Prim
    sessionLayer : Sdf.Layer

    Returns
    -------
    Dict[str, str]
    '''
    import usdlib.utils

    defaults = {}
    variantSets = prim.GetVariantSets()
    left = set(variantSets.GetNames())
    sessionLayers = usdlib.utils.getAllSubLayers(sessionLayer)
    sessionSpecified = {}
    firstNonSessionLayer = True
    for spec in prim.GetPrimStack():
        if not left:
            break
        if spec.layer in sessionLayers:
            sessionSpecified.update(spec.variantSelections)
        else:
            # optimization (assumes that session layers are highest strength):
            if firstNonSessionLayer:
                # we can stop searching for variants that are not specified
                # in session layer
                for name in left.difference(sessionSpecified):
                    defaults[name] = variantSets.GetVariantSelection(name)
                firstNonSessionLayer = False

            for name, variant in spec.variantSelections.iteritems():
                if name in left:
                    defaults[name] = variant
                    left.remove(name)
    return defaults


def getPrimVariantSelectionInLayer(prim, specificLayer):
    '''
    Get the variant selections for a prim that are specified in the session
    layer.

    Parameters
    ----------
    prim : Usd.Prim
    specificLayer : Sdf.Layer

    Returns
    -------
    Dict[str, str]
    '''
    selected = {}
    variantSets = prim.GetVariantSets()
    if variantSets.GetNames():
        for spec in prim.GetPrimStack():
            if spec.layer == specificLayer:
                selected.update(spec.variantSelections)
    return selected


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
    '''
    Queries the given layer (or path to a layer) to see if the given prim
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
    '''
    if not isinstance(layer, Sdf.Layer):
        layer = Sdf.Layer.FindOrOpen(layer)

    if prim is None:
        prim = layer.defaultPrim
        if not prim:
            raise ValueError("no prim specified, and layer {!r} had no default"
                             " prim".format(layer.identifier))

    return layerPrimHasVariantSelection(layer.rootPrims[prim], selection)


def layerPrimHasVariantSelection(primSpec, selection):
    '''
    Queries the given layer PrimSpec to see if it has the given variant
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
    '''
    selection = dict((key, val) for key, val in selection.iteritems()
                     if val is not None)

    if not selection:
        return True

    variantSets = primSpec.variantSets
    if not variantSets:
        return False

    # first, find all variant sets that intersect at this "selection level"
    intersectedSets = set(variantSets).intersection(selection)

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


def variantsByKey(primVariants, cacheKeys):
    '''
    Replace the name of a variant set tuple with its distinct key.

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
    return [(cacheKey, activeValue) for cacheKey, (_, activeValue)
            in zip(cacheKeys, primVariants)]


def variantSelectionKey(primVariants):
    '''Return a distinct key for a list of selections on a prim'''
    key = ''
    for setName, variantName in primVariants:
        key += '{%s=%s}' % (setName, variantName)
    return key


def variantSetKey(variantSetPairs):
    '''
    Given an iterable of (setName, variantName) pairs, yield a set of
    hierarchical cache keys for the sets in the same order.

    >>> primVariants = [
    ... PrimVariant(setName='elem', variantName='anim'),
    ... PrimVariant(setName='color', variantName='blue'),
    ... PrimVariant(setName='version', variantName='A02')
    ... ]
    >>> print variantSetKey(primVariants))
    ... '{elem=anim}{color=blue}version'

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
    for setName, variant in variantSetPairs[:-2]:
        key = '%s{%s=%s}' % (key, setName, variant)
    return '%s%s' % (key, variantSetPairs[-1][0])


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


# rename to CreateVariantContext?
class VariantContext(object):
    '''
    A Helper context that uses pixar's VariantEditContext to target edits
    to a variant but will also:
     - create missing variant sets and variants
     - set multiple variants for a hierarchical variant sets
     - optionally, restore selections after editing variant
    '''
    def __init__(self, prim, variantTuples, select=True):
        '''
        Create variant sets and variants that don't exist and get the
        variant contexts.

        Parameters
        ----------
        prim : Usd.Prim
        variantTuples: Optional[Iterable[Tuple[str, str]]]
            iterable of tuples mapping variantSetName to variantName that can
            represent a hierarchy of nested variants.
        select : Union[bool, callable]
            If True, select the variants in variantTuples as the default variant
            in the edit layer.
            If False, keep them the same as they are currently and author no
            selection on new variants.
            If a callable, and if adding a variant other than the current one
            call function with:
                (variantSetName, oldValue, newValue)
            and set the value to the result.
        '''
        self.contexts = []
        self.select = select
        self.originalSelections = []
        self.prim = prim
        self.variantTuples = variantTuples or []

        self.stage = self.prim.GetStage()
        self.sessionLayer = self.stage.GetSessionLayer()

    def __enter__(self):
        for variantSetName, variantName in self.variantTuples:
            variantSetName = makeValid(variantSetName)
            variantName = makeValid(variantName)
            variantSet = self.prim.GetVariantSets().AddVariantSet(
                variantSetName)
            if variantName not in variantSet.GetVariantNames():
                variantSet.AddVariant(variantName)

            original = variantSet.GetVariantSelection()
            self.originalSelections.append((variantSet, original))

            # make the selection on the session layer so that it will be the
            # selected variant in the context.
            with EditTargetContext(self.stage, self.sessionLayer):
                status = variantSet.SetVariantSelection(variantName)
                assert status is True, 'variant selection failed'
                assert variantSet.GetVariantSelection() == variantName

            if self.select and original != variantName:
                default = variantName
                if callable(self.select):
                    default = self.select(variantSetName, original, variantName)
                if default:
                    variantSet.SetVariantSelection(default)

            context = variantSet.GetVariantEditContext()
            context.__enter__()
            self.contexts.append(context)

        # print('In variant context: %s' % getPrimVariants(self.prim))

    def __exit__(self, type, value, traceback):
        for context, original in reversed(zip(self.contexts,
                                              self.originalSelections)):
            context.__exit__(type, value, traceback)
            with EditTargetContext(self.stage, self.sessionLayer):
                for variantSet, original in self.originalSelections:
                    variantSet.SetVariantSelection(original)


class SessionVariantContext(object):
    '''
    Temporarily set some variants but then restore them on exit. Use this
    context to inspect hypothetical variant selections and then return to the
    session layers original state.

    Note: Intended for inspection, tries to restore original state, so changes
    to created specs may be lost.
    '''
    def __init__(self, prim, variantTuples):
        '''
        Parameters
        ----------
        prim : Usd.Prim
        variantTuples: Iterable[Tuple[str, str]]
            iterable of tuples mapping variantSetName to variantName that can
            represent a hierarchy of nested variants.
        '''
        self.originalSelections = []
        self.prim = prim
        self.variantTuples = variantTuples

        self.stage = self.prim.GetStage()
        self.sessionLayer = self.stage.GetSessionLayer()
        self.createdSpecs = []

    def __enter__(self):
        variantSets = self.prim.GetVariantSets()
        for prefix in self.prim.GetPath().GetPrefixes():
            if not self.sessionLayer.GetPrimAtPath(prefix):
                self.createdSpecs.append(prefix)
                break  # removing the parent will remove any children
        selections = getPrimVariantSelectionInLayer(self.prim, self.sessionLayer)
        for variantSetName, variantName in self.variantTuples:
            variantSet = variantSets.GetVariantSet(variantSetName)
            self.originalSelections.append((variantSet,
                                            selections.get(variantSetName, '')))

            # make the selection on the session layer so that it will be the
            # selected variant in the context.
            with EditTargetContext(self.stage, self.sessionLayer):
                status = variantSet.SetVariantSelection(variantName)
                if status is not True or \
                        variantSet.GetVariantSelection() != variantName:
                    raise VariantSelectionError(
                        'Failed to select prim variant: %s %s=%s, selected: %s'
                        % (self.prim.GetPath(), variantSetName, variantName,
                           getPrimVariants(self.prim)))

    def __exit__(self, type, value, traceback):
        with EditTargetContext(self.stage, self.sessionLayer):
            # restore session layer selection
            for variantSet, original in self.originalSelections:
                variantSet.SetVariantSelection(original)
            # remove any prim spec creation side effects
            for prefix in self.createdSpecs:
                self.stage.RemovePrim(prefix)
