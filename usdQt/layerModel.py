#
# Copyright 2016 Pixar
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

import os.path
from ._Qt import QtCore, QtWidgets, QtGui

from pxr import Sdf

from . import compatability
from . import roles


class LayerBaseModel(QtCore.QAbstractTableModel):
    """Base model for exposing a Usd Stage's layer stack to a Qt item view.

    For all but the simplest examples, you'll likely need to subclass
    this to add either additional columns, flags, or functionality.

    If you're interested in filtering out layers, consider using a custom
    subclass of QSortFilterProxyModel.

    WARNING.  There is currently no support for change notification for 
    adding and removing sublayers.
    """

    def __init__(self, stage=None,
                 includeSessionLayers=True,
                 parent=None):
        super(LayerBaseModel, self).__init__(parent=parent)
        self.__includeSessionLayers = includeSessionLayers
        self.__stage = None
        self.ResetStage(stage)

    def ResetStage(self, stage):
        """Apply the model to new stage"""
        if stage == self.__stage:
            return
        self.beginResetModel()
        self.__stage = stage
        if not self.__IsStageValid():
            self.__layers = None
        else:
            self.__layers = []
            if self.__includeSessionLayers:
                self.__layers.append((stage.GetSessionLayer(), 0))
                for subLayerPath in stage.GetSessionLayer().subLayerPaths:
                    self.__layers.append((Sdf.Layer.FindOrOpen(subLayerPath), 1))
            self.__WalkSublayers(0, self.__stage.GetPseudoRoot(
            ).GetPrimIndex().rootNode.layerStack.layerTree)
        self.endResetModel()

    def __WalkSublayers(self, depth, layerTree):
        self.__layers.append((layerTree.layer, depth))
        for childTree in layerTree.childTrees:
            self.__WalkSublayers(depth + 1, childTree)

    def __IsStageValid(self):
        return self.__stage and self.__stage.GetPseudoRoot()

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not self.__IsStageValid():
            return 0
        return len(self.__layers)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == QtCore.Qt.DisplayRole:
            if self.GetLayerFromIndex(index) == self.__stage.GetSessionLayer():
                return "session"
            identifier = self.GetIdentifierFromIndex(index)
            return os.path.splitext(os.path.split(identifier)[1])[0]

        if role == QtCore.Qt.ToolTipRole:
            return self.GetLayerPathFromIndex(index)

        if role == roles.LayerStackDepthRole:
            return self.GetLayerDepthFromIndex(index)

    def GetIdentifierFromIndex(self, index):
        """Returns the unique path identifier to the layer"""
        if not self.__IsStageValid():
            raise Exception("Requesting layer from closed stage.")
        return self.__layers[index.row()][0].identifier

    def GetLayerPathFromIndex(self, index):
        """Returns the unique path identifier to the layer """
        if not self.__IsStageValid():
            raise Exception("Requesting layer from closed stage.")
        return self.__layers[index.row()][0].realPath

    def GetLayerDepthFromIndex(self, index):
        """Returns the layer's depth in the layer tree hierarchy"""
        if not self.__IsStageValid():
            raise Exception("Requesting layer from closed stage.")
        return self.__layers[index.row()][1]

    def GetLayerFromIndex(self, index):
        """Returns an Sdf.Layer for the given index"""
        if not self.__IsStageValid():
            raise Exception("Requesting layer from closed stage.")
        return self.__layers[index.row()][0]


class LayerStandardModel(LayerBaseModel):
    """Configurable model for common options for displaying sublayers

    The standard model supports additional various masking operations. The masks
    are bitwise anded with the default implementation of flags.
    """

    def __init__(self, stage=None,
                 includeSessionLayers=True,
                 parent=None):
        super(LayerStandardModel, self).__init__(
            stage, includeSessionLayers=includeSessionLayers, parent=parent)

        self.__unsaveableFlagMask = None
        self.__uneditableFlagMask = None
        self.__fileFormatFlagMask = {}

    def flags(self, index):
        parentFlags = super(LayerStandardModel, self).flags(index)

        layer = self.GetLayerFromIndex(index)

        if not layer:
            parentFlags &= ~QtCore.Qt.ItemIsEnabled
        else:
            fileFormat = layer.GetFileFormat()
            if fileFormat in self.__fileFormatFlagMask:
                parentFlags &= self.__fileFormatFlagMask[fileFormat]
            if self.__uneditableFlagMask is not None:
                parentFlags &= self.__uneditableFlagMask
            if self.__unsaveableFlagMask is not None:
                parentFlags &= self.__unsaveableFlagMask

        return parentFlags

    def SetFileFormatFlagMask(self, fileFormat, flags):
        if not issubclass(type(fileFormat), Sdf.FileFormat):
            raise Exception("fileFormat must be of type Sdf.FileFormat")
        if flags is None and fileFormat in self.__fileFormatFlagMask:
            del self.__fileFormatFlagMask[fileFormat]
        self.__fileFormatFlagMask[fileFormat] = flags

    def SetUneditableFlagMask(self, flags):
        self.__uneditableFlagMask = flags

    def SetUnsaveableFlagMask(self, flags):
        self.__unsaveableFlagMask = flags


class LayerStackStyledDelegate(QtWidgets.QStyledItemDelegate):
    """Style delegate to handle indentation of layers """

    def __init__(self, parent=None):
        super(LayerStackStyledDelegate, self).__init__(parent)
        self.maxDepth = None

    def paint(self, painter, option, index):
        # indentation snippet from http://www.mimec.org/node/305
        depth = compatability.ResolveValue(
            index.data(roles.LayerStackDepthRole))

        if (depth == -1):
            super(LayerStackStyledDelegate, self).paint(painter, option, index)
            middle = (option.rect.top() + option.rect.bottom()) / 2.0
            painter.setPen(option.palette.color(
                QtGui.QPalette.Active, QtGui.QPalette.Dark))
            painter.drawLine(option.rect.left(), middle,
                             option.rect.right(), middle)
        else:
            indentedOption = QtWidgets.QStyleOptionViewItem(option)
            indentedationSize = option.fontMetrics.width('    ') * depth
            indentedOption.rect.adjust(indentedationSize, 0, 0, 0)
            super(LayerStackStyledDelegate, self).paint(
                painter, indentedOption, index)

if __name__ == '__main__':
    """ Sample usage """
    from pxr import Usd
    from ._Qt import QtWidgets
    import sys
    app = QtWidgets.QApplication([])

    stage = Usd.Stage.Open(
        "testenv/testUsdqLayerStackModel/simpleLayerStack.usda")

    comboBox = QtWidgets.QComboBox()
    delegate = LayerStackStyledDelegate()
    model = LayerStandardModel(stage)

    # disallow users from interacting with 'usdc' files
    model.SetFileFormatFlagMask(Sdf.FileFormat.FindById('usdc'),
                                ~QtCore.Qt.ItemIsEnabled)

    comboBox.setModel(model)
    comboBox.setItemDelegate(delegate)

    def OnActivated(index):
        print(model.data(model.createIndex(index, 0)))

    comboBox.activated.connect(OnActivated)
    comboBox.show()

    sys.exit(app.exec_())
