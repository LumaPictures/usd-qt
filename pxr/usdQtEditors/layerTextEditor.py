#
# Copyright 2017 Pixar
#
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification; you may not use this file except in
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
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License with the above modification is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the Apache License for the specific
# language governing permissions and limitations under the Apache License.
#

from __future__ import absolute_import

from ._Qt import QtCore, QtWidgets
from pxr import Sdf, Tf, Usd

if False:
    from typing import *


class LayerTextEditor(QtWidgets.QWidget):
    """A basic text widget for viewing/editing the contents of a layer."""
    # Emitted when the layer is saved by this editor.
    layerSaved = QtCore.Signal(Sdf.Layer)

    def __init__(self, layer, readOnly=False, parent=None):
        # type: (Sdf.Layer, bool, Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        layer : Sdf.Layer
        readOnly : bool
        parent : Optional[QtWidgets.QWidget]
        """
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

        self.SetEditable(False)
        self.Refresh()

    def SetEditable(self, editable):
        # type: (bool) -> None
        """
        Parameters
        ----------
        editable : bool
        """
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


class LayerTextEditorDialog(QtWidgets.QDialog):
    """Dialog version of LayerTextEditor that enables easy sharing of instances.
    """
    _sharedInstances = {}
    def __init__(self, layer, readOnly=False, parent=None):
        # type: (Sdf.Layer, bool, Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        layer : Sdf.Layer
        readOnly : bool
        parent : Optional[QtWidgets.QWidget]
        """
        super(LayerTextEditorDialog, self).__init__(parent=parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.editor = LayerTextEditor(layer, readOnly=readOnly, parent=self)
        layout.addWidget(self.editor)

        self.setWindowTitle('Layer: %s' % layer.identifier)
        self.resize(800, 600)

    @classmethod
    def _OnSharedInstanceFinished(cls, layer):
        dialog = cls._sharedInstances.pop(layer, None)
        if dialog:
            dialog.deleteLater()

    @classmethod
    def GetSharedInstance(cls, layer, readOnly=False, parent=None):
        # type: (Sdf.Layer, bool, Optional[QtWidgets.QWidget]) -> LayerTextEditorDialog
        """Convenience method to get or create a shared editor dialog instance.

        Parameters
        ----------
        layer : Sdf.Layer
        readOnly : bool
        parent : Optional[QtWidgets.QWidget]

        Returns
        -------
        LayerTextEditorDialog
        """
        dialog = cls._sharedInstances.get(layer)
        if dialog is None:
            dialog = cls(layer, readOnly=readOnly, parent=parent)
            cls._sharedInstances[layer] = dialog
            dialog.finished.connect(
                lambda result: cls._OnSharedInstanceFinished(layer))
        return dialog


if __name__ == "__main__":
    import sys

    stage = Usd.Stage.Open(
        '../usdQt/testenv/testUsdQtOpinionModel/simple.usda')
    layer = stage.GetLayerStack(includeSessionLayers=True)[1]

    app = QtWidgets.QApplication(sys.argv)

    e = LayerTextEditorDialog(layer, readOnly=True)
    e.show()
    sys.exit(app.exec_())
