from __future__ import absolute_import

import operator

from pxr import Sdf, Usd
import usdlib.stage
import usdlib.utils
import usdlib.variants
from Qt import QtCore, QtGui, QtWidgets
from treemodel.itemtree import LazyItemTree, TreeItem
from treemodel.qt import AbstractTreeModelMixin
from usdqt.common import NULL_INDEX, DARK_ORANGE

from typing import (Any, Dict, Iterable, Iterator, List, Optional,
                    Tuple, TypeVar, Union)


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


class AssetTreeView(QtWidgets.QTreeView):
    '''
    Basic ``QTreeView`` subclass for displaying asset data.
    '''
    def __init__(self, parent=None):
        super(AssetTreeView, self).__init__(parent=parent)

        # QAbstractItemView(?) options
        self.setAlternatingRowColors(True)
        #         self.setSortingEnabled(True)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.ExtendedSelection)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        #         self.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.setEditTriggers(self.CurrentChanged | self.SelectedClicked)

        # QTreeView-specific options
        self.setUniformRowHeights(True)
        self.header().setStretchLastSection(True)


class LazyPrimItemTree(LazyItemTree[UsdPrimItem]):

    def __init__(self, rootPrim, primFilter=None):
        assert isinstance(rootPrim, Usd.Prim)
        if primFilter is not None:
            assert callable(primFilter)
        self.primFilter = primFilter

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
        primFilter = self.primFilter
        if primFilter is None:
            for child in startPrim.GetAllChildren():
                yield child
            return

        it = iter(Usd.PrimRange.AllPrims(startPrim))
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
        itemTree = LazyPrimItemTree(self._stageRoot)

        super(OutlinerStageModel, self).__init__(itemTree=itemTree,
                                                 parent=parent)

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

    def getPrimSpecAtEditTarget(self, prim):
        '''
        Return a PrimSpec for the given prim in the layer containing the stage's
        current edit target. This may be None if the layer does not contain
        authored opinions about the prim.
        
        Parameters
        ----------
        prim : Usd.Prim
        
        Returns
        -------
        Sdf.PrimSpec
        '''
        return self._stage.GetEditTarget().GetPrimSpecForScenePath(prim.GetPath())

    # TODO: Possibly reconsider this design.
    # - Should we implement insert/removeRow(s) to handle the begin/end calls?
    # - Do we want to put the business logic for stage changes on the model, the
    #   view, or the app? This approach is sort of designed for one of the two
    #   latter options.
    def beginPrimHierarchyChange(self, modelIndex, item=None):
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

    def endPrimHierarchyChange(self, item):
        '''
        Parameters
        ----------
        item : UsdPrimItem
        '''
        self.itemTree.forgetChildren(item)
        self.endRemoveRows()

    def togglePrimActive(self, modelIndex, prim, item=None):
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
        self.beginPrimHierarchyChange(modelIndex, item=item)
        prim.SetActive(newState)
        self.endPrimHierarchyChange(item)

    def addNewPrim(self, modelIndex, parentPrim, primName, primType='Xform',
                   item=None):
        '''
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
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

    def primVariantChanged(self, modelIndex, setName, value, item=None):
        '''
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
        setName : str
        value : str
        item : Optional[UsdPrimItem]
        '''
        self.beginPrimHierarchyChange(modelIndex, item=item)
        item.prim.GetVariantSet(setName).SetVariantSelection(value)
        self.endPrimHierarchyChange(item)

    def removePrimFromCurrentLayer(self, modelIndex, prim, item=None):
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
        self.itemTree.removeItems(item)
        result = self._stage.RemovePrim(prim.GetPath())
        self.endRemoveRows()
        return result

    # FIXME: luma-specific
    def addNewReference(self, modelIndex, parentPrim, refPath,
                        primName, item=None):
        '''
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
        parentPrim : Usd.Prim
        refPath : str
        primName : str
        item : Optional[UsdPrimItem]
        '''
        if item is None:
            item = modelIndex.internalPointer()  # type: UsdPrimItem

        refPrimPath = parentPrim.GetPath().AppendChild(primName)
        refPrim = self._stage.DefinePrim(refPrimPath)
        assert refPrim, 'Failed to create new prim at %s' % str(refPrimPath)
        print 'Adding new reference:', refPath

        # FIXME: Stopgap solution, remove when we have variant editor.
        from luma_usd import dbfiles
        try:
            # if we can parse the path, add a reference under an element
            # variant so that we have element control downstream.
            _, parseDict = dbfiles.parse(refPath)
            variantTuples = [('elem', parseDict['elem'])]
        except (dbfiles.UsdDBParsingError, KeyError):
            variantTuples = []
        # END Stopgap

        with usdlib.variants.VariantContext(refPrim, variantTuples,
                                            setAsDefaults=True):
            success = refPrim.GetReferences().SetReferences(
                [Sdf.Reference(refPath)])

        if success:
            childCount = self.itemTree.childCount(parent=item)
            newItems = self.itemTree.appendPrim(refPrim, item)
            if newItems:
                self.beginInsertRows(modelIndex, childCount,
                                     childCount + len(newItems) - 1)
                self.endInsertRows()

    def activeLayerChanged(self, layer):
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        '''
        # emit a signal that will make the delegates redraw their items.
        self.dataChanged.emit(NULL_INDEX, NULL_INDEX)

    def resetStage(self, layer):
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        '''
        self.beginResetModel()
        self.itemTree = LazyPrimItemTree(self._stageRoot)
        self.endResetModel()


class OutlinerTreeView(AssetTreeView):
    def __init__(self, dataModel, parent=None):
        '''
        Parameters
        ----------
        dataModel : OutlinerStageModel
        parent : Optional[QtGui.QWidget]
        '''
        super(OutlinerTreeView, self).__init__(parent=parent)
        self.setModel(dataModel)
        self._dataModel = dataModel
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

    # Qt methods ---------------------------------------------------------------
    def contextMenuEvent(self, event):
        index, item, prim = self._getSelectedIndexItemAndPrim()
        if prim is None:
            return

        menu = self.buildContextMenu(index, item, prim)
        menu.exec_(event.globalPos())
        event.accept()

    # Custom methods -----------------------------------------------------------
    def _getSelectedIndexItemAndPrim(self):
        '''
        Returns
        -------
        Tuple[Optional[QtCore.QModelIndex], Optional[UsdPrimItem], Optional[Usd.Prim]]
        '''
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return (None, None, None)

        index = indexes[0]
        item = index.internalPointer()  # type: UsdPrimItem
        prim = item.prim
        if not prim:
            return (index, item, None)
        return (index, item, prim)

    def togglePrimActive(self):
        index, item, prim = self._getSelectedIndexItemAndPrim()
        if prim is not None:
            self._dataModel.togglePrimActive(index, prim, item=item)

    def addNewPrim(self, spec=None):
        index, item, prim = self._getSelectedIndexItemAndPrim()
        if prim is None:
            return
        # TODO: Right now, this doesn't override the primType passed to the
        # model's addNewPrim method, so this only produces Xforms. May need to
        # support the ability to specify types for new prims eventually.
        name, _ = QtWidgets.QInputDialog.getText(self, 'Enter Prim Name',
                                                 'Name for the new transform:')
        if not name:
            return
        newPath = prim.GetPath().AppendChild(name)
        if self._dataModel.stage.GetPrimAtPath(newPath):
            QtWidgets.QMessageBox.warning(self, 'Duplicate Prim Path',
                                          'A prim already exists at '
                                          '{0}'.format(newPath))
            return
        self._dataModel.addNewPrim(index, prim, name, item=item)

    def removePrim(self):
        index, item, prim = self._getSelectedIndexItemAndPrim()
        if prim is None:
            return
        if QtWidgets.QMessageBox.question(
                self,
                'Confirm Prim Removal',
                'Remove prim (and any children) at {0}?'.format(prim.GetPath()),
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Ok) == QtWidgets.QMessageBox.Ok:
            self._dataModel.removePrimFromCurrentLayer(index, prim, item=item)

    # FIXME: luma-specific
    def _getNewReferencePaths(self):
        '''Opens a dialog to get a prim name and path from the user
        (Luma specific).

        Returns
        -------
        Iterator[Tuple[str, str]]
            mapping prim names to reference paths
        '''
        import luma_qt.lumaFileBrowser
        import luma_usd.registry
        result = luma_qt.lumaFileBrowser.lumaBrowser(
            package='maya',
            mode=luma_qt.lumaFileBrowser.UsdAssetBrowser.mode)
        if not result:
            return

        for item in result:
            addSuffix = item['copies'] > 1
            for i in xrange(item['copies']):
                path = item['path']
                primName = item['primName']
                if addSuffix:
                    primName += str(i + 1).zfill(2)
                registryPath = luma_usd.registry.getRegistryFromPath(path)
                if registryPath:
                    yield primName, registryPath

    # FIXME: add ability to add references to existing prims
    def addReference(self):
        index, item, prim = self._getSelectedIndexItemAndPrim()
        if prim is None:
            return

        for primName, referencePath in self._getNewReferencePaths():
            self._dataModel.addNewReference(index, prim, referencePath,
                                            primName)

    def buildContextMenu(self, modelIndex, primItem, prim):
        '''
        Build and return the top-level context menu for the view.
        
        Parameters
        ----------
        modelIndex: QtCore.QModelIndex
        primItem : UsdPrimItem
        prim : Usd.Prim
        
        Returns
        -------
        QtWidgets.QMenu
        '''
        menu = QtWidgets.QMenu(self)
        a = menu.addAction('Deactivate' if prim.IsActive() else 'Activate')
        a.triggered.connect(self.togglePrimActive)
        a = menu.addAction('Add Transform...')
        a.triggered.connect(self.addNewPrim)
        a = menu.addAction('Add Reference...')
        a.triggered.connect(self.addReference)

        if prim.HasVariantSets():
            variantMenu = menu.addMenu('Variants')
            for setName, currentValue in usdlib.variants.getPrimVariants(prim):
                setMenu = variantMenu.addMenu(setName)
                variantSet = prim.GetVariantSet(setName)
                for setValue in variantSet.GetVariantNames():
                    a = setMenu.addAction(setValue)
                    if setValue == currentValue:
                        a.setCheckable(True)
                        a.setChecked(True)
                        continue
                    # Note: This is currently only valid for PySide. PyQt always
                    # passes the action's `checked` value.
                    a.triggered.connect(
                        lambda n=setName, v=setValue: \
                            self._dataModel.primVariantChanged(modelIndex, n, v,
                                                               item=primItem))

        menu.addSeparator()
        spec = self._dataModel.getPrimSpecAtEditTarget(prim)
        removeLabel = 'Remove Prim'
        removeEnabled = False
        if spec:
            if spec.specifier == Sdf.SpecifierDef:
                removeEnabled = True
            elif spec.specifier == Sdf.SpecifierOver:
                removeLabel = 'Remove Prim Edits'
                removeEnabled = True
        a = menu.addAction(removeLabel)
        a.triggered.connect(self.removePrim)
        a.setEnabled(removeEnabled)
        return menu


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

    def setActiveLayer(self, layer):
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        '''
        self._activeLayer = layer

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
