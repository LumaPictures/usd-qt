import pymel.core as pm
from pxr import Sdf

from treemodel.itemtree import ItemLookupError
import usdQt.app

from Qt import QtCore


class ProxyShapeOutliner(usdQt.app.UsdOutliner):
    '''Generic outliner attached to a single AL maya ProxyShape node'''
    OUTLINER_WINDOW_NAME = 'MayaUsdOutlinerWin'

    def __init__(self, stage, proxyShape, role=None, parent=None):
        super(ProxyShapeOutliner, self).__init__(
            stage,
            role=role,
            parent=parent)
        self.setObjectName(self.OUTLINER_WINDOW_NAME)
        self._proxyShape = proxyShape

        self.view.setIndentation(10)
        self.view.primSelectionChanged.connect(self.pushPrimToMaya)
        self.view.model().primChanged.connect(self.primChanged)

        self._blockSelectionCallback = False
        self.selectionCallbackId = None
        self._refreshScheduled = False

    def pushPrimToMaya(self, selectedPrims, deselectedPrims):
        '''
        Create transforms in maya for the selected prims and deselect 
        transforms (which deletes them if they are not needed) for deselected 
        prims in the outliner.
        '''
        if self._blockSelectionCallback:
            return
        self._blockSelectionCallback = True

        def getDagPath(prim):
            # AL_usdmaya stores a mapping from prim to dag path in session layer
            dagPath = prim.GetCustomDataByKey("MayaPath")
            if dagPath and pm.objExists(dagPath):
                return dagPath

        toSelect = []
        toDeselect = []
        toSelectPrimPaths = []
        toDeselectPrimPaths = []
        for prim in selectedPrims:
            toSelectPrimPaths.append(str(prim.GetPath()))
            dag = getDagPath(prim)
            if dag:
                toSelect.append(dag)

        if toSelectPrimPaths:
            # print 'pm.AL_usdmaya_ProxyShapeSelect(%s, primPath=%s, ' \
            #       'append=True)' % (self._proxyShape, toSelectPrimPaths)
            pm.AL_usdmaya_ProxyShapeSelect(
                self._proxyShape,
                primPath=toSelectPrimPaths,
                append=True
            )

        for prim in deselectedPrims:
            toDeselectPrimPaths.append(str(prim.GetPath()))
            dag = getDagPath(prim)
            if dag:
                toDeselect.append(dag)

        if toDeselectPrimPaths:
            # print 'pm.AL_usdmaya_ProxyShapeSelect(%s, primPath=%s, ' \
            #       'deselect=True)' % (self._proxyShape, toDeselectPrimPaths)
            pm.AL_usdmaya_ProxyShapeSelect(
                self._proxyShape,
                primPath=str(prim.GetPath()),
                deselect=True
            )

        self._blockSelectionCallback = False

    def mayaSelectionChanged(self, *args):
        '''Callback to mirror maya selection changes in the Outliner'''
        if self._blockSelectionCallback:
            return
        self._blockSelectionCallback = True

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
        self._blockSelectionCallback = False

    def primChanged(self, prim):
        '''Slot that receives a signal that a refresh is required to update'''
        if self._refreshScheduled:
            return

        def refreshViewport():
            self._refreshScheduled = False
            pm.refresh()

        pm.evalDeferred(refreshViewport)

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
        super(ProxyShapeOutliner, self).hideEvent(event)
