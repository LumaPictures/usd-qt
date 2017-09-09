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
from __future__ import division
from __future__ import print_function

from pxr import Usd

from ._Qt import QtCore, QtGui, QtWidgets


class LayerTextEditor(QtWidgets.QWidget):
    """A simple editor allowing for browsing the ascii for a Usd Layer"""

    def __init__(self, parent=None):
        super(LayerTextEditor, self).__init__(parent)
        self.__refreshButton = QtWidgets.QPushButton("Refresh")
        self.__textEdit = QtWidgets.QPlainTextEdit(parent)
        self.__textEdit.setFont(QtGui.QFont("monospace"))
        self.__textEdit.setReadOnly(True)
        self.__layout = QtWidgets.QVBoxLayout()
        self.__headerLayout = QtWidgets.QHBoxLayout()
        self.__headerLayout.addWidget(self.__refreshButton)
        self.__layout.addLayout(self.__headerLayout)
        self.__layout.addWidget(self.__textEdit)
        self.setLayout(self.__layout)
        self.__refreshButton.clicked.connect(self.__OnRefreshButtonClicked)

        self.__layer = None

    def SetLayer(self, layer):
        self.__layer = layer

    @QtCore.Slot(Usd.EditTarget)
    def OnEditTargetChanged(self, editTarget):
        """Slot for changing the layer whenever the edit target changes."""
        self.__editTargetLayer = editTarget.GetLayer()

    @QtCore.Slot()
    def __OnRefreshButtonClicked(self):
        if self.__layer:
            self.__textEdit.document().setPlainText(
                self.__layer.ExportToString())
        else:
            self.__textEdit.document().setPlainText("Invalid layer")


if __name__ == "__main__":
    import sys
    from pxr import Usd

    stage = Usd.Stage.Open(
        '../usdQt/testenv/testUsdQtOpinionModel/simple.usda')
    layer = stage.GetLayerStack(includeSessionLayers=True)[1]

    app = QtWidgets.QApplication(sys.argv)

    e = LayerTextEditor()
    e.SetLayer(layer)
    e.show()

    sys.exit(app.exec_())
