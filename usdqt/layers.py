from __future__ import absolute_import

from pxr import Sdf, Usd, Tf
from Qt import QtCore, QtGui, QtWidgets
from treemodel.itemtree import TreeItem, ItemTree
from treemodel.qt.base import AbstractTreeModelMixin
from usdqt.common import NULL_INDEX

from typing import (Any, Dict, Iterable, Iterator, List, Optional,
                    Tuple, TypeVar, Union)


class LayerTextViewDialog(QtWidgets.QDialog):
    # emitted when a layer changes
    layerEdited = QtCore.Signal(Sdf.Layer)

    def __init__(self, layer, parent=None):
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        parent : Optional[QtGui.QWidget]
        '''
        super(LayerTextViewDialog, self).__init__(parent=parent)
        self.layer = layer
        self.setWindowTitle('Layer: %s' % layer.identifier)

        layout = QtWidgets.QVBoxLayout(self)
        self.textArea = QtWidgets.QPlainTextEdit(self)
        self.editableCheckBox = QtWidgets.QCheckBox('Unlock for Editing')
        self.editableCheckBox.stateChanged.connect(self.SetEditable)
        layout.addWidget(self.editableCheckBox)
        layout.addWidget(self.textArea)

        buttonLayout = QtWidgets.QHBoxLayout()
        refreshButton = QtWidgets.QPushButton('Reload', parent=self)
        refreshButton.clicked.connect(self.Refresh)
        buttonLayout.addWidget(refreshButton)
        self.saveButton = QtWidgets.QPushButton('Apply', parent=self)
        self.saveButton.clicked.connect(self.Save)
        buttonLayout.addWidget(self.saveButton)
        layout.addLayout(buttonLayout)

        self.editableCheckBox.setChecked(False)
        self.SetEditable(False)
        self.resize(800, 600)

    def SetEditable(self, checkState):
        if checkState == QtCore.Qt.Checked:
            self.textArea.setUndoRedoEnabled(True)
            self.textArea.setReadOnly(False)
            self.saveButton.setEnabled(True)
        else:
            self.textArea.setUndoRedoEnabled(False)
            self.textArea.setReadOnly(True)
            self.saveButton.setEnabled(False)

    def Refresh(self):
        self.textArea.setPlainText(self.layer.ExportToString())

    def Save(self):
        try:
            self.layer.ImportFromString(self.textArea.toPlainText())
        except Tf.ErrorException as err:
            box = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                "Syntax Error",
                "Problem parsing your changes:\n\n{0}".format(err.message))
            box.exec_()
        else:
            self.layerEdited.emit(self.layer)
            # refresh so that formatting will get standardized
            self.Refresh()


class LayerItem(TreeItem):

    def __init__(self, layer):
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        '''
        super(LayerItem, self).__init__(key=layer.identifier)
        self.layer = layer


class SubLayerModel(AbstractTreeModelMixin, QtCore.QAbstractItemModel):
    '''Holds a hierarchy of usd layers and their sublayers
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
        super(SubLayerModel, self).__init__(parent=parent)
        sessionLayer = self._stage.GetSessionLayer()
        if sessionLayer:
            self.populateUnder(sessionLayer)

        self.populateUnder(stage.GetRootLayer())

    # Qt methods ---------------------------------------------------------------
    def columnCount(self, parentIndex):
        return 3

    def flags(self, modelIndex):
        if modelIndex.isValid():
            item = modelIndex.internalPointer()
            if item.layer.permissionToEdit:
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        return QtCore.Qt.NoItemFlags

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if section == 0:
                return 'Name'
            elif section == 1:
                return 'Path'
            elif section == 2:
                return 'Resolved Path'

    def data(self, modelIndex, role=QtCore.Qt.DisplayRole):
        if not modelIndex.isValid():
            return
        if role == QtCore.Qt.DisplayRole:
            column = modelIndex.column()
            item = modelIndex.internalPointer()
            if column == 0:
                if item.layer.anonymous:
                    return 'anonymous.usd'
                return item.layer.identifier.split('/')[-1]
            elif column == 1:
                return item.layer.identifier
            elif column == 2:
                return item.layer.realPath
        elif role == QtCore.Qt.FontRole:
            item = modelIndex.internalPointer()
            if item.layer == self._stage.GetEditTarget().GetLayer():
                font = QtGui.QFont()
                font.setBold(True)
                return font

    # Custom Methods -----------------------------------------------------------
    def populateUnder(self, layer, parent=None):
        '''
        Parameters
        ----------
        layer : SdfLayer
        parent : Optional[LayerItem]
        '''
        layerItem = LayerItem(layer)
        self.itemTree.addItems(layerItem, parent=parent)

        for subLayerPath in layer.subLayerPaths:
            subLayer = Sdf.Layer.FindOrOpen(subLayerPath)
            self.populateUnder(subLayer, parent=layerItem)


class SubLayerDialog(QtWidgets.QDialog):
    # emitted with the new edit layer when the edit target is changed
    editTargetChanged = QtCore.Signal(Sdf.Layer)

    def __init__(self, stage, parent=None):
        '''
        Parameters
        ----------
        stage : Usd.Stage
        parent : Optional[QtGui.QWidget]
        '''
        super(SubLayerDialog, self).__init__(parent=parent)
        self.stage = stage
        self.dataModel = SubLayerModel(stage, parent=self)

        # Widget and other Qt setup
        self.setModal(False)
        self.setWindowTitle('Select Edit Target')

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.view = QtWidgets.QTreeView(parent=self)
        self.view.setModel(self.dataModel)
        layout.addWidget(self.view)
        self.view.setColumnWidth(0, 160)
        self.view.setColumnWidth(1, 300)
        self.view.setColumnWidth(2, 100)
        self.view.setExpandsOnDoubleClick(False)
        self.view.doubleClicked.connect(self.SelectLayer)
        self.view.expandAll()

        self.resize(700, 200)

    def SelectLayer(self, selectedIndex=None):
        '''
        Parameters
        ----------
        selectedIndex : Optional[QtCore.QModelIndex]
        '''
        if not selectedIndex:
            selectedIndexes = self.view.selectedIndexes()
            if not selectedIndexes:
                return
            selectedIndex = selectedIndexes[0]

        selectedLayer = selectedIndex.internalPointer().layer
        currentLayer = self.stage.GetEditTarget().GetLayer()
        if selectedLayer == currentLayer or not selectedLayer.permissionToEdit:
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
        self.editTargetChanged.emit(selectedLayer)
        # Explicitly get two arg version of signal for Qt4/Qt5
        self.dataModel.dataChanged[QtCore.QModelIndex, QtCore.QModelIndex].emit(
            NULL_INDEX, NULL_INDEX)
