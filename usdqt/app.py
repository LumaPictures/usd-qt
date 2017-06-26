from __future__ import absolute_import

from pxr import Sdf, Usd
from Qt import QtCore, QtGui, QtWidgets
from usdqt.outliner import (OutlinerTreeView, OutlinerViewDelegate,
                            OutlinerStageModel)
from usdqt.layers import LayerTextViewDialog, SubLayerDialog


class UsdOutliner(QtWidgets.QDialog):
    # emitted with the new edit layer when the edit target is changed
    editTargetChanged = QtCore.Signal(Sdf.Layer)

    def __init__(self, stage, parent=None):
        assert isinstance(stage, Usd.Stage), 'A Stage instance is required'
        super(UsdOutliner, self).__init__(parent=parent)

        self.stage = stage
        self.dataModel = OutlinerStageModel(self.stage, parent=self)

        # Widget and other Qt setup
        self.setModal(False)
        self.updateTitle()

        self._menuBar = QtWidgets.QMenuBar(self)
        self.menus = {
            'file': self._menuBar.addMenu('&File'),
            'tools': self._menuBar.addMenu('&Tools')
        }
        self.populateMenus()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self._menuBar)
        view = OutlinerTreeView(self.dataModel, parent=self)
        delegate = OutlinerViewDelegate(self.stage.GetEditTarget().GetLayer(),
                                        parent=self)
        self.editTargetChanged.connect(delegate.setActiveLayer)
        self.editTargetChanged.connect(self.dataModel.activeLayerChanged)
        view.setItemDelegate(delegate)
        layout.addWidget(view)

        view.setColumnWidth(0, 360)
        self.view = view

        self.resize(900, 600)

    @property
    def editTarget(self):
        return self.stage.GetEditTarget().GetLayer()

    def updateTitle(self, identifier=None):
        if not identifier:
            identifier = self.editTarget.identifier
        self.setWindowTitle('Outliner - %s' % identifier)

    def updateEditTarget(self, layer):
        self.stage.SetEditTarget(layer)
        self.editTargetChanged.emit(layer)
        self.updateTitle()

    def getMenu(self, name):
        return self.menus.get(name.lower())

    def populateMenus(self):
        toolsMenu = self.getMenu('tools')

        def showEditTargetLayerText():
            # FIXME: only allow one window. per layer could be nice here?
            d = LayerTextViewDialog(self.stage.GetEditTarget().GetLayer(),
                                    parent=self)
            d.layerEdited.connect(self.dataModel.resetStage)
            d.refresh()
            d.show()

        def changeEditTarget():
            # FIXME: only allow one window
            d = SubLayerDialog(self.stage, parent=self)
            d.editTargetChanged.connect(self.updateEditTarget)
            d.show()

        a = toolsMenu.addAction('Show Current Layer Text')
        a.triggered.connect(showEditTargetLayerText)
        a = toolsMenu.addAction('Change Edit Target')
        a.triggered.connect(changeEditTarget)

    @classmethod
    def fromUsdFile(cls, usdFile, parent=None):
        with Usd.StageCacheContext(Usd.BlockStageCaches):
            stage = Usd.Stage.Open(usdFile, Usd.Stage.LoadNone)
            assert stage
            stage.SetEditTarget(stage.GetSessionLayer())
        return cls(stage, parent=parent)


if __name__ == '__main__':
    # simple test
    import sys

    app = QtWidgets.QApplication(sys.argv)

    usdFileArg = sys.argv[1]

    dialog = UsdOutliner.fromUsdFile(usdFileArg)
    dialog.show()
    dialog.exec_()
