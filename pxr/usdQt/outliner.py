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

from __future__ import absolute_import

import operator

from ._Qt import QtCore, QtGui, QtWidgets
from pxr import Sdf, Usd

import usdlib.utils
import usdlib.variants
from treemodel.itemtree import LazyItemTree, TreeItem
from treemodel.qt.base import AbstractTreeModelMixin
from .common import NULL_INDEX, DARK_ORANGE, passSingleSelection, \
    passMultipleSelection, ContextMenuBuilder, ContextMenuMixin, \
    UsdQtUtilities, ContextMenuAction

from typing import *

NO_VARIANT_SELECTION = '<No Variant Selected>'


class GroupItem(TreeItem):
    '''
    TreeItem holding an arbitrary UI group, not related to a prim
    '''

    def __init__(self, groupName):
        super(GroupItem, self).__init__('__GROUP__%s' % groupName)
        self.name = groupName


class UsdPrimItem(TreeItem):
    '''
    TreeItem holding a Usd Prim.

    If the prim has variants it is expected to be instantiated wtih a
    `VariablePrimHelper`.
    '''

    def __init__(self, prim, variantHelper=None):
        '''
        Parameters
        ----------
        prim : Usd.Prim
        variantHelper : Optional[usdlib.variants.VariablePrimHelper]
            this is expected to be passed if `prim` has variants
        '''
        import usdlib.utils
        self.prim = prim
        self.variantHelper = variantHelper
        self.name = prim.GetName()
        self.type = prim.GetTypeName()
        # reuse this data if we've already queried it
        if variantHelper:
            self.path = variantHelper.path
            self.assetName = variantHelper.assetName
        else:
            self.path = str(prim.GetPath())
            self.assetName = usdlib.utils.getAssetName(prim)
        super(UsdPrimItem, self).__init__(self.path)


class LazyPrimItemTree(LazyItemTree[UsdPrimItem]):

    def __init__(self, rootPrim, primFilter=None, primPredicate=None):
        assert isinstance(rootPrim, Usd.Prim)
        if primFilter is not None:
            assert callable(primFilter)
        self.primFilter = primFilter
        self.primPredicate = primPredicate or Usd.PrimDefaultPredicate

        super(LazyPrimItemTree, self).__init__(rootItem=UsdPrimItem(rootPrim))

    # LazyItemTree methods -----------------------------------------------------
    def _fetchItemChildren(self, parent):
        '''
        Parameters
        ----------
        parent : UsdPrimItem

        Returns
        -------
        List[UsdPrimItem]
        '''
        return self.getChildPrimItems(parent.prim)

    # Custom methods -----------------------------------------------------------
    def iterFilteredChildPrims(self, startPrim):
        '''
        Returns an iterator over the next child prims of `startPrim` that
        satisfy `self.primFilter(child)`.

        This will traverse down the prim tree from each immediate child of
        `startPrim` until a qualifying prim is found or that branch of the
        hierarchy is exhausted.

        Parameters
        ----------
        startPrim : Usd.Prim

        Returns
        -------
        Iterator[Usd.Prim]
        '''
        if not startPrim.IsValid():
            return
        primFilter = self.primFilter
        if primFilter is None:
            for child in startPrim.GetFilteredChildren(self.primPredicate):
                yield child
            return

        it = iter(Usd.PrimRange(startPrim, self.primPredicate).AllPrims(startPrim))
        it.next()
        for child in it:
            if primFilter(child):
                yield child
                it.PruneChildren()

    def getChildPrimItems(self, startPrim):
        '''
        Parameters
        ----------
        startPrim : Usd.Prim

        Returns
        -------
        List[UsdPrimItem]
        '''
        return sorted(
            (UsdPrimItem(c) for c in self.iterFilteredChildPrims(startPrim)),
            key=operator.attrgetter('name'))

    def appendPrim(self, prim, parentItem=None):
        if self.primFilter is None or self.primFilter(prim):
            newItems = [UsdPrimItem(prim)]
        else:
            newItems = self.getChildPrimItems(prim)
        self.addItems(newItems, parent=parentItem)
        return newItems


class OutlinerStageModel(AbstractTreeModelMixin, QtCore.QAbstractItemModel):
    '''
    '''
    primChanged = QtCore.Signal(Usd.Prim)

    def __init__(self, stage, parent=None):
        '''
        Parameters
        ----------
        stage : Usd.Stage
        parent : Optional[QtGui.QWidget]
        '''
        assert isinstance(stage, Usd.Stage)

        self._stage = stage
        self._stageRoot = stage.GetPseudoRoot()
        # display defined prims but also include inactive/unloaded prims so
        # they can be activated.
        self._primPredicate = Usd.PrimIsDefined
        itemTree = LazyPrimItemTree(self._stageRoot,
                                    primPredicate=self._primPredicate)

        super(OutlinerStageModel, self).__init__(itemTree=itemTree,
                                                 parent=parent)

    # Qt methods ---------------------------------------------------------------
    def columnCount(self, parentIndex):
        return 2

    def flags(self, modelIndex):
        if modelIndex.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        return QtCore.Qt.NoItemFlags

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if section == 0:
                return 'Prim Name'
            elif section == 1:
                return 'Asset'

    def data(self, modelIndex, role=QtCore.Qt.DisplayRole):
        if not modelIndex.isValid():
            return
        if role == QtCore.Qt.DisplayRole:
            column = modelIndex.column()
            item = modelIndex.internalPointer()
            if column == 0:
                return item.name
            elif column == 1:
                return item.assetName

    # Custom Methods -----------------------------------------------------------
    @property
    def stage(self):
        '''
        Returns
        -------
        Usd.Stage
        '''
        return self._stage

    def GetPrimSpecAtEditTarget(self, prim):
        '''
        Return a PrimSpec for the given prim in the layer containing the stage's
        current edit target. This may be None if the layer does not contain
        authored opinions about the prim.

        Parameters
        ----------
        prim : Union[Usd.Prim, Sdf.Path]
        
        Returns
        -------
        Sdf.PrimSpec
        '''
        if isinstance(prim, Usd.Prim):
            path = prim.GetPath()
        else:
            path = prim
        return self._stage.GetEditTarget().GetPrimSpecForScenePath(path)

    # TODO: Possibly reconsider this design.
    # - Should we implement insert/removeRow(s) to handle the begin/end calls?
    # - Do we want to put the business logic for stage changes on the model, the
    #   view, or the app? This approach is sort of designed for one of the two
    #   latter options.
    def BeginPrimHierarchyChange(self, modelIndex, item=None):
        '''
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
        item :  Optional[UsdPrimItem]
        '''
        if item is None:
            item = modelIndex.internalPointer()
        self.beginRemoveRows(modelIndex, 0,
                             max(self.itemTree.childCount(parent=item) - 1, 0))

    def EndPrimHierarchyChange(self, item):
        '''
        Parameters
        ----------
        item : UsdPrimItem
        '''
        self.itemTree.forgetChildren(item)
        self.endRemoveRows()

    def TogglePrimActive(self, modelIndex, prim, item=None):
        '''
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
        prim : Usd.Prim
        item : Optional[UsdPrimItem]
        '''
        if item is None:
            item = modelIndex.internalPointer()  # type: UsdPrimItem
        newState = not prim.IsActive()
        self.BeginPrimHierarchyChange(modelIndex, item=item)
        prim.SetActive(newState)
        self.primChanged.emit(prim)
        self.EndPrimHierarchyChange(item)

    def AddNewPrim(self, modelIndex, parentPrim, primName, primType='Xform',
                   item=None):
        '''
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
            new prim's parent model index
        parentPrim : Usd.Prim
        primName : str
        primType : str
        item : Optional[UsdPrimItem]
        '''
        assert primName
        if item is None:
            item = modelIndex.internalPointer()  # type: UsdPrimItem
        newPrimPath = parentPrim.GetPath().AppendChild(primName)
        if primType is None:
            newPrim = self._stage.DefinePrim(newPrimPath)
        else:
            newPrim = self._stage.DefinePrim(newPrimPath, primType)
        assert newPrim, 'Failed to create new prim at %s' % str(newPrimPath)

        childCount = self.itemTree.childCount(parent=item)
        newItems = self.itemTree.appendPrim(newPrim, item)
        if newItems:
            self.beginInsertRows(modelIndex, childCount,
                                 childCount + len(newItems) - 1)
            self.endInsertRows()

    def PrimVariantChanged(self, modelIndex, setName, value, item=None):
        '''
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
        setName : str
        value : str
        item : Optional[UsdPrimItem]
        '''
        self.BeginPrimHierarchyChange(modelIndex, item=item)
        varSet = item.prim.GetVariantSet(setName)
        current = varSet.GetVariantSelection()
        if value == NO_VARIANT_SELECTION:
            varSet.ClearVariantSelection()
        else:
            varSet.SetVariantSelection(value)
        if current != varSet.GetVariantSelection():
            self.primChanged.emit(item.prim)
        self.EndPrimHierarchyChange(item)

    def RemovePrimFromCurrentLayer(self, modelIndex, prim, item=None):
        '''
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
        prim : Usd.Prim
        item : Optional[UsdPrimItem]
        '''
        if item is None:
            item = modelIndex.internalPointer()

        parentIndex = self.parent(modelIndex)
        rowIndex = self.itemTree.rowIndex(item)
        self.beginRemoveRows(parentIndex, rowIndex, rowIndex)
        path = prim.GetPath()
        result = self._stage.RemovePrim(path)
        # check if entire prim is gone or if its just the prim edits that are
        # gone
        prim = self._stage.GetPrimAtPath(path)
        if not prim or prim.GetSpecifier() == Sdf.SpecifierOver:
            self.itemTree.removeItems(item)
        self.endRemoveRows()
        return result

    def _SetReference(self, prim, refPath, refPrimPath=None, variantTuples=None):
        '''Set the references on a prim to be a list of one specific path.'''

        editLayer = self.stage.GetEditTarget().GetLayer()
        if not self.stage.HasLocalLayer(editLayer):
            # We use a temporary stage here to get around the local layer
            # restriction for variant edit contexts.
            editTargetStage = Usd.Stage.Open(editLayer)
            # this assumes prim path is the same in edit target
            prim = editTargetStage.GetPrimAtPath(prim.GetPath())

        with usdlib.variants.VariantContext(prim, variantTuples,
                                            select=True):
            if refPrimPath:
                refs = [Sdf.Reference(refPath, refPrimPath)]
            else:
                refs = [Sdf.Reference(refPath)]
            success = prim.GetReferences().SetReferences(refs)

        return success

    def AddNewReference(self, modelIndex, prim, refPath, refPrimPath=None,
                        variantTuples=None, item=None):
        '''
        Add a reference to an existing prim.

        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
        prim : Usd.Prim
        refPath : str
        variantTuples : Optional[List[Tuple]]
        item : Optional[UsdPrimItem]
        '''
        if item is None:
            item = modelIndex.internalPointer()  # type: UsdPrimItem

        success = self._SetReference(prim,
                                     refPath,
                                     refPrimPath=refPrimPath,
                                     variantTuples=variantTuples)

        if success:
            # adding a reference may change structure of prims children
            self.itemTree.forgetChildren(item)
            self.primChanged.emit(prim)

    def AddNewPrimAndReference(self, modelIndex, parentPrim, refPath, primName,
                               refPrimPath=None, variantTuples=None, item=None):
        '''
        Add a new prim and set it to reference another usd file.

        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
            new prim's parent model index
        parentPrim : Usd.Prim
        refPath : str
        primName : str
        refPrimPath : Optional[str]
        variantTuples : Optional[List[Tuple]]
        item : Optional[UsdPrimItem]

        Returns
        -------
        Optional[Usd.Prim]
        '''
        if item is None:
            item = modelIndex.internalPointer()  # type: UsdPrimItem

        primPath = parentPrim.GetPath().AppendChild(primName)
        newPrim = self._stage.DefinePrim(primPath)
        assert newPrim, 'Failed to create new prim at %s' % str(primPath)
        print 'Adding new reference:', refPath, refPrimPath

        success = self._SetReference(newPrim,
                                     refPath,
                                     refPrimPath=refPrimPath,
                                     variantTuples=variantTuples)

        if success:
            childCount = self.itemTree.childCount(parent=item)
            newItems = self.itemTree.appendPrim(newPrim, item)
            if newItems:
                self.beginInsertRows(modelIndex, childCount,
                                     childCount + len(newItems) - 1)
                self.endInsertRows()
            return newPrim

    def ActiveLayerChanged(self, layer):
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        '''
        # emit a signal that will make the delegates redraw their items.
        self.dataChanged.emit(NULL_INDEX, NULL_INDEX)

    def ResetStage(self, layer=None):
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        '''
        self.beginResetModel()
        self.itemTree = LazyPrimItemTree(self._stageRoot,
                                         primPredicate=self._primPredicate)
        self.endResetModel()


Selection = NamedTuple('Selection', [
    ('index', Optional[QtCore.QModelIndex]),
    ('item', Optional[UsdPrimItem]),
    ('prim', Optional[Usd.Prim]),
])


@passMultipleSelection
class ActivatePrim(ContextMenuAction):
    def label(self, builder, selection):
        anyActive = any((s.prim.IsActive() for s in selection))
        return 'Deactivate' if anyActive else 'Activate'

    def do(self, builder, multiSelection):
        print 'doing!'
        anyActive = any((s.prim.IsActive() for s in multiSelection))
        for selection in multiSelection:
            if not selection.prim.IsValid():
                continue
            if selection.prim.IsActive() == anyActive:
                builder.model.TogglePrimActive(selection.index,
                                               selection.prim,
                                               item=selection.item)


@passSingleSelection
class AddNewPrim(ContextMenuAction):
    def label(self, builder, selection):
        return 'Add Transform...'

    def do(self, builder, selection):
        # TODO: Right now, this doesn't override the primType passed to the
        # model's AddNewPrim method, so this only produces Xforms. May need to
        # support the ability to specify types for new prims eventually.
        name, _ = QtWidgets.QInputDialog.getText(builder.view,
                                                 'Enter Prim Name',
                                                 'Name for the new transform:')
        if not name:
            return
        newPath = selection.prim.GetPath().AppendChild(name)
        if builder.model.GetPrimSpecAtEditTarget(newPath):
            QtWidgets.QMessageBox.warning(builder.view,
                                          'Duplicate Prim Path',
                                          'A prim already exists at '
                                          '{0}'.format(newPath))
            return
        builder.model.AddNewPrim(selection.index,
                                 selection.prim,
                                 name,
                                 item=selection.item)


@passMultipleSelection
class RemovePrim(ContextMenuAction):
    def label(self, builder, selections):
        label = 'Remove Prims' if len(selections) > 1 else 'Remove Prim'
        for selection in selections:
            spec = builder.model.GetPrimSpecAtEditTarget(selection.prim)
            if spec:
                if spec.specifier == Sdf.SpecifierOver:
                    return 'Remove Prim Edits'
        return label

    def enable(self, builder, selections):
        for selection in selections:
            spec = builder.model.GetPrimSpecAtEditTarget(selection.prim)
            if spec:
                if (spec.specifier == Sdf.SpecifierDef or
                        spec.specifier == Sdf.SpecifierOver):
                    return True
        return False

    def do(self, builder, multiSelection):
        ask = True
        for selection in multiSelection:
            if ask:
                answer = QtWidgets.QMessageBox.question(
                    builder.view, 'Confirm Prim Removal',
                    'Remove prim (and any children) at {0}?'.format(
                        selection.prim.GetPath()),
                    buttons=(QtWidgets.QMessageBox.Yes |
                             QtWidgets.QMessageBox.Cancel |
                             QtWidgets.QMessageBox.YesToAll),
                    defaultButton=QtWidgets.QMessageBox.Yes)
                if answer == QtWidgets.QMessageBox.Cancel:
                    return
                elif answer == QtWidgets.QMessageBox.YesToAll:
                    ask = False
            builder.model.RemovePrimFromCurrentLayer(selection.index,
                                                     selection.prim,
                                                     item=selection.item)


@passSingleSelection
class SelectVariants(ContextMenuAction):

    def Build(self, builder, menu, selections):
        selection = selections[0]
        if selection.prim.HasVariantSets():
            variantMenu = menu.addMenu('Variants')
            for setName, currentValue in usdlib.variants.getPrimVariants(
                    selection.prim):
                setMenu = variantMenu.addMenu(setName)
                variantSet = selection.prim.GetVariantSet(setName)
                for setValue in [NO_VARIANT_SELECTION] + \
                        variantSet.GetVariantNames():
                    a = setMenu.addAction(setValue)
                    a.setCheckable(True)
                    if setValue == currentValue or \
                            (setValue == NO_VARIANT_SELECTION
                             and currentValue == ''):
                        a.setChecked(True)

                    # Note: This is currently only valid for PySide. PyQt
                    # always passes the action's `checked` value.
                    a.triggered.connect(
                        lambda n=setName, v=setValue:
                            builder.model.PrimVariantChanged(
                                selection.index, n, v, item=selection.item))

    def shouldShow(self, builder, selections):
        return len(selections) == 1


@passSingleSelection
class AddReference(ContextMenuAction):
    def label(self, builder, selections):
        return 'Add Reference...'

    def _GetNewReferencePath(self):
        return UsdQtUtilities.exec_('GetReferencePath',
                                    stage=self.model.stage)

    def do(self, builder, selection):
        '''Add a reference directly to an existing prim'''
        refPath = self._GetNewReferencePath()
        builder.model.AddNewReference(selection.index, selection.prim, refPath)


class OutlinerTreeView(ContextMenuMixin, QtWidgets.QTreeView):
    # Emitted with lists of selected and deselected prims
    primSelectionChanged = QtCore.Signal(list, list)

    def __init__(self, dataModel, contextMenuActions=None,
                 contextMenuBuilder=None, parent=None):
        '''
        Parameters
        ----------
        dataModel : OutlinerStageModel
        contextMenuActions : Optional[Callable[[OutlinerTreeView], List[ContextMenuAction]]]
        contextMenuBuilder : Optional[Type[ContextMenuBuilder]]
        parent : Optional[QtGui.QWidget]
        '''
        super(OutlinerTreeView, self).__init__(
            parent=parent,
            contextMenuBuilder=contextMenuBuilder,
            contextMenuActions=contextMenuActions)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.ExtendedSelection)
        self.setEditTriggers(self.CurrentChanged | self.SelectedClicked)

        self.setUniformRowHeights(True)
        self.header().setStretchLastSection(True)

        self.setModel(dataModel)

        # This can't be a one-liner because of a PySide refcount bug.
        selectionModel = self.selectionModel()
        selectionModel.selectionChanged.connect(self._SelectionChanged)

    # Custom methods -----------------------------------------------------------
    def _SelectionChanged(self, selected, deselected):
        '''Connected to selectionChanged'''
        def toPrims(qSelection):
            indexes = qSelection.indexes()
            prims = [index.internalPointer().prim for index in indexes
                     if index.column() == 0]
            return prims

        self.primSelectionChanged.emit(toPrims(selected), toPrims(deselected))

    def SelectedPrims(self):
        indexes = self.selectionModel().selectedRows()
        return [index.internalPointer().prim for index in indexes]

    def GetSelection(self):
        '''
        Returns
        -------
        List[Selection]
        '''
        indexes = self.selectionModel().selectedRows()
        items = [index.internalPointer() for index in indexes]  # type: List[UsdPrimItem]
        return [Selection(index, item, item.prim)
                for index, item in zip(indexes, items) if item.prim]


class OutlinerViewDelegate(QtWidgets.QStyledItemDelegate):
    '''
    Item delegate class assigned to an ``OutlinerTreeView``.
    '''

    def __init__(self, activeLayer, parent=None):
        '''
        Parameters
        ----------
        activeLayer : Sdf.Layer
        parent : Optional[QtGui.QWidget]
        '''
        super(OutlinerViewDelegate, self).__init__(parent=parent)
        self._activeLayer = activeLayer

    # Qt methods ---------------------------------------------------------------
    def paint(self, painter, options, modelIndex):
        if modelIndex.isValid():
            item = modelIndex.internalPointer()
            prim = item.prim
            palette = options.palette
            textColor = palette.color(QtGui.QPalette.Text)
            if prim.HasVariantSets():
                textColor = DARK_ORANGE
            if not prim.IsActive():
                textColor.setAlphaF(.5)
            spec = self._activeLayer.GetPrimAtPath(prim.GetPrimPath())
            if spec:
                specifier = spec.specifier
                if specifier == Sdf.SpecifierDef:
                    options.font.setBold(True)
                elif specifier == Sdf.SpecifierOver:
                    options.font.setItalic(True)
            palette.setColor(QtGui.QPalette.Text, textColor)

        return QtWidgets.QStyledItemDelegate.paint(self, painter, options,
                                                   modelIndex)

    # Custom methods -----------------------------------------------------------
    def SetActiveLayer(self, layer):
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        '''
        self._activeLayer = layer
