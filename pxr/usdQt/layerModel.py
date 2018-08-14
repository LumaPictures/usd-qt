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

from ._Qt import QtCore
from pxr import Sdf, Usd

from treemodel.itemtree import ItemTree, TreeItem
from treemodel.qt.base import AbstractTreeModelMixin

if False:
    from typing import *


class LayerItem(TreeItem):
    __slots__ = ('layer',)

    def __init__(self, layer):
        # type: (Sdf.Layer) -> None
        """
        Parameters
        ----------
        layer : Sdf.Layer
        """
        super(LayerItem, self).__init__(key=layer.identifier)
        self.layer = layer


class LayerStackBaseModel(AbstractTreeModelMixin, QtCore.QAbstractItemModel):
    """Basic tree model that exposes a Stage's layer stack."""
    headerLabels = ('Name', 'Path')

    def __init__(self, stage, includeSessionLayers=True, parent=None):
        # type: (Usd.Stage, bool, Optional[QtCore.QObject]) -> None
        """
        Parameters
        ----------
        stage : Usd.Stage
        includeSessionLayers : bool
        parent : Optional[QtCore.QObject]
        """
        super(LayerStackBaseModel, self).__init__(parent=parent)
        self._stage = None
        self._includeSessionLayers = includeSessionLayers
        self.ResetStage(stage)

    # Qt methods ---------------------------------------------------------------
    def columnCount(self, parentIndex):
        return 2

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.headerLabels[section]

    def data(self, modelIndex, role=QtCore.Qt.DisplayRole):
        if not modelIndex.isValid():
            return
        if role == QtCore.Qt.DisplayRole:
            column = modelIndex.column()
            item = modelIndex.internalPointer()
            if column == 0:
                if item.layer.anonymous:
                    return '<anonymous>'
                return item.layer.identifier.rsplit('/', 1)[-1]
            elif column == 1:
                return item.layer.identifier

    # Custom methods -----------------------------------------------------------
    def LayerCount(self):
        """Return the number of layers in the current stage's layer stack."""
        return self.itemTree.ItemCount()

    def ResetStage(self, stage):
        # type: (Usd.Stage) -> None
        """Reset the model from a new stage.

        Parameters
        ----------
        stage : Usd.Stage
        """
        if stage == self._stage:
            return

        self.beginResetModel()
        itemTree = self.itemTree = ItemTree()

        def addLayer(layer, parent=None):
            layerItem = LayerItem(layer)
            itemTree.AddItems(layerItem, parent=parent)
            return layerItem

        def addLayerTree(layerTree, parent=None):
            item = addLayer(layerTree.layer, parent=parent)
            for childTree in layerTree.childTrees:
                addLayerTree(childTree, parent=item)

        self._stage = None
        if stage:
            root = stage.GetPseudoRoot()
            if root:
                self._stage = stage
                if self._includeSessionLayers:
                    sessionLayer = stage.GetSessionLayer()
                    if sessionLayer:
                        sessionLayerItem = addLayer(sessionLayer)
                        for path in sessionLayer.subLayerPaths:
                            addLayer(Sdf.Layer.FindOrOpen(path),
                                     parent=sessionLayerItem)
                layerTree = root.GetPrimIndex().rootNode.layerStack.layerTree
                addLayerTree(layerTree)

        self.endResetModel()


if __name__ == '__main__':
    """ Sample usage """
    from pxr import Usd
    from ._Qt import QtWidgets
    import sys
    import os

    app = QtWidgets.QApplication([])
    path = os.path.join(os.path.dirname(__file__), 'testenv',
                        'testUsdQtLayerModel', 'simpleLayerStack.usda')
    stage = Usd.Stage.Open(path)

    model = LayerStackBaseModel(stage)
    view = QtWidgets.QTreeView()
    view.setModel(model)

    def OnDoubleClicked(modelIndex):
        print modelIndex.data()

    view.doubleClicked.connect(OnDoubleClicked)
    view.show()

    sys.exit(app.exec_())
