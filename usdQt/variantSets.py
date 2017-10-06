'''
Variant Set and Variant Editing Widget.

TODO:
- support more than one variant set at each level of the hierarchy (This is 
  supported in usd) i.e. two variants that are not mutually exclusive, but can 
  be selected at the same time because they are in different sets.
- Expand selected variants initially
- Possible: Only fetch variant children when requested by expansion for 
  performance. Unfortunately this may mean we loose ui friendliness of the 
  "expandable" indicator 
- Ability to Remove Variants?
- Allow setting variant selections within nested variants?
'''

from __future__ import absolute_import

from pxr import Sdf, Usd, Tf
from Qt import QtCore, QtGui, QtWidgets
from treemodel.itemtree import TreeItem, LazyItemTree
from treemodel.qt.base import AbstractTreeModelMixin
from usdQt.common import NULL_INDEX, ContextMenuBuilder, ContextMenuMixin,\
    passSingleSelection, passMultipleSelection, UsdQtUtilities
import usdlib.variants as varlib


class VariantItem(TreeItem):

    def __init__(self, prim, variantSet, path):
        '''
        Parameters
        ----------
        variantSet : Usd.VariantSet
        path : Sdf.Path
        '''
        self.prim = prim
        self.path = path
        self.variantSet = variantSet
        print self.path, varlib.variantSetKey(path)
        self.variant = varlib.PrimVariant(*path.GetVariantSelection())
        super(VariantItem, self).__init__(key=(varlib.variantSetKey(path),
                                               self.variant.variantName))
        self.parentVariants = []
        parentPath = path.GetParentPath()
        while parentPath.ContainsPrimVariantSelection():
            parentVariant = PrimVariant(*parentPath.GetVariantSelection())
            self.parentVariants.insert(0, parentVariant)
            parentPath = parentPath.GetParentPath()

    @property
    def selected(self):
        '''
        Returns
        -------
        bool
        '''
        return self.variantSet.GetVariantSelection() == \
           self.variant.variantName

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


# TODO:
def getPrimVariantTree(tree, prim):
    for path, variant in getPrimVariantsWithPaths(prim):
        # all nodes returned will have at least one variant selection
        parentPath = path.GetParentPath()
        parent = None
        if parentPath.ContainsPrimVariantSelection():
            parent = tree.itemByKey(str(parentPath))
        tree.addItems(VariantItem(path), parent=parent)

    import pprint

    pprint.pprint(tree._parentToChildren)
    return tree


# FIXME:
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
        print parentVariants
        # set variants temporarily so that underlying variants can be inspected.
        with varlib.SessionVariantContext(self.prim, parentVariants):
            for path, primVariant in varlib.getPrimVariantsWithPaths(self.prim):
                if primVariant in parentVariants:
                    continue
                variantSet = self.prim.GetVariantSet(primVariant.setName)

                variantItems = []
                names = variantSet.GetVariantNames()
                names.append('')

                parentPath = path.GetParentPath()
                for variantName in names:
                    variantPath = parentPath.AppendVariantSelection(
                        primVariant.setName,
                        variantName)
                    altVariantItem = VariantItem(self.prim,
                                                 variantSet,
                                                 variantPath)
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
    showMenuOnNoSelection = True
    referenceAdded = QtCore.Signal()

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
        def summary(strings):
            return '/'.join(set(strings))

        if selections:
            model = self.view.model()
            setsStr = summary((s.variant.setName for s in selections))
            variantsStr = summary((s.name for s in selections))
            hasVariantSelection = all(s.variant.variantName for s in selections)
            a = menu.addAction('Add "%s" Variant' % setsStr)
            a.triggered.connect(self.AddVariant)

            # for now only allow one nested variant set per variant
            allowAdding = not any(model.itemTree.childCount(parent=s)
                                  for s in selections)
            a = menu.addAction('Add Nested Variant Set Under "%s"'
                               % variantsStr)
            a.triggered.connect(self.AddNestedVariantSet)
            a.setEnabled(hasVariantSelection and allowAdding)
            a = menu.addAction('Add Reference Under "%s"' % variantsStr)
            a.triggered.connect(self.AddReference)
            a.setEnabled(hasVariantSelection)
        if len(selections) == 0:
            a = menu.addAction('Add Top Level Variant Set')
            a.triggered.connect(self.AddVariantSet)

            # TODO: may not be api for these actions, you can always remove the
            # prim spec and rebuild.
            # if isinstance(selection, VariantItem):
            #     layer = self.view.model().Layer()
            #     if layer.GetPrimAtPath(selection.path):
            #         a = menu.addAction('Remove Variant')
            #         a.triggered.connect(self.RemoveVariant)
            #         a = menu.addAction('Remove Variant Set')
            #         a.triggered.connect(self.RemoveVariantSet)
        return menu

    @passMultipleSelection
    def AddVariant(self, selectedItems):
        name, _ = QtWidgets.QInputDialog.getText(
            self.view,
            'Enter New Variant Name',
            'Name for the new variant \n%s=:'
            % '/'.join((i.variant.setName for i in selectedItems)))
        if not name:
            return
        for selectedItem in selectedItems:
            # want to add new variant inside of parents variant context.
            with varlib.VariantContext(selectedItem.prim,
                                       selectedItem.parentVariants,
                                       setAsDefaults=True):
                selectedItem.variantSet.AddVariant(name)
        self.view.model().Reset()  # TODO: Reload only necessary part

    def _GetVariantSetName(self):
        name, _ = QtWidgets.QInputDialog.getText(
            self.view,
            'Enter New Variant Set Name',
            'Name for the new variant set:')
        return name

    @passMultipleSelection
    def AddNestedVariantSet(self, selectedItems):
        name = self._GetVariantSetName()
        if not name:
            return

        for selectedItem in selectedItems:
            # want to add new variant set inside of parents variant context.
            with varlib.VariantContext(selectedItem.prim,
                                       selectedItem.variants,
                                       setAsDefaults=False):
                selectedItem.prim.GetVariantSets().AddVariantSet(name)
        self.view.model().Reset()  # TODO: Reload only necessary part

    def AddVariantSet(self):
        name = self._GetVariantSetName()
        if not name:
            return
        self.view.model().prim.GetVariantSets().AddVariantSet(name)
        self.view.model().Reset()  # TODO: Reload only necessary part

    @passSingleSelection
    def RemoveVariant(self, selectedItem):
        pass

    @passSingleSelection
    def RemoveVariantSet(self, item):
        model = self.view.model()
        spec = model.Layer().GetPrimAtPath(item.path)
        if spec:
            # FIXME:
            spec.variantSetNameList.Remove(item.variant.setName)

    @passSingleSelection
    def AddReference(self, item):
        path = UsdQtUtilities.exec_('getReferencePath',
                                    self.view,
                                    stage=item.prim.GetStage())
        if not path:
            return
        with varlib.VariantContext(item.prim,
                                   item.variants,
                                   setAsDefaults=False):
            item.prim.GetReferences().SetReferences([Sdf.Reference(path)])


class VariantTreeView(ContextMenuMixin, QtWidgets.QTreeView):

    def __init__(self, parent=None, contextMenuBuilder=None):
        if contextMenuBuilder is None:
            contextMenuBuilder = VariantContextMenuBuilder
        super(VariantTreeView, self).__init__(
            parent=parent,
            contextMenuBuilder=contextMenuBuilder)
        self.setSelectionMode(self.ExtendedSelection)


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
