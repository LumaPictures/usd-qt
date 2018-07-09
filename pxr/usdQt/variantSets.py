'''
Variant Set and Variant Editing Widget.

TODO:
- Expand selected variants initially
- Possible: Only fetch variant children when requested by expansion for 
  performance. Unfortunately this may mean we loose ui friendliness of the 
  "expandable" indicator 
- Ability to Remove Variants?
- Allow setting variant selections within nested variants?
'''

from __future__ import absolute_import

from pxr import Sdf, Usd
from ._Qt import QtCore, QtGui, QtWidgets
from treemodel.itemtree import TreeItem, LazyItemTree
from treemodel.qt.base import AbstractTreeModelMixin
from .common import NULL_INDEX, ContextMenuBuilder, ContextMenuMixin,\
    passSingleSelection, passMultipleSelection, UsdQtUtilities
import usdlib.variants as varlib

from typing import *


class VariantItem(TreeItem):

    def __init__(self, prim, parentVariants, variantSet, path, varSetKey):
        '''
        Parameters
        ----------
        prim : Usd.Prim
        parentVariants : List[varlib.PrimVariant]
        variantSet : Usd.VariantSet
        path : Sdf.Path
        varSetKey : str
        '''
        self.prim = prim
        self.path = path
        self.variantSet = variantSet
        self.variant = varlib.PrimVariant(*path.GetVariantSelection())
        key = '_'.join((varSetKey, self.variant.variantName))
        super(VariantItem, self).__init__(key=key)
        self.parentVariants = parentVariants

    @property
    def selected(self):
        '''
        Returns
        -------
        bool
        '''
        return self.variantSet.GetVariantSelection() == self.variant.variantName

    @property
    def variants(self):
        '''
        Returns
        -------
        List[varlib.PrimVariant]
        '''
        return self.parentVariants + [self.variant]

    @property
    def name(self):
        '''
        Returns
        -------
        str
        '''
        return '{}={}'.format(*self.variant)


class LazyVariantTree(LazyItemTree):

    def __init__(self, prim):
        self.prim = prim
        super(LazyVariantTree, self).__init__()

    # May want to replace this with an even lazier tree that only fetches
    # children that are explicitly requested by expansion or variant selection.
    # This depends on the cost of switching variants vs. usability.
    def _fetchItemChildren(self, parent):
        if not self.prim:
            return None

        parentVariants = []
        if isinstance(parent, VariantItem):
            if not parent.variant.variantName:
                # clear selections will have no child variants
                return []
            parentVariants = parent.parentVariants + [parent.variant]

        parentKey = varlib.variantSelectionKey(parentVariants)
        level = len(parentVariants)
        # set variants temporarily so that underlying variants can be inspected.
        with varlib.SessionVariantContext(self.prim, parentVariants):
            variantItems = []
            variantSets = set()
            for path, key, primVariant in varlib.getPrimVariantsWithPaths(self.prim):
                if parentKey not in key:
                    continue  # different branch
                if key.count('{') != level:
                    continue  # ancestor or grandchild

                variantSet = self.prim.GetVariantSet(primVariant.setName)
                if variantSet not in variantSets:
                    variantSets.add(variantSet)
                    # add all variants for variant set from parent, because only
                    # the selected ones are included in getPrimVariants
                    parentPath = path.GetParentPath()
                    # for each variant set add a blank '' for clearing selection
                    for name in variantSet.GetVariantNames() + ['']:
                        variantPath = parentPath.AppendVariantSelection(
                            primVariant.setName,
                            name)
                        item = VariantItem(self.prim,
                                           parentVariants,
                                           variantSet,
                                           variantPath,
                                           key)
                        variantItems.append(item)
            return variantItems


class VariantModel(AbstractTreeModelMixin, QtCore.QAbstractItemModel):
    '''Holds a hierarchy of variant sets and their selections
    '''

    def __init__(self, stage, prims, parent=None):
        '''
        Parameters
        ----------
        prims : List[Usd.Prim]
            Current  prim selection
        parent : Optional[QtGui.QWidget]
        '''
        self._stage = stage
        self._prims = prims
        super(VariantModel, self).__init__(parent=parent)
        self.Reset()

    def columnCount(self, parentIndex):
        return 3

    def flags(self, modelIndex):
        if modelIndex.isValid():
            item = modelIndex.internalPointer()
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        return QtCore.Qt.NoItemFlags

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if (orientation == QtCore.Qt.Horizontal and
                role == QtCore.Qt.DisplayRole):
            if section == 0:
                return 'Variant'
            elif section == 1:
                return 'Path'
            elif section == 2:
                return 'Data'

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
            elif column == 2:
                return ''
        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            item = modelIndex.internalPointer()
            if not isinstance(item, VariantItem):
                return
            if not self._stage.GetEditTarget().GetLayer().GetPrimAtPath(item.path):
                font.setItalic(True)
            if item.selected:
                parentIndex = self.parent(modelIndex)
                parent = parentIndex.internalPointer()
                while isinstance(parent, VariantItem):
                    if not parent.selected:
                        return font
                    parentIndex = self.parent(parentIndex)
                    parent = parentIndex.internalPointer()
                font.setBold(True)
            return font

    # Custom Methods -----------------------------------------------------------

    @property
    def prim(self):
        if len(self._prims) == 1:
            return self._prims[0]
        return None

    @property
    def title(self):
        numPrims = len(self._prims)
        if numPrims == 1:
            return self._prims[0].GetPath()
        elif numPrims == 0:
            return '<no selection>'
        else:
            return '<multiple prims selected>'

    def Reset(self):
        self.beginResetModel()
        # only single selection is supported
        if len(self._prims) == 1:
            self.itemTree = LazyVariantTree(self._prims[0])
        self.endResetModel()

    def PrimSelectionChanged(self, selected, deselected):
        prims = set(self._prims)
        prims.difference_update(deselected)
        prims.update(selected)
        self._prims = list(prims)
        self.Reset()

    def EditTargetChanged(self, layer):
        # if the edit target changes we refresh the variants because they
        # display whether they are defined on the edit target
        self.dataChanged.emit(NULL_INDEX, NULL_INDEX)

    def Layer(self):
        return self._stage.GetEditTarget().GetLayer()


class VariantContextMenuBuilder(ContextMenuBuilder):
    '''
    Class to customize the building of right-click context menus for selected
    variants.
    '''


def _summary(strings):
    return '/'.join(set(strings))


def variantSetNames(selections):
    return _summary((s.variant.setName for s in selections))


def variantsNames(selections):
    return _summary((s.name for s in selections))


def hasVariantSelection(selections):
    return all(s.variant.variantName for s in selections)


@passMultipleSelection
class AddVariant(ContextMenuAction):
    def label(self, builder, selections):
        return 'Add "%s" Variant' % variantSetNames(selections)

    def do(self, builder, selections):
        name, _ = QtWidgets.QInputDialog.getText(
            builder.view,
            'Enter New Variant Name',
            'Name for the new variant \n%s=:'
            % '/'.join((i.variant.setName for i in selections)))
        if not name:
            return
        for selectedItem in selections:
            # want to add new variant inside of parents variant context.
            with varlib.VariantContext(selectedItem.prim,
                                       selectedItem.parentVariants,
                                       select=True):
                selectedItem.variantSet.AddVariant(name)
        builder.view.model().Reset()  # TODO: Reload only necessary part


def _GetVariantSetName(view):
    name, _ = QtWidgets.QInputDialog.getText(
        view,
        'Enter New Variant Set Name',
        'Name for the new variant set:')
    return name


@passMultipleSelection
class AddNestedVariant(ContextMenuAction):
    def enable(self, builder, selections):
        # for now only allow one nested variant set per variant
        allowAdding = not any(builder.view.model().itemTree.childCount(parent=s)
                              for s in selections)
        return hasVariantSelection(selections) and allowAdding

    def label(self, builder, selections):
        return 'Add Nested Variant Set Under "%s"' % variantsNames(selections)

    def do(self, builder, selectedItems):
        name = _GetVariantSetName(builder.view)
        if not name:
            return

        for selectedItem in selectedItems:
            # want to add new variant set inside of parents variant context.
            with varlib.VariantContext(selectedItem.prim,
                                       selectedItem.variants,
                                       select=False):
                selectedItem.prim.GetVariantSets().AddVariantSet(name)
        builder.view.model().Reset()  # TODO: Reload only necessary part


class AddVariantSet(ContextMenuAction):
    def label(self, builder, selection):
        return 'Add Top Level Variant Set'

    def enable(self, builder, selection):
        return len(selection) == 0

    def shouldShow(self, builder, selection):
        return self.enable(builder, selection)

    def do(self, builder):
        name = _GetVariantSetName(builder.view)
        if not name:
            return
        builder.view.model().prim.GetVariantSets().AddVariantSet(name)
        builder.view.model().Reset()  # TODO: Reload only necessary part


@passSingleSelection
class AddReference(ContextMenuAction):
    referenceAdded = QtCore.Signal()

    def label(self, builder, selections):
        return 'Add Reference Under "%s"' % variantsNames(selections)

    def enable(self, builder, selections):
        return hasVariantSelection(selections)

    def do(self, builder, item):
        path = UsdQtUtilities.exec_('GetReferencePath',
                                    builder.view,
                                    stage=item.prim.GetStage())
        if not path:
            return
        with varlib.VariantContext(item.prim,
                                   item.variants,
                                   select=False):
            item.prim.GetReferences().SetReferences([Sdf.Reference(path)])
        builder.view.model().Reset()  # TODO: Reload only necessary part


class VariantTreeView(ContextMenuMixin, QtWidgets.QTreeView):

    def __init__(self, parent=None, contextMenuActions=None):
        super(VariantTreeView, self).__init__(
            parent=parent,
            contextMenuBuilder=ContextMenuBuilder,
            contextMenuActions=contextMenuActions)
        self.setSelectionMode(self.ExtendedSelection)

    def defaultContextMenuActions(self, view):
        return [AddVariant(),
                AddNestedVariant(),
                AddVariantSet(),
                AddReference()]


class VariantEditorDialog(QtWidgets.QDialog):
    def __init__(self, stage, prims, parent=None):
        '''
        Parameters
        ----------
        stage : Usd.Stage
        parent : Optional[QtGui.QWidget]
        '''
        super(VariantEditorDialog, self).__init__(parent=parent)
        self.stage = stage
        self.prims = prims
        self.dataModel = VariantModel(stage, prims, parent=self)

        # Widget and other Qt setup
        self.setModal(False)

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
        self.dataModel.modelReset.connect(self.Refresh)
        # expand selected variants which wont have a cost.
        # self.view.expandAll()

        self.resize(700, 500)
        self.Refresh()

    def SelectVariant(self, selectedIndex=None):
        if not selectedIndex:
            selectedIndexes = self.view.selectedIndexes()
            if not selectedIndexes:
                return
            selectedIndex = selectedIndexes[0]

        item = selectedIndex.internalPointer()
        if not isinstance(item, VariantItem):
            return

        # may eventually want to author selections within other variants. Which
        # would require getting a context for the specific parent variant.
        # with item.variantSet.GetVariantEditContext():
        item.variantSet.SetVariantSelection(item.variant.variantName)

        self.dataModel.dataChanged.emit(NULL_INDEX, NULL_INDEX)

    def Refresh(self):
        editLayer = self.stage.GetEditTarget().GetLayer()
        if self.stage.HasLocalLayer(editLayer):
            self.setWindowTitle('Variant Editor: %s' % self.dataModel.title)
        else:
            # warn that adding references and nested variants will fail.
            self.setWindowTitle('Warning: Not editing local layer!')
