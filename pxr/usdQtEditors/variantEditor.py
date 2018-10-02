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
"""
Variant Set and Variant Editing Widget.
"""

from __future__ import absolute_import

from collections import namedtuple

from pxr import Sdf, Usd, Tf
from Qt import QtCore, QtGui, QtWidgets
from treemodel.itemtree import TreeItem, LazyItemTree, ItemLookupError
from treemodel.qt.base import AbstractTreeModelMixin
from pxr.UsdQt.qtUtils import MenuAction, DARK_ORANGE, ContextMenuMixin
from pxr.UsdQt.usdUtils import EditTargetContext
from pxr.UsdQt.hooks import UsdQtHooks


class VariantSelectionError(Exception):
    pass


NULL_INDEX = QtCore.QModelIndex()


PrimVariant = namedtuple('PrimVariant',
                         ['setName',
                          'variantName'])


def MakeValid(name):
    """Return a valid variant name by replacing invalid characters"""
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


def IterVariantSpecs(spec):
    # type: (Sdf.PrimSpec) -> Iterator[Sdf.PrimSpec]
    """Recursively iterate through nested variant prim specs.

    Parameters
    ----------
    spec : Sdf.PrimSpec

    Returns
    ------
    Iterator[Sdf.PrimSpec]
    """
    yield spec
    for variantSet in spec.variantSets:
        for variant in variantSet.variantList:
            for child in IterVariantSpecs(variant.primSpec):
                yield child


def GetSpecSelections(spec):
    """Returns a list of tuples representing a prim's variant set names and active
    values.

    Parameters
    ----------
    prim : Usd.Prim

    Returns
    -------
    OrderedDict[str, str]
        VariantSetName to VariantName
    """
    from collections import OrderedDict
    selections = OrderedDict()
    for contributing in IterVariantSpecs(spec):
        if contributing.path.ContainsPrimVariantSelection():
            sel = contributing.path.GetVariantSelection()
            selections.setdefault(sel[0], sel[1])
    return selections


def RemoveVariant(spec, variantSetName, variantName):
    # type: (Sdf.PrimSpec, str) -> None
    """
    Remove a variant from a prim spec

    Parameters
    ----------
    spec : Sdf.VariantSetSpec
    variantName : str
    """
    varSetSpec = spec.variantSets.get(variantSetName)
    if varSetSpec:
        varSpec = varSetSpec.variants.get(variantName)
        if varSpec:
            varSetSpec.RemoveVariant(varSpec)


def RemoveVariantSet(spec, variantSetName):
    # type: (Sdf.PrimSpec, str) -> None
    """
    Remove a variant set from a prim spec

    Parameters
    ----------
    spec : Sdf.PrimSpec
    variantSetName : str
    """
    spec.variantSetNameList.prependedItems.remove(variantSetName)
    spec.variantSetNameList.addedItems.remove(variantSetName)
    spec.variantSetNameList.appendedItems.remove(variantSetName)
    if variantSetName in spec.variantSelections:
        spec.variantSelections.pop(variantSetName)
    if variantSetName in spec.variantSets:
        del spec.variantSets[variantSetName]


# TODO: Note that this will undo variant selections made on the session layer
# rename to CreateVariantContext?
class CreateVariantContext(object):
    """
    A Helper context that uses pixar's VariantEditContext to target edits
    to a variant but will also:
     - create missing variant sets and variants
     - set multiple variants for a hierarchical variant sets
     - optionally, restore selections after editing variant
    """
    def __init__(self, prim, variantTuples, select=True):
        """
        Create variant sets and variants that don't exist and get the
        variant contexts.

        Parameters
        ----------
        prim : Usd.Prim
        variantTuples: Optional[Iterable[Tuple[str, str]]]
            iterable of tuples mapping variantSetName to variantName that can
            represent a hierarchy of nested variants.
        select : bool
            If True, select the variants in variantTuples as the default variant
            in the edit layer.
            If False, keep them the same as they are currently and author no
            selection on new variants.
        """
        self.contexts = []
        self.select = select
        self.originalSelections = []
        self.prim = prim
        self.variantTuples = variantTuples or []

        self.stage = self.prim.GetStage()
        self.sessionLayer = self.stage.GetSessionLayer()

    def __enter__(self):
        for variantSetName, variantName in self.variantTuples:
            variantSetName = MakeValid(variantSetName)
            variantName = MakeValid(variantName)
            variantSet = self.prim.GetVariantSets().AddVariantSet(
                variantSetName)
            if variantName not in variantSet.GetVariantNames():
                variantSet.AddVariant(variantName)

            # we only care about selections that were on the session layer
            # to begin with, because those are the ones to preserve.
            # original = variantSet.GetVariantSelection()
            spec = self.sessionLayer.GetPrimAtPath(self.prim.GetPath())
            if spec:
                original = GetSpecSelections(spec).get(variantSet, '')
            else:
                original = ''
            self.originalSelections.append((variantSet, original))

            # make the selection on the session layer so that it will be the
            # selected variant in the context.
            with EditTargetContext(self.stage, self.sessionLayer):
                status = variantSet.SetVariantSelection(variantName)
                assert status is True, 'variant selection failed'
                assert variantSet.GetVariantSelection() == variantName

            if self.select and original != variantName:
                variantSet.SetVariantSelection(variantName)

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
    """
    Temporarily set some variants but then restore them on exit. Use this
    context to inspect hypothetical variant selections and then return to the
    session layers original state.

    Note: Intended for inspection, tries to restore original state, so changes
    to created specs may be lost.
    """
    def __init__(self, prim, variantTuples):
        """
        Parameters
        ----------
        prim : Usd.Prim
        variantTuples: Iterable[Tuple[str, str]]
            Iterable of tuples mapping variantSetName to variantName that can
            represent a hierarchy of nested variants.
        """
        self.originalSelections = []
        self.prim = prim
        self.variantTuples = list(variantTuples)

        self.stage = self.prim.GetStage()
        self.sessionLayer = self.stage.GetSessionLayer()
        self.createdSpecs = []

    def __enter__(self):
        variantSets = self.prim.GetVariantSets()
        for prefix in self.prim.GetPath().GetPrefixes():
            if not self.sessionLayer.GetPrimAtPath(prefix):
                self.createdSpecs.append(prefix)
                break  # removing the parent will remove any children
        sessionSpec = self.sessionLayer.GetPrimAtPath(self.prim.GetPath())
        selections = GetSpecSelections(sessionSpec) if sessionSpec else {}
        # make the selections on the session layer so that they are guaranteed
        # to be selected within the context.
        with EditTargetContext(self.stage, self.sessionLayer):
            for variantSetName, variantName in self.variantTuples:
                variantSet = variantSets.GetVariantSet(variantSetName)
                original = selections.get(variantSetName, '')
                self.originalSelections.append((variantSet, original))

                status = variantSet.SetVariantSelection(variantName)
                if (status is not True
                        or variantSet.GetVariantSelection() != variantName):
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


class VariantItem(TreeItem):
    __slots__ = ('prim', 'path', 'variantSet', 'variant', 'parentVariants',
                 '_isVariantSet')

    def __init__(self, prim, parentVariants, variantSet, path, varSetKey):
        """
        Parameters
        ----------
        prim : Usd.Prim
        parentVariants : List[PrimVariant]
        variantSet : Usd.VariantSet
        path : Sdf.Path
        varSetKey : str
        """
        super(VariantItem, self).__init__(key=varSetKey)
        self.prim = prim
        self.path = path
        self.variantSet = variantSet
        self.variant = PrimVariant(*path.GetVariantSelection())
        self.parentVariants = parentVariants
        # whether this item represents a variant set or a variant
        self._isVariantSet = self.variant[1] == ''

    @property
    def isVariantSet(self):
        return self._isVariantSet

    @property
    def selected(self):
        """
        Returns
        -------
        bool
        """
        return self.variantSet.GetVariantSelection() == \
           self.variant.variantName

    @property
    def variants(self):
        """
        Returns
        -------
        List[PrimVariant]
        """
        return self.parentVariants + [self.variant]

    @property
    def name(self):
        """
        Returns
        -------
        str
        """
        if self.isVariantSet:
            return self.variant[0] + ':'
        return self.variant[1]

    @property
    def accessible(self):
        """
        Whether or not this variant is exposed and selectable with the other
        variant selections.

        Returns
        -------
        bool
        """
        setName, variantName = self.variant
        return setName in self.prim.GetVariantSets().GetNames() and \
               (variantName in self.prim.GetVariantSet(setName).GetVariantNames()
                or variantName == '')


def variantKeyFunc(path):
    """Return just the variant selection part of a spec path.
    
    Parameters
    ----------
    Sdf.Path
    
    Returns
    -------
    str
    """
    return path.pathString[len(path.StripAllVariantSelections().pathString):]


def DeclaredVariants(spec):
    declared = []
    declared.extend(spec.variantSetNameList.prependedItems)
    declared.extend(spec.variantSetNameList.addedItems)
    declared.extend(spec.variantSetNameList.appendedItems)
    return declared


class LazyVariantTree(LazyItemTree):
    """A tree that will lazily expand nested variant sets and variants
    """

    def __init__(self, prim):
        self.prim = prim
        super(LazyVariantTree, self).__init__()

    # May want to replace this with an even lazier tree that only fetches
    # children that are explicitly requested by expansion or variant selection.
    # This depends on the cost of switching variants vs. usability.
    def _FetchItemChildren(self, parent):
        prim = self.prim
        if not prim:
            return []

        parentVariants = []
        isVariantSetItem = False
        if isinstance(parent, VariantItem):
            if not parent.variant.variantName:
                # variant set
                parentVariants = parent.parentVariants
                isVariantSetItem = True
            else:
                # variant
                parentVariants = parent.variants
            parentKey = parent.key
        else:
            # is root item
            parentKey = ''
        parentLevel = parentKey.count('{')
        # keys for items that will be added in this method
        keys = set()

        def IsNew(key):
            try:
                if key not in keys:
                    # will raise if key is not yet in tree
                    self.ItemByKey(key)
            except ItemLookupError:
                keys.add(key)
                return True
            return False

        # set variants temporarily so that any variant sets defined under the
        # parent variant can be inspected.
        # with these set, we can guarantee that we see all immediate children
        # specs
        with SessionVariantContext(prim, parentVariants):
            variantItems = []
            for primSpec in prim.GetPrimStack():
                for variantSpec in IterVariantSpecs(primSpec):
                    key = variantKeyFunc(variantSpec.path)
                    primVariant = variantSpec.path.GetVariantSelection()
                    if key == parentKey and not isVariantSetItem:
                        # gather any variant sets added at this level, that may
                        # or may not have variants with specs yet
                        for setName in DeclaredVariants(variantSpec):
                            noSelectionPath = variantSpec.path.AppendVariantSelection(setName, '')
                            declaredSetKey = variantKeyFunc(noSelectionPath)
                            if IsNew(declaredSetKey):
                                variantSet = prim.GetVariantSet(setName)
                                item = VariantItem(prim,
                                                   parentVariants,
                                                   variantSet,
                                                   noSelectionPath,
                                                   declaredSetKey)
                                variantItems.append(item)
                        # skipping parent, its already added to tree
                        continue

                    if not variantSpec.path.ContainsPrimVariantSelection():
                        continue
                    if not key.startswith(parentKey[:-1]):
                        continue  # different branch

                    if isVariantSetItem:
                        if key.count('{') != parentLevel:
                            continue  # ancestor or grandchild
                    else:
                        # not a variant set, so we don't need to add any
                        # variants at this level.
                        continue

                    if not IsNew(key):
                        continue
                    variantSet = prim.GetVariantSet(primVariant[0])
                    item = VariantItem(prim,
                                       parentVariants,
                                       variantSet,
                                       variantSpec.path,
                                       key)
                    variantItems.append(item)
            return variantItems


class VariantModel(AbstractTreeModelMixin, QtCore.QAbstractItemModel):
    """Holds a hierarchy of variant sets and their selections
    """
    NormalColor = QtGui.QBrush(QtGui.QColor(150, 150, 150))
    GroupColor = QtGui.QBrush(DARK_ORANGE)
    SelectedColor = QtGui.QBrush(QtGui.QColor(200, 100, 180))
    InactiveDarker = 400
    headerLabels = ('Name', 'Path')

    def __init__(self, stage, prim=None, parent=None):
        """
        Parameters
        ----------
        stage : Usd.Stage
        prims : Optional[Usd.Prim]
            Current  prim selection
        parent : Optional[QtGui.QWidget]
        """
        super(VariantModel, self).__init__(parent=parent)
        self._stage = stage
        self._prim = None
        if prim:
            self.ResetPrim(prim)
        else:
            # only reset stage
            self.ResetStage(stage)

    # Qt methods ---------------------------------------------------------------

    def columnCount(self, parentIndex):
        return 2

    def flags(self, modelIndex):
        if modelIndex.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        return QtCore.Qt.NoItemFlags

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal \
                and role == QtCore.Qt.DisplayRole:
            return self.headerLabels[section]

    def data(self, modelIndex, role=QtCore.Qt.DisplayRole):
        if not modelIndex.isValid():
            return
        if role == QtCore.Qt.DisplayRole:
            column = modelIndex.column()
            item = modelIndex.internalPointer()
            if column == 0:
                return item.name
            elif column == 1:
                return str(item.path)
        elif role == QtCore.Qt.ForegroundRole or role == QtCore.Qt.FontRole:
            item = modelIndex.internalPointer()

            def selected():
                if item.selected and not item.isVariantSet:
                    parentIndex = self.parent(modelIndex)
                    parent = parentIndex.internalPointer()
                    while isinstance(parent, VariantItem):
                        if not parent.selected and not parent.isVariantSet:
                            return False
                        parentIndex = self.parent(parentIndex)
                        parent = parentIndex.internalPointer()
                    return True
                return False

            if role == QtCore.Qt.ForegroundRole:
                brush = self.NormalColor
                if item.isVariantSet:
                    return self.GroupColor
                if selected():
                    return self.SelectedColor

                if item.accessible:
                    brush = QtGui.QBrush(brush)
                    brush.setColor(brush.color().darker(
                        self.InactiveDarker))
                return brush
            elif role == QtCore.Qt.FontRole:
                font = QtGui.QFont()
                item = modelIndex.internalPointer()
                if not item.isVariantSet and not \
                        self.GetEditLayer().GetPrimAtPath(item.path):
                    font.setItalic(True)
                if selected():
                    font.setBold(True)
                return font

    # Custom Methods -----------------------------------------------------------

    @property
    def stage(self):
        return self._stage

    @property
    def prim(self):
        return self._prim

    def SelectVariant(self, item):

        def toggle():
            val = item.variant.variantName
            if item.variantSet.GetVariantSelection() == val:
                val = ''
            item.variantSet.SetVariantSelection(val)

        # may eventually want to author selections within other variants. Which
        # would require getting a context for the specific parent variant.
        if item.parentVariants:
            # with item.parentVariants[-1].GetVariantEditContext():
            with CreateVariantContext(item.prim, item.parentVariants,
                                      select=False):
                print 'in context:', item.parentVariants
                toggle()
        else:
            toggle()
        self.dataChanged.emit(NULL_INDEX, NULL_INDEX)  # TODO: refine

    def RemoveItem(self, item):
        layer = self.GetEditLayer()
        parent = self.GetItemIndex(item, 0).parent()
        if item.isVariantSet:
            spec = layer.GetPrimAtPath(item.path.GetParentPath())
            if spec:
                RemoveVariantSet(spec, item.variant[0])
                self.RebuildUnder(modelIndex=parent)
        else:
            spec = layer.GetPrimAtPath(item.path.GetParentPath())
            if spec:
                RemoveVariant(spec, *item.path.GetVariantSelection())
                self.RebuildUnder(modelIndex=parent)

    def RebuildUnder(self, modelIndex=None, item=None):
        if not modelIndex and not item:
            raise ValueError('Must pass either a modelIndex or an item')
        if not modelIndex:
            modelIndex = self.GetItemIndex(item, 0)
        if item is None:
            item = modelIndex.internalPointer()

        self.beginRemoveRows(modelIndex, 0,
                             max(self.itemTree.ChildCount(parent=item) - 1, 0))
        if item:
            self.itemTree.ForgetChildren(item)
        else:
            # cannot forget root children, so make a new tree
            self.itemTree = LazyVariantTree(self._prim)
        self.endRemoveRows()

    def ResetPrim(self, prim=None):
        if prim:
            if prim == self._prim:
                return
        self.beginResetModel()
        self._prim = prim
        self.itemTree = LazyVariantTree(prim)
        self.endResetModel()
        if self._prim:
            self.ResetStage(self._prim.GetStage())

    def ResetStage(self, stage):
        if stage == self._stage:
            return
        self._stage = stage
        if self._stage:
            self._listener = Tf.Notice.Register(Usd.Notice.StageEditTargetChanged,
                                                self._OnEditTargetChanged, stage)
        else:
            self._listener = None
        if self._prim and stage != self._prim.GetStage():
            self.ResetPrim()  # clear prim and reset model

    def _OnEditTargetChanged(self, notice, stage):
        # if the edit target changes we refresh the variants because they
        # display whether they are defined on the edit target
        self.dataChanged[QtCore.QModelIndex, QtCore.QModelIndex].emit(
            NULL_INDEX, NULL_INDEX)

    def GetEditLayer(self):
        return self._stage.GetEditTarget().GetLayer()


def _Summary(strings):
    return '/'.join(set(strings))


def VariantSetNames(selections):
    return _Summary((s.variant.setName for s in selections))


def ItemNames(selections):
    return _Summary((s.name for s in selections))


def AreAllVariants(selections):
    if not selections:
        return False
    return not any(s.isVariantSet for s in selections)


def AreAllVariantSets(selections):
    if not selections:
        return False
    return all(s.isVariantSet for s in selections)


class AddVariant(MenuAction):
    defaultText = 'Add Variant'

    def Update(self, action, context):
        action.setVisible(bool(AreAllVariantSets(context.selectedVariantItems)))

    def Do(self):
        context = self.GetCurrentContext()
        selections = context.selectedVariantItems
        name, _ = QtWidgets.QInputDialog.getText(
            context.variantView,
            'Enter New Variant Name',
            'Name for the new variant \n%s=:'
            % '/'.join((i.variant.setName for i in selections)))
        if not name:
            return
        for selectedItem in selections:
            # want to add new variant inside of parents variant context.
            with CreateVariantContext(selectedItem.prim,
                                      selectedItem.parentVariants,
                                      select=True):
                selectedItem.variantSet.AddVariant(name)
            # FIXME: Object changed stage notices
            context.variantView.model().RebuildUnder(item=selectedItem)


def _GetVariantSetName(parent):
    name, _ = QtWidgets.QInputDialog.getText(
        parent,
        'Enter New Variant Set Name',
        'Name for the new variant set:')
    return name


class AddNestedVariantSet(MenuAction):

    def Update(self, action, context):
        if not AreAllVariants(context.selectedVariantItems):
            action.setVisible(False)
            return
        text = 'Add Nested Variant Set Under "%s"' % \
               ItemNames(context.selectedVariantItems)
        action.setText(text)

    def Do(self):
        context = self.GetCurrentContext()
        name = _GetVariantSetName(context.variantView)
        if not name:
            return

        for selectedItem in context.selectedVariantItems:
            # want to add new variant set inside of parents variant context.
            with CreateVariantContext(selectedItem.prim,
                                      selectedItem.variants,
                                      select=True):
                selectedItem.prim.GetVariantSets().AddVariantSet(name)
            # FIXME: Object changed stage notices
            context.variantView.model().RebuildUnder(item=selectedItem)


class AddVariantSet(MenuAction):
    defaultText = 'Add Top Level Variant Set'

    def Update(self, action, context):
        if (context.variantView.model().prim and
                len(context.selectedVariantItems) == 0):
            action.setVisible(True)
        else:
            action.setVisible(False)

    def Do(self):
        context = self.GetCurrentContext()
        name = _GetVariantSetName(context.variantView)
        if not name:
            return
        model = context.variantView.model()
        model.prim.GetVariantSets().AddVariantSet(name)
        # rebuild under the root or just reset the model...
        prim = model.prim
        model.ResetPrim(prim=None)
        model.ResetPrim(prim=prim)


class AddReference(MenuAction):
    referenceAdded = QtCore.Signal()

    def Update(self, action, context):
        selections = context.selectedVariantItems
        if len(selections) != 1 or not AreAllVariants(selections):
            action.setVisible(False)
            return
        text = 'Add Reference Under "%s"' \
               % ItemNames(context.selectedVariantItems)
        action.setText(text)

    def Do(self):
        context = self.GetCurrentContext()
        item = context.selectedVariantItems[0]
        path = UsdQtHooks.Call('GetReferencePath',
                               context.variantView,
                               stage=context.stage)
        if not path:
            return
        with CreateVariantContext(item.prim,
                                  item.variants,
                                  select=False):
            item.prim.GetReferences().SetReferences([Sdf.Reference(path)])
        context.variantView.model().RebuildUnder(item=item)


class SelectVariant(MenuAction):
    defaultText = 'Select / Deselect Variant'

    def Update(self, action, context):
        selections = context.selectedVariantItems
        action.setVisible(AreAllVariants(selections) and
                          all(s.accessible for s in selections))

    def Do(self):
        context = self.GetCurrentContext()
        item = context.selectedVariantItems[0]
        context.variantView.model().SelectVariant(item)


class Remove(MenuAction):

    def Update(self, action, context):
        if not context.selectedVariantItems:
            action.setVisible(False)
            return
        text = 'Remove "%s"' % ItemNames(context.selectedVariantItems)
        action.setText(text)

    def Do(self):
        removed = []
        context = self.GetCurrentContext()
        for item in sorted(context.selectedVariantItems, key=lambda x: x.path):
            for removedPath in removed:
                if item.path.HasPrefix(removedPath):
                    continue
            removed.append(item.path)
            context.variantView.model().RemoveItem(item)


class VariantTreeView(ContextMenuMixin, QtWidgets.QTreeView):

    def __init__(self, parent=None, contextMenuActions=None):
        if not contextMenuActions:
            contextMenuActions = [AddVariant,
                                  AddNestedVariantSet,
                                  AddVariantSet,
                                  AddReference,
                                  SelectVariant,
                                  Remove]
        super(VariantTreeView, self).__init__(
            parent=parent,
            contextMenuActions=contextMenuActions)
        self.setSelectionMode(self.ExtendedSelection)

    def SelectedVariantItems(self):
        indexes = self.selectionModel().selectedRows(0)
        return [index.internalPointer() for index in indexes]

    def GetMenuContext(self):
        items = self.SelectedVariantItems()
        return VariantEditorContext(variantView=self,
                                    stage=self.model().stage,
                                    selectedVariantItems=items,
                                    editTargetLayer=self.model().GetEditLayer())


VariantEditorContext = namedtuple('VariantEditorContext',
                                  ['variantView',
                                   'stage',
                                   'selectedVariantItems',
                                   'editTargetLayer'])


class VariantEditor(QtWidgets.QWidget):
    """A widget that displays a hierarchy of variants and allows adding and
    removing variant specs
    """
    def __init__(self, stage, prim=None, parent=None):
        """
        Parameters
        ----------
        stage : Usd.Stage
        prim : Usd.Prim
        parent : Optional[QtGui.QWidget]
        """
        super(VariantEditor, self).__init__(parent=parent)
        self._stage = stage
        self.dataModel = VariantModel(stage, prim=prim, parent=self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.view = VariantTreeView(parent=self)
        self.view.setModel(self.dataModel)
        layout.addWidget(self.view)
        self.view.setColumnWidth(0, 400)
        self.view.setColumnWidth(1, 100)
        self.view.setColumnWidth(2, 100)
        self.view.setExpandsOnDoubleClick(False)
        self.view.doubleClicked.connect(self.SelectVariant)

    def SelectVariant(self, selectedIndex=None):
        if not selectedIndex:
            selectedIndexes = self.view.selectedIndexes()
            if not selectedIndexes:
                return
            selectedIndex = selectedIndexes[0]

        item = selectedIndex.internalPointer()
        if not isinstance(item, VariantItem):
            return

        self.dataModel.SelectVariant(item)


class VariantEditorDialog(QtWidgets.QDialog):
    INVALID_EDIT_TARGET = 'Warning: Not editing local layer!'
    def __init__(self, stage, prim=None, parent=None):
        """
        Parameters
        ----------
        stage : Usd.Stage
        prim : Usd.Prim
        parent : Optional[QtGui.QWidget]
        """
        super(VariantEditorDialog, self).__init__(parent=parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.editor = VariantEditor(stage, prim=prim, parent=self)
        layout.addWidget(self.editor)
        self._listener = None
        self._stage = None
        self._title = None
        self.ResetStage(stage)

        # Widget and other Qt setup
        self.setModal(False)
        self.resize(700, 500)

    def ResetStage(self, stage):
        if stage:
            self._listener = \
                Tf.Notice.Register(Usd.Notice.StageEditTargetChanged,
                                   self._OnEditTargetChanged,
                                   stage)
        else:
            if self._listener:
                self._listener.Revoke()
            self._listener = None
        self._stage = stage
        self._CheckValidEditTarget()

    def _CheckValidEditTarget(self):
        """Make sure the edit target is one where we can add/remove variants.

        Note: I suspect we might be able to get around this by delving into
        the spec edits. However, eventually I'd like to be able to set a
        variant edit context and author arbitrary edits in the outliner.

        Returns
        -------
        isValid : bool
        """
        if not self._stage:
            self.setWindowTitle('No stage loaded.')
            return False

        editLayer = self._stage.GetEditTarget().GetLayer()
        if not self._stage.HasLocalLayer(editLayer):
            # warn that adding references and nested variants will fail.
            self.setWindowTitle(self.INVALID_EDIT_TARGET)
            return False
        elif self.windowTitle() == self.INVALID_EDIT_TARGET:
            self.setWindowTitle(self._title)
        return True

    def _OnEditTargetChanged(self, notice, stage):
        self._CheckValidEditTarget()

    @QtCore.Slot()
    def OnPrimSelectionChanged(self, selected=None, deselected=None):
        prims = self.sender().SelectedPrims()
        title = '<multiple prims selected>'
        prim = None
        if len(prims) == 1:
            prim = prims[0]
            title = prim.GetPath().pathString
        elif len(prims) == 0:
            title = '<no selection>'

        self.editor.dataModel.ResetPrim(prim=prim)
        self._title = 'Variant Editor: %s' % title
        self.setWindowTitle(self._title)
        self._CheckValidEditTarget()
