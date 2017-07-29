from __future__ import absolute_import

from pxr import Sdf, Usd
from Qt import QtCore, QtGui, QtWidgets
from usdQt.outliner import (OutlinerTreeView, OutlinerViewDelegate,
                            OutlinerStageModel, ContextMenuBuilder)
from usdQt.layers import LayerTextViewDialog, SubLayerDialog

from typing import (Any, Dict, Iterable, Iterator, List, Optional,
                    Tuple, TypeVar, Union)


class UsdOutliner(QtWidgets.QDialog):
    # emitted with the new edit layer when the edit target is changed
    editTargetChanged = QtCore.Signal(Sdf.Layer)

    def __init__(self, stage, menuBuilder=None, parent=None):
        '''
        Parameters
        ----------
        stage : Usd.Stage
        menuBuilder : Optional[Type[ContextMenuBuilder]]
        parent : Optional[QtGui.QWidget]
        '''
        assert isinstance(stage, Usd.Stage), 'A Stage instance is required'
        super(UsdOutliner, self).__init__(parent=parent)

        self.stage = stage
        self.dataModel = self._GetModel()

        # instances of child dialogs
        self.layerTextDialogs = {}
        self.editTargetDlg = None

        # Widget and other Qt setup
        self.setModal(False)
        self.UpdateTitle()

        self._menuBar = QtWidgets.QMenuBar(self)
        self._menus = {}  # type: Dict[str, QtWidgets.QMenu]
        self.AddMenu('file', '&File')
        self.AddMenu('tools', '&Tools')
        self.PopulateMenus()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self._menuBar)
        view = self._GetView(self.dataModel, menuBuilder)
        delegate = OutlinerViewDelegate(self.stage.GetEditTarget().GetLayer(),
                                        parent=self)
        self.editTargetChanged.connect(delegate.SetActiveLayer)
        self.editTargetChanged.connect(self.dataModel.ActiveLayerChanged)
        view.setItemDelegate(delegate)
        layout.addWidget(view)

        view.setColumnWidth(0, 360)
        self.view = view

        self.resize(900, 600)

    @property
    def editTarget(self):
        return self.stage.GetEditTarget().GetLayer()

    def _GetModel(self):
        '''
        Get the model for the outliner

        Returns
        -------
        QtCore.QAbstractItemModel
        '''
        return OutlinerStageModel(self.stage, parent=self)

    def _GetView(self, model, menuBuilder):
        '''
        Get the view for the outliner

        Parameters
        ----------
        model : QtCore.QAbstractItemModel
        menuBuilder : Optional[Type[ContextMenuBuilder]]

        Returns
        -------
        QtWidgets.QTreeView
        '''
        return OutlinerTreeView(model, menuBuilder=menuBuilder, parent=self)

    def UpdateTitle(self, identifier=None):
        '''
        Parameters
        ----------
        identifier : Optional[str]
            If not provided, acquired from the curent edit target
        '''
        if not identifier:
            identifier = self.editTarget.identifier
        self.setWindowTitle('Outliner - %s' % identifier)

    def UpdateEditTarget(self, layer):
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        '''
        currentLayer = self.stage.GetEditTarget().GetLayer()
        if layer == currentLayer or not layer.permissionToEdit:
            return

        if currentLayer.dirty:
            box = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                "Unsaved Changes",
                "You have unsaved layer edits which you cant access from "
                "another layer. Continue?",
                buttons=(QtWidgets.QMessageBox.Cancel |
                         QtWidgets.QMessageBox.Yes))
            if box.exec_() != QtWidgets.QMessageBox.Yes:
                return
            # FIXME: Should we blow away changes or allow them to
            # persist on the old edit target?

        self.stage.SetEditTarget(layer)
        self.editTargetChanged.emit(layer)
        self.UpdateTitle()

    def AddMenu(self, name, label=None):
        '''
        Parameters
        ----------
        name : str
            name of registered menu
        label : Optional[str]
            label to display in the menu bar

        Returns
        -------
        QtWidgets.QMenu
        '''
        if label is None:
            label = name
        menu = self._menuBar.addMenu(label)
        self._menus[name] = menu
        return menu

    def GetMenu(self, name):
        '''
        Get a named menu from the application's registered menus

        Parameters
        ----------
        name : str
            name of registered menu

        Returns
        -------
        Optional[QtWidgets.QMenu]
        '''
        return self._menus.get(name.lower())

    def _ShowEditTargetLayerText(self, layer=None):
        # only allow one window per layer
        # may need to hook this bookkeeping up to hideEvent
        self.layerTextDialogs = \
            dict(((layer, dlg)
                  for layer, dlg in self.layerTextDialogs.iteritems()
                  if dlg.isVisible()))
        if layer is None:
            layer = self.stage.GetEditTarget().GetLayer()
        try:
            dlg = self.layerTextDialogs[layer]
        except KeyError:
            dlg = LayerTextViewDialog(layer, parent=self)
            dlg.layerEdited.connect(self.dataModel.ResetStage)
            self.layerTextDialogs[layer] = dlg
        dlg.Refresh()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _ChangeEditTarget(self):
        # only allow one window
        if not self.editTargetDlg:
            dlg = SubLayerDialog(self.stage, parent=self)
            dlg.view.editTargetChanged.connect(self.UpdateEditTarget)
            dlg.view.showLayerContents.connect(self._ShowEditTargetLayerText)
            dlg.view.openLayer.connect(self._OpenLayerInOutliner)
            self.editTargetDlg = dlg
        self.editTargetDlg.show()
        self.editTargetDlg.raise_()
        self.editTargetDlg.activateWindow()

    def PopulateMenus(self):
        toolsMenu = self.GetMenu('tools')
        a = toolsMenu.addAction('Show Current Layer Text')
        a.triggered.connect(self._ShowEditTargetLayerText)
        a = toolsMenu.addAction('Change Edit Target')
        a.triggered.connect(self._ChangeEditTarget)

    @classmethod
    def FromUsdFile(cls, usdFile, parent=None):
        with Usd.StageCacheContext(Usd.BlockStageCaches):
            stage = Usd.Stage.Open(usdFile, Usd.Stage.LoadNone)
            assert stage
            stage.SetEditTarget(stage.GetSessionLayer())
        return cls(stage, parent=parent)

    def _OpenLayerInOutliner(self, layer):
        dlg = self.FromUsdFile(layer.identifier)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        dlg.exec_()


if __name__ == '__main__':
    # simple test
    import sys

    app = QtWidgets.QApplication(sys.argv)

    usdFileArg = sys.argv[1]

    dialog = UsdOutliner.FromUsdFile(usdFileArg)
    dialog.show()
    dialog.exec_()
