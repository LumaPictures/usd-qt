from __future__ import absolute_import

from pxr import Sdf, Usd, Tf
from luma_qt.Qt import QtCore, QtGui, QtWidgets
from treemodel.itemtree import TreeItem, ItemTree, LazyItemTree
from treemodel.qt.base import AbstractTreeModelMixin
from usdQt.common import NULL_INDEX
import usdlib.variants as varlib


class PrimItem(TreeItem):
    def __init__(self, prim):
        super(PrimItem, self).__init__(key=prim.GetPath())
        self.prim = prim
        self.path = prim.GetPath()


class VariantItem(TreeItem):
    def __init__(self, variantSet, path, parentVariants, primVariant):
        '''
        Parameters
        ----------
        variantSet : Usd.VariantSet
        path : Sdf.Path
        parentVariants : List[varlib.PrimVariant]
        primVariant : varlib.PrimVariant
        '''
        super(VariantItem, self).__init__(
            key=varlib.variantSelectionKey(parentVariants + [primVariant]))
        self.variantSet = variantSet
        self.prim = variantSet.GetPrim()
        self.path = path
        self.primVariant = primVariant
        self.parentVariants = parentVariants

    @property
    def selected(self):
        return self.variantSet.GetVariantSelection() == \
               self.primVariant.variantName


class LazyVariantTree(LazyItemTree):

    def _fetchItemChildren(self, parent):
        parentVariants = []
        if isinstance(parent, PrimItem):
            prim = parent.prim
        elif isinstance(parent, VariantItem):
            prim = parent.prim
            if not parent.primVariant.variantName:
                # clear selections will have no child variants
                return []
            parentVariants = parent.parentVariants + [parent.primVariant]
        else:
            # root's children (prims) must be populated manually
            return []

        # set variants temporarily so that underlying variants can be inspected.
        with varlib.SessionVariantContext(prim, parentVariants):
            for path, primVariant in varlib.getPrimVariants(prim,
                                                            includePath=True):
                if primVariant in parentVariants:
                    continue
                variantSet = prim.GetVariantSet(primVariant.setName)
                variantItem = VariantItem(variantSet,
                                          path,
                                          parentVariants,
                                          primVariant)
                variantItems = [variantItem]
                # add non-selected items
                names = variantSet.GetVariantNames()
                names.remove(primVariant.variantName)
                names.append('')

                parentPath = path.GetParentPath()
                for altVariant in names:
                    altPath = parentPath.AppendVariantSelection(
                        primVariant.setName,
                        altVariant)
                    altVariant = varlib.PrimVariant(primVariant.setName,
                                                    altVariant)
                    altVariantItem = VariantItem(variantSet,
                                                 altPath,
                                                 parentVariants,
                                                 altVariant)
                    variantItems.append(altVariantItem)
                # break loop because next iteration is the children's children
                return variantItems
        return []


class VariantModel(AbstractTreeModelMixin, QtCore.QAbstractItemModel):
    '''Holds a hierarchy of variant sets and their selections
    '''
    def __init__(self, stage, prims, parent=None):
        '''
        Parameters
        ----------
        prims : List[Usd.Prim]
        parent : Optional[QtGui.QWidget]
        '''
        self._stage = stage
        self._prims = prims
        super(VariantModel, self).__init__(itemTree=LazyVariantTree(),
                                           parent=parent)
        self.Reset()

    def columnCount(self, parentIndex):
        return 3

    def flags(self, modelIndex):
        if modelIndex.isValid():
            item = modelIndex.internalPointer()
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        return QtCore.Qt.NoItemFlags

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
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
            if isinstance(item, PrimItem):
                if column == 0:
                    return str(item.path)
                return ''
            if column == 0:
                return '{}={}'.format(*item.primVariant)
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

    def _PopulateVariants(self, prims):
        '''
        Parameters
        ----------
        prims : List[Usd.Prim]
        '''
        if not prims:
            return

        for prim in prims:
            primItem = PrimItem(prim)
            self.itemTree.addItems(primItem, parent=None)
        self.dataChanged.emit(NULL_INDEX, NULL_INDEX)

    def Reset(self):
        self.beginResetModel()
        self.itemTree = LazyVariantTree()
        # only single selection is supported
        if len(self._prims) == 1:
            self._PopulateVariants(self._prims)
        self.endResetModel()

    def PrimSelectionChanged(self, selected, deselected):
        prims = set(self._prims)
        prims.difference_update(deselected)
        prims.update(selected)
        self._prims = list(prims)
        self.Reset()

    def EditTargetChanged(self, layer):
        self.dataChanged.emit(NULL_INDEX, NULL_INDEX)


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
        self.setWindowTitle('Variant Editor')

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.view = QtWidgets.QTreeView(parent=self)
        self.view.setModel(self.dataModel)
        layout.addWidget(self.view)
        self.view.setColumnWidth(0, 400)
        self.view.setColumnWidth(1, 100)
        self.view.setColumnWidth(2, 100)
        self.view.setExpandsOnDoubleClick(False)
        self.view.doubleClicked.connect(self.SelectVariant)
        # self.view.expandAll()

        self.resize(700, 500)

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
        # with varlib.VariantContext(item.prim,
        #                            item.parentVariants,
        #                            setAsDefaults=False):
        item.variantSet.SetVariantSelection(item.primVariant.variantName)

        self.dataModel.dataChanged.emit(NULL_INDEX, NULL_INDEX)
