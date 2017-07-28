from __future__ import absolute_import

import operator

from pxr import Sdf, Usd
import usdlib.utils
import usdlib.variants
from Qt import QtCore, QtGui, QtWidgets
from treemodel.itemtree import LazyItemTree, TreeItem
from treemodel.qt.base import AbstractTreeModelMixin
from usdqt.common import NULL_INDEX, DARK_ORANGE

from typing import (Any, Dict, Iterable, Iterator, List, Optional,
                    NamedTuple, Tuple, TypeVar, Union)

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


class AssetTreeView(QtWidgets.QTreeView):
    '''
    Basic ``QTreeView`` subclass for displaying asset data.
    '''
    def __init__(self, parent=None):
        '''
        Parameters
        ----------
        parent : Optional[QtGui.QWidget]
        '''
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
        self.EndPrimHierarchyChange(item)

    def AddNewPrim(self, modelIndex, parentPrim, primName, primType='Xform',
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
        if value == NO_VARIANT_SELECTION:
            item.prim.GetVariantSet(setName).ClearVariantSelection()
        else:
            item.prim.GetVariantSet(setName).SetVariantSelection(value)
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
        self.itemTree.removeItems(item)
        result = self._stage.RemovePrim(prim.GetPath())
        self.endRemoveRows()
        return result

    # FIXME: luma-specific
    def AddNewReference(self, modelIndex, parentPrim, refPath,
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
        except (dbfiles.UsdDBParsingError, KeyError, ImportError):
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


class ContextMenuCallback(object):
    '''descriptor for passing on builder selection to builder methods'''

    def __init__(self, func, supportsMultiSelection=False):
        self.func = func
        self.supportsMultiSelection = supportsMultiSelection

    def __call__(self, *args, **kwargs):
        selection = [s for s in self.builder.GetSelection() if s.prim]
        if selection:
            if self.supportsMultiSelection:
                return self.func(self.builder, selection, *args, **kwargs)
            return self.func(self.builder, selection[0], *args, **kwargs)

    def __get__(self, builder, objtype):
        self.builder = builder
        return self


def passSingleSelection(f):
    '''
    decorator to get the first selection item from the outliner and pass it
    into the decorated function.

    Parameters
    ----------
    f : Callable
        This method should operate on a single Selection object.

    Returns
    -------
    Callable
    '''
    return ContextMenuCallback(f, supportsMultiSelection=False)


def passMultipleSelection(f):
    '''
    decorator to get the current selection from the outliner and pass it
    into the decorated function.

    Parameters
    ----------
    f : Callable
        This method should operate on a list of Selection objects.

    Returns
    -------
    Callable
    '''
    return ContextMenuCallback(f, supportsMultiSelection=True)


class ContextMenuBuilder(object):
    '''
    Class to customize the building of right-click context menus for selected
    prims.
    '''
    def __init__(self, view):
        self.view = view

    @property
    def model(self):
        return self.view._dataModel

    def GetSelection(self):
        '''
        Returns
        -------
        List[Selection]
        '''
        indexes = self.view.selectionModel().selectedRows()
        if not indexes:
            return Selection(None, None, None)

        items = [index.internalPointer() for index in indexes]  # type: List[UsdPrimItem]
        # FIXME: Do we need to support selection for primItem.prim = None?
        return [Selection(index, item, item.prim or None) for item in items]

    def Build(self, menu, selections):
        '''
        Build and return the top-level context menu for the view.

        Parameters
        ----------
        menu : QtWidgets.QMenu
        selections : List[Selection]

        Returns
        -------
        Optional[QtWidgets.QMenu]
        '''
        singleSelection = len(selections) == 1

        def connectAction(action, method):
            if singleSelection or method.supportsMultiSelection:
                action.triggered.connect(method)
            else:
                action.setEnabled(False)

        anyActive = any((s.prim.IsActive() for s in selections))
        a = menu.addAction('Deactivate' if anyActive else 'Activate')
        connectAction(a, self.DeactivatePrim if anyActive else self.ActivatePrim)

        a = menu.addAction('Add Transform...')
        connectAction(a, self.AddNewPrim)
        a = menu.addAction('Add Reference...')
        connectAction(a, self.AddReference)

        if singleSelection:
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
                                self.model.PrimVariantChanged(
                                    selection.index, n, v, item=selection.item))

            menu.addSeparator()
            spec = self.model.GetPrimSpecAtEditTarget(selections[0].prim)
            removeLabel = 'Remove Prim'
            removeEnabled = False
            if spec:
                if spec.specifier == Sdf.SpecifierDef:
                    removeEnabled = True
                elif spec.specifier == Sdf.SpecifierOver:
                    removeLabel = 'Remove Prim Edits'
                    removeEnabled = True
            a = menu.addAction(removeLabel)
            connectAction(a, self.RemovePrim)
            a.setEnabled(removeEnabled)
        return menu

    @passMultipleSelection
    def ActivatePrim(self, multiSelection):
        for selection in multiSelection:
            if not selection.prim.IsActive():
                self.model.TogglePrimActive(selection.index, selection.prim,
                                            item=selection.item)

    @passMultipleSelection
    def DeactivatePrim(self, multiSelection):
        for selection in multiSelection:
            if selection.prim.IsActive():
                self.model.TogglePrimActive(selection.index, selection.prim,
                                            item=selection.item)

    @passSingleSelection
    def AddNewPrim(self, selection):
        # TODO: Right now, this doesn't override the primType passed to the
        # model's AddNewPrim method, so this only produces Xforms. May need to
        # support the ability to specify types for new prims eventually.
        name, _ = QtWidgets.QInputDialog.getText(self.view, 'Enter Prim Name',
                                                 'Name for the new transform:')
        if not name:
            return
        newPath = selection.prim.GetPath().AppendChild(name)
        if self.model.stage.GetPrimAtPath(newPath):
            QtWidgets.QMessageBox.warning(self.view, 'Duplicate Prim Path',
                                          'A prim already exists at '
                                          '{0}'.format(newPath))
            return
        self.model.AddNewPrim(selection.index, selection.prim, name,
                              item=selection.item)

    @passSingleSelection
    def RemovePrim(self, selection):
        answer = QtWidgets.QMessageBox.question(
            self.view, 'Confirm Prim Removal',
            'Remove prim (and any children) at {0}?'.format(
                selection.prim.GetPath()),
            buttons=(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel),
            defaultButton=QtWidgets.QMessageBox.Ok)
        if answer == QtWidgets.QMessageBox.Ok:
            self.model.RemovePrimFromCurrentLayer(selection.index,
                                                  selection.prim,
                                                  item=selection.item)

    # FIXME: luma-specific
    def _GetNewReferencePaths(self):
        '''Opens a dialog to get a prim name and path from the user

        Returns
        -------
        Iterator[Tuple[str, str]]
            mapping prim names to reference paths
        '''
        import luma_qt.lumaFileBrowser
        import luma_usd.registry
        import luma_usd.dbfiles
        import luma.project
        import luma.filepath

        # Try to find the project...
        startPath = None
        project = None
        try:
            usdPathsToTry = [self.model.stage.GetRootLayer().identifier]
            # stage might be an in-memory, so root layer might be an
            # anonymous...
            # so try subLayersPaths too
            usdPathsToTry.extend(self.model.stage.GetRootLayer().subLayerPaths)
            for usdPath in usdPathsToTry:
                try:
                    parsedSqlPath = luma_usd.dbfiles.parse(usdPath)
                except luma_usd.dbfiles.UsdDBParsingError:
                    try:
                        project = luma.filepath.Path(usdPath).projectClass()
                    except luma.filepath.NamingConventionError:
                        pass
                else:
                    if 'project' in parsedSqlPath[1]:
                        project = luma.project.Project(
                            parsedSqlPath[1]['project'])
                if project is not None:
                    startPath = project.modelDir
                    break
        except Exception:
            import traceback
            print "Error extracting project modelDir:"
            traceback.print_exc()

        result = luma_qt.lumaFileBrowser.lumaBrowser(
            package='maya',
            mode=luma_qt.lumaFileBrowser.UsdAssetBrowser.mode,
            initialPath=startPath
        )
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
    @passSingleSelection
    def AddReference(self, selection):
        for primName, referencePath in self._GetNewReferencePaths():
            self.model.AddNewReference(selection.index, selection.prim,
                                       referencePath, primName)


class OutlinerTreeView(AssetTreeView):
    # emitted when a prim has been selected in the view
    primSelectionChanged = QtCore.Signal(list, list)

    def __init__(self, dataModel, menuBuilder=None, parent=None):
        '''
        Parameters
        ----------
        dataModel : OutlinerStageModel
        menuBuilder : Optional[Type[ContextMenuBuilder]]
        parent : Optional[QtGui.QWidget]
        '''
        super(OutlinerTreeView, self).__init__(parent=parent)
        self.setModel(dataModel)
        self._dataModel = dataModel
        if menuBuilder is None:
            menuBuilder = ContextMenuBuilder
        self._menuBuilder = menuBuilder(self)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        # keep a ref for model because of refCount bug in pyside
        selectionModel = self.selectionModel()
        selectionModel.selectionChanged.connect(self._SelectionChanged)

    # Qt methods ---------------------------------------------------------------
    def contextMenuEvent(self, event):
        selection = [s for s in self._menuBuilder.GetSelection() if s.prim]
        if not selection:
            return
        menu = QtWidgets.QMenu(self)
        menu = self._menuBuilder.Build(menu, selection)
        if menu is None:
            return
        menu.exec_(event.globalPos())
        event.accept()

    # Custom methods -----------------------------------------------------------
    def _SelectionChanged(self, selected, deselected):
        '''Connected to selectionChanged '''
        def toPrims(qSelection):
            indexes = qSelection.indexes()
            prims = [index.internalPointer().prim for index in indexes
                     if index.column() == 0]
            return prims

        self.primSelectionChanged.emit(toPrims(selected), toPrims(deselected))


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
