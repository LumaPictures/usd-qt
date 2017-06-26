import pymel.core as pm
from pxr import Sdf

from treemodel.itemtree import ItemLookupError
import usdqt.app

from luma_qt.Qt import QtCore


class ProxyShapeOutliner(usdqt.app.UsdOutliner):
    '''Generic outliner attached to a single AL maya ProxyShape node'''
    OUTLINER_WINDOW_NAME = 'MayaUsdOutlinerWin'

    def __init__(self, stage, proxyShape, parent=None):
        super(ProxyShapeOutliner, self).__init__(stage, parent=parent)
        self.setObjectName(self.OUTLINER_WINDOW_NAME)
        self._proxyShape = proxyShape

        self.view.setIndentation(10)
        self.view.primSelectionChanged.connect(self.pushPrimToMaya)

        self._blockSelectionCallback = False

    def pushPrimToMaya(self, selectedPrims, deselectedPrims):
        '''
        Create transforms in maya for the selected prims and deselect 
        transforms (which deletes them if they are not needed) for deselected 
        prims in the outliner.
        '''
        self._blockSelectionCallback = True
        for prim in selectedPrims:
            # this command also selects the transform it creates
            pm.AL_usdmaya_ProxyShapeSelectPrimPath(
                self._proxyShape,
                primPath=prim.GetPath())

        toDeselect = []
        for prim in deselectedPrims:
            # AL_usdmaya stores a mapping from prim to dag path in session layer
            dagPath = prim.GetCustomDataByKey("MayaPath")
            if dagPath and pm.objExists(dagPath):
                toDeselect.append(dagPath)

        if toDeselect:
            pm.select(toDeselect, deselect=True)
        self._blockSelectionCallback = False

    def mayaSelectionChanged(self, *args):
        '''Callback to mirror maya selection changes in the Outliner'''
        if self._blockSelectionCallback:
            return

        parentPath = self._proxyShape.getParent().fullPath()
        selected = pm.ls(type=pm.nt.AL_usdmaya_Transform, selection=1)
        qSelection = QtCore.QItemSelection()
        for dagNode in selected:
            dagPath = dagNode.fullPath()
            assert parentPath in dagPath, '%s not in %s' % (parentPath, dagPath)
            primPath = dagPath[len(parentPath):].replace('|', '/')

            try:
                itemIndex = self.getIndexForPrimPath(primPath)
            except ItemLookupError:
                # create missing prim items as needed before selecting
                self.createParents(primPath)
                itemIndex = self.getIndexForPrimPath(primPath)
            qSelection.select(itemIndex, itemIndex)
        selModel = self.view.selectionModel()
        selModel.select(qSelection,
                        QtCore.QItemSelectionModel.SelectCurrent |
                        QtCore.QItemSelectionModel.Clear |
                        QtCore.QItemSelectionModel.Rows)

        indexes = qSelection.indexes()
        if indexes:
            self.view.scrollTo(indexes[0], self.view.PositionAtTop)

    def createParents(self, path):
        '''Create any missing prim parents down to path'''
        sdfPath = Sdf.Path(path)
        lastPrim = self.stage.GetPseudoRoot()
        itemTree = self.dataModel.itemTree
        for prefix in sdfPath.GetPrefixes():
            try:
                item = itemTree.itemByKey(prefix)
            except ItemLookupError:
                # populate parent's children so that item exists
                lastPrimItem = itemTree.itemByKey(str(lastPrim.GetPath()))
                itemTree._getItemChildren(lastPrimItem)
                item = itemTree.itemByKey(str(prefix))
            lastPrim = item.prim

    def getIndexForPrimPath(self, path):
        '''Return the row indexes for a certain prim path'''
        item = self.dataModel.itemTree.itemByKey(path)
        leftIndex = self.dataModel.getItemIndex(item, 0)
        return leftIndex

    def showEvent(self, event):
        '''Add callbacks to keep ui in sync while visible'''
        self.selectionCallbackId = \
            pm.api.MEventMessage.addEventCallback('SelectionChanged',
                                                  self.mayaSelectionChanged)
        # make sure selection starts in correct state
        self.mayaSelectionChanged()
        super(ProxyShapeOutliner, self).showEvent(event)

    def hideEvent(self, event):
        '''Remove callbacks on ui hide'''
        if self.selectionCallbackId:
            pm.api.MMessage.removeCallback(self.selectionCallbackId)
            self.selectionCallbackId = None
        # not using super to make this call reload proof for now
        usdqt.app.UsdOutliner.hideEvent(self, event)