#
# Copyright 2016 Pixar
#
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification; you may not use this file except in
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
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License with the above modification is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the Apache License for the specific
# language governing permissions and limitations under the Apache License.
#

from __future__ import absolute_import

from pxr import Pcp, Sdf

if False:
    from typing import *
    from pxr import Usd


def SpecifierToString(specifier):
    # type: (Sdf.Specifier) -> str
    """
    Parameters
    ----------
    specifier : Sdf.Specifier

    Returns
    -------
    str
    """
    if specifier is Sdf.SpecifierDef:
        return "def"
    elif specifier is Sdf.SpecifierOver:
        return "over"
    elif specifier is Sdf.SpecifierClass:
        return "class"
    else:
        raise Exception("Unknown specifier.")


class EditTargetContext(object):
    """A context manager that changes a stage's edit target on entry, and then
    returns it to  its previous value on exit.
    """
    __slots__ = ('stage', 'target', 'originalEditTarget')

    def __init__(self, stage, target):
        # type: (Usd.Stage, Sdf.Layer) -> None
        """
        Parameters
        ----------
        stage : Usd.Stage
        target : Sdf.Layer
        """
        self.stage = stage
        self.target = target
        self.originalEditTarget = None

    def __enter__(self):
        self.originalEditTarget = self.stage.GetEditTarget()
        self.stage.SetEditTarget(self.target)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stage.SetEditTarget(self.originalEditTarget)


def GetPrimVariants(prim):
    # type: (Usd.Prim) -> List[Tuple[str, str]]
    """Returns a list of tuples representing a prim's variant set names and
    active values.

    The results are ordered "depth-first" by variant opinion strength in the
    prim's index.

    Parameters
    ----------
    prim : Usd.Prim

    Returns
    -------
    List[Tuple[str, str]]
        (variantSetName, variantName) pairs
    """
    # FIXME: We might need a strategy for duplicate variant sets that are nested
    # under different variant hierarchies. These aren't very practical though,
    # since the selection on the composed stage is the same.

    def walkVariantNodes(node):
        if node.arcType == Pcp.ArcTypeVariant and not node.IsDueToAncestor():
            yield node.path.GetVariantSelection()

        for childNode in node.children:
            for childSelection in walkVariantNodes(childNode):
                yield childSelection

    results = []
    primIndex = prim.GetPrimIndex()
    setNames = set(prim.GetVariantSets().GetNames())
    for variantSetName, variantSetValue in walkVariantNodes(primIndex.rootNode):
        try:
            setNames.remove(variantSetName)
        except KeyError:
            pass
        else:
            results.append((variantSetName, variantSetValue))

    # If a variant is not selected, it won't be included in the prim index, so
    # we need a way to get those variants. `Prim.ComputeExpandedPrimIndex()`
    # seems unstable and slow so far. We can easily get variant names using the
    # main API methods. The problem is they are not ordered hierarchically...
    # Variants with no selection hide subsequent variants so missing ones are
    # usually top level variants.
    for setName in setNames:
        setValue = prim.GetVariantSet(setName).GetVariantSelection()
        results.append((setName, setValue))

    return results
