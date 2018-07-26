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

from functools import partial

from ._Qt import QtCore, QtGui, QtWidgets
from pxr import Sdf, Usd, Tf
from typing import NamedTuple, Optional

from treemodel.itemtree import TreeItem
from treemodel.qt.base import AbstractTreeModelMixin
from .common import CopyToClipboard, MenuAction, ContextMenuMixin

if False:
    from typing import *


NULL_INDEX = QtCore.QModelIndex()


class LayerTextEditor(QtWidgets.QWidget):
    # Emitted when the layer is saved by this dialog.
    layerSaved = QtCore.Signal(Sdf.Layer)

    def __init__(self, layer, readOnly=False, parent=None):
        # type: (Sdf.Layer, bool, Optional[QtGui.QWidget]) -> None
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        readOnly : bool
        parent : Optional[QtGui.QWidget]
        '''
        super(LayerTextEditor, self).__init__(parent=parent)

        self._layer = layer
        self.readOnly = readOnly

        self.textArea = QtWidgets.QPlainTextEdit(self)
        refreshButton = QtWidgets.QPushButton('Reload', parent=self)
        refreshButton.clicked.connect(self.Refresh)

        layout = QtWidgets.QVBoxLayout(self)
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(refreshButton)

        if not readOnly:
            editableCheck = QtWidgets.QCheckBox('Unlock for Editing',
                                                parent=self)
            editableCheck.setChecked(False)
            editableCheck.stateChanged.connect(self.SetEditable)
            layout.addWidget(editableCheck)
            self.saveButton = QtWidgets.QPushButton('Apply', parent=self)
            self.saveButton.clicked.connect(self.Save)
            buttonLayout.addWidget(self.saveButton)

        layout.addWidget(self.textArea)
        layout.addLayout(buttonLayout)

        self.setWindowTitle('Layer: %s' % layer.identifier)
        self.SetEditable(False)
        self.Refresh()
        self.resize(800, 600)

    def SetEditable(self, editable):
        if editable:
            if self.readOnly:
                return
            self.textArea.setUndoRedoEnabled(True)
            self.textArea.setReadOnly(False)
            self.saveButton.setEnabled(True)
        else:
            self.textArea.setUndoRedoEnabled(False)
            self.textArea.setReadOnly(True)
            if not self.readOnly:
                self.saveButton.setEnabled(False)

    def Refresh(self):
        self.textArea.setPlainText(self._layer.ExportToString())

    def Save(self):
        if self.readOnly:
            raise RuntimeError('Cannot save layer when readOnly is set')
        try:
            success = self._layer.ImportFromString(self.textArea.toPlainText())
        except Tf.ErrorException as e:
            QtWidgets.QMessageBox.warning(self, 'Layer Syntax Error',
                                          'Failed to apply modified layer '
                                          'contents:\n\n{0}'.format(e.message))
        else:
            if success:
                self.layerSaved.emit(self._layer)
                self.Refresh()  # To standardize formatting


class LayerTextEditorDialog(QtWidgets.QDialog, LayerTextEditor):
    # Used for keeping shared instances alive.
    _sharedInstances = {}

    @classmethod
    def _OnSharedInstanceFinished(cls, layer):
        dialog = cls._sharedInstances.pop(layer, None)
        if dialog:
            dialog.deleteLater()

    @classmethod
    def GetSharedInstance(cls, layer, readOnly=False, parent=None):
        dialog = cls._sharedInstances.get(layer)
        if dialog is None:
            dialog = cls(layer, readOnly=readOnly, parent=parent)
            cls._sharedInstances[layer] = dialog
        dialog.finished.connect(partial(cls._OnSharedInstanceFinished, layer))
        return dialog


class LayerItem(TreeItem):
    __slots__ = ('layer',)

    def __init__(self, layer):
        # type: (Sdf.Layer) -> None
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
        # type: (Usd.Stage, Optional[QtGui.QWidget]) -> None
        '''
        Parameters
        ----------
        stage : Usd.Stage
        parent : Optional[QtGui.QWidget]
        '''
        assert isinstance(stage, Usd.Stage)
        super(SubLayerModel, self).__init__(parent=parent)

        self._stage = stage
        sessionLayer = stage.GetSessionLayer()
        if sessionLayer:
            self.PopulateUnder(sessionLayer)
        self.PopulateUnder(stage.GetRootLayer())
        self._listener = Tf.Notice.Register(Usd.Notice.StageEditTargetChanged,
                                            self._OnEditTargetChanged, stage)

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
    def _OnEditTargetChanged(self, notice, stage):
        self.dataChanged[QtCore.QModelIndex, QtCore.QModelIndex].emit(
            NULL_INDEX, NULL_INDEX)

    def PopulateUnder(self, layer, parent=None):
        # type: (Sdf.Layer, Optional[LayerItem]) -> Any
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        parent : Optional[LayerItem]
        '''
        layerItem = LayerItem(layer)
        self.itemTree.addItems(layerItem, parent=parent)

        for subLayerPath in layer.subLayerPaths:
            subLayer = Sdf.Layer.FindOrOpen(subLayerPath)
            self.PopulateUnder(subLayer, parent=layerItem)


SublayerDialogContext = NamedTuple('SublayerDialogContext',
                                   [('layerDialog', QtWidgets.QWidget),
                                    ('stage', Usd.Stage),
                                    ('selectedLayer', Optional[Sdf.Layer]),
                                    ('editTargetLayer', Sdf.Layer)])


class ShowLayerContents(MenuAction):
    defaultText = 'Show Layer Text'

    def Do(self, context):
        if context.selectedLayer:
            dialog = LayerTextEditorDialog.GetSharedInstance(
                context.selectedLayer,
                parent=context.layerDialog.parent())
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()


class CopyLayerPath(MenuAction):
    defaultText = 'Copy Layer Identifier'

    def Do(self, context):
        if context.selectedLayer:
            CopyToClipboard(context.selectedLayer.identifier)

class OpenLayer(MenuAction):
    # emitted when menu option is selected to show layer contents
    openLayer = QtCore.Signal(Sdf.Layer)

    def label(self, builder, selection):
        return 'Open Layer in a new Outliner'

    def do(self, builder, selection):
        self.openLayer.emit(selection.layer)


class SubLayerTreeView(ContextMenuMixin, QtWidgets.QTreeView):
    def __init__(self, contextProvider, parent=None):
        contextMenuActions = [ShowLayerContents, CopyLayerPath, OpenLayer]
        super(SubLayerTreeView, self).__init__(
            contextMenuActions=contextMenuActions,
            contextProvider=contextProvider,
            parent=parent)

    def GetSelectedLayer(self):
        '''
        Returns
        -------
        Optional[Sdf.Layer]
        '''
        selectionModel = self.selectionModel()
        indexes = selectionModel.selectedRows()
        if indexes:
            index = indexes[0]
            if index.isValid():
                return index.internalPointer().layer


class SubLayerDialog(QtWidgets.QDialog):
    def __init__(self, stage, editTargetChangeCallback=None, parent=None):
        # type: (Usd.Stage, Optional[QtGui.QWidget]) -> None
        '''
        Parameters
        ----------
        stage : Usd.Stage
        editTargetChangeCallback : Callable[[], bool]
            Optional validation callback that will be called when the user
            attempts to change the current edit target (by double-clicking a
            layer). If this is provided and returns False, the edit target will
            not be changed.
        parent : Optional[QtGui.QWidget]
        '''
        super(SubLayerDialog, self).__init__(parent=parent)
        self._stage = stage
        self._dataModel = SubLayerModel(stage, parent=self)
        self._editTargetChangeCallback = editTargetChangeCallback

        # Widget and other Qt setup
        self.setModal(False)
        self.setWindowTitle('Select Edit Target')

        self.view = SubLayerTreeView(self, parent=self)
        self.view.setModel(self._dataModel)
        self.view.doubleClicked.connect(self.ChangeEditTarget)
        self.view.setColumnWidth(0, 160)
        self.view.setColumnWidth(1, 300)
        self.view.setColumnWidth(2, 100)
        self.view.setExpandsOnDoubleClick(False)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self.view)
        self.view.expandAll()

        self.resize(700, 200)

    def GetMenuContext(self):
        stage = self._stage
        return SublayerDialogContext(
            layerDialog=self,
            stage=stage,
            selectedLayer=self.view.GetSelectedLayer(),
            editTargetLayer=stage.GetEditTarget().GetLayer())

    @QtCore.Slot(QtCore.QModelIndex)
    def ChangeEditTarget(self, modelIndex):
        if not modelIndex.isValid():
            return
        item = modelIndex.internalPointer()
        newLayer = item.layer

        if self._editTargetChangeCallback is None \
                or self._editTargetChangeCallback(newLayer):
            self._stage.SetEditTarget(newLayer)
