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
from pxr import UsdQt

# TODO: Make all proxies and handlers not private
from pxr.UsdQt._bindings import _AttributeProxy, _DisplayGroupProxy, \
    _MetadataProxy, _PrimProxy, _VariantSetProxy, _VariantSetsProxy
from pxr.UsdQt.opinionStackModel import _AttributeHandler, _PrimMetadataHandler, \
    _VariantSetHandler, _VariantSetsHandler

from . import treeView

from ._Qt import QtCore, QtWidgets


class OpinionStackWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(OpinionStackWidget, self).__init__(parent=parent)
        self.__toolBar = QtWidgets.QToolBar()
        self.__toolBar.addWidget(QtWidgets.QLabel('Opinion Stack'))
        self.__toolBar.addSeparator()
        self.__showAllAction = self.__toolBar.addAction("Show All")
        self.__showAllAction.setCheckable(True)
        self.__closeAction = self.__toolBar.addAction("Close")
        self.__showAllAction.toggled.connect(self.__OnShowAllToggled)
        self.__closeAction.triggered.connect(self.__OnClose)

        self.__opinionFilter = UsdQt.OpinionStackFilter()
        self.__view = QtWidgets.QTreeView()
        self.__view.setModel(self.__opinionFilter)

        self.__layout = QtWidgets.QVBoxLayout()
        self.__layout.addWidget(self.__toolBar)
        self.__layout.addWidget(self.__view)
        self.setLayout(self.__layout)

        policy = QtWidgets.QSizePolicy()
        policy.setHorizontalPolicy(QtWidgets.QSizePolicy.MinimumExpanding)
        policy.setVerticalPolicy(QtWidgets.QSizePolicy.MinimumExpanding)
        self.setSizePolicy(policy)

    def Launch(self, model):
        self.__opinionFilter.setSourceModel(model)
        self.show()

    def Close(self):
        self.hide()
        self.__opinionFilter.setSourceModel(None)

    def __OnShowAllToggled(self, checked):
        self.__opinionFilter.SetShowFullStack(checked)

    def __OnClose(self):
        self.Close()


class OpinionEditor(QtWidgets.QWidget):

    def __init__(self, delegate=None, parent=None):
        super(OpinionEditor, self).__init__(parent=parent)
        self.__menuBar = QtWidgets.QMenuBar()
        self.__layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.__layout)
        self.__layout.addWidget(self.__menuBar)
        self.__SetupActions()
        self.__SetupOptionsMenu()
        self.__SetupEditMenu()

        self.__filterLineEdit = QtWidgets.QLineEdit()

        self.__view = treeView.TreeView()
        itemDelegate = delegate if delegate else UsdQt.ValueDelegate()
        self.__view.setItemDelegate(itemDelegate)
        self.__view.setEditTriggers(
            QtWidgets.QAbstractItemView.CurrentChanged |
            QtWidgets.QAbstractItemView.SelectedClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed)

        self.__splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
        self.__layout.addWidget(self.__filterLineEdit)
        self.__layout.addWidget(self.__splitter)
        self.__splitter.addWidget(self.__view)
        self.__view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        self.__SetupOpinionViewWidget()

    @property
    def view(self):
        return self.__view

    def __SetupActions(self):
        pass

    def __SetupOptionsMenu(self):
        self.__optionsMenu = QtWidgets.QMenu("Options")
        # self.__optionsMenu.addAction(self.__actionToggleOpinionDebugger)
        self.__menuBar.addMenu(self.__optionsMenu)

    def __SetupEditMenu(self):
        self.__editMenu = QtWidgets.QMenu("Edit")
        # self.__editMenu.addAction(self.__actionToggleEditScalar)
        # self.__editMenu.addAction(self.__actionToggleEditArray)
        self.__menuBar.addMenu(self.__editMenu)

    def __SetupOpinionViewWidget(self):
        self.__opinionViewer = OpinionStackWidget()
        self.__opinionViewer.hide()
        self.__splitter.addWidget(self.__opinionViewer)

    def LaunchOpinionViewer(self, prim, handler):
        self.__opinionViewer.Launch(UsdQt.OpinionStackModel(prim, handler))

    def SetSourceModel(self, model):
        self.__view.setModel(model)
        self.ResetColumnSpanned()

    def __TraverseAllDescendents(self, index):
        for i in xrange(self.__view.model().rowCount(index)):
            childIndex = self.__view.model().index(i, 0, index)
            yield childIndex
            for descendent in self.__TraverseAllDescendents(childIndex):
                yield descendent

    def ResetColumnSpanned(self):
        for index in self.__TraverseAllDescendents(QtCore.QModelIndex()):
            if type(index.internalPointer()) in (_DisplayGroupProxy, _PrimProxy):
                self.__view.setFirstColumnSpanned(
                    index.row(), index.parent(), True)


class OpinionController(QtCore.QObject):

    def __init__(self, model, editor, parent=None):
        super(OpinionController, self).__init__(parent)
        self.model = model
        self.editor = editor
        self.editor.view.doubleClicked.connect(self.OnDoubleClicked)

    @QtCore.Slot(QtCore.QModelIndex)
    def OnDoubleClicked(self, index):
        proxy = self.model.GetProxyForIndex(index)
        if type(proxy) == _AttributeProxy:
            if proxy.GetSize() == 1:
                attributes = proxy.GetAttributes()
                attribute = attributes[0]
                self.editor.LaunchOpinionViewer(attribute.GetPrim(),
                                                _AttributeHandler(attribute.GetName(),
                                                                  Usd.TimeCode.Default()))
        elif type(proxy) == _MetadataProxy:
            if proxy.GetSize() == 1:
                objects = proxy.GetObjects()
                obj = objects[0]
                if type(obj) == Usd.Prim:
                    self.editor.LaunchOpinionViewer(obj,
                                                    _PrimMetadataHandler(proxy.GetName()))

    def ResetPrims(self, prims):
        self.model.ResetPrims(prims)
        self.editor.ResetColumnSpanned()

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    stage = Usd.Stage.Open('../usdQt/testenv/testUsdQtOpinionModel/simple.usda')
    prim = stage.GetPrimAtPath('/MyPrim1/Child1')

    model = UsdQt.OpinionStandardModel([prim])
    # modelComposition = compositionModel.CompositionStandardModel(prim)
    editor = OpinionEditor()

    controller = OpinionController(model, editor)
    editor.SetSourceModel(model)
    editor.show()

    sys.exit(app.exec_())
