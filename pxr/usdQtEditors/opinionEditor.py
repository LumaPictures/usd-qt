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

# TODO: Make all proxies and handlers not private
from pxr.UsdQt._bindings import _AttributeProxy, _DisplayGroupProxy, \
    _MetadataProxy, _PrimProxy, _VariantSetProxy, _VariantSetsProxy
from pxr.UsdQt.opinionStackModel import OpinionStackFilter, OpinionStackModel, \
    _AttributeHandler, _PrimMetadataHandler, _VariantSetHandler, \
    _VariantSetsHandler
from pxr.UsdQt.valueDelegate import ValueDelegate

from ._Qt import QtCore, QtWidgets
from . import treeView

if False:
    from typing import *
    from pxr.UsdQt.opinionStackModel import _BaseHandler, OpinionBaseModel


class OpinionStackWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(OpinionStackWidget, self).__init__(parent=parent)
        self._toolBar = QtWidgets.QToolBar()
        self._toolBar.addWidget(QtWidgets.QLabel('Opinion Stack'))
        self._toolBar.addSeparator()
        self._showAllAction = self._toolBar.addAction("Show All")
        self._showAllAction.setCheckable(True)
        self._closeAction = self._toolBar.addAction("Close")
        self._showAllAction.toggled.connect(self._OnShowAllToggled)
        self._closeAction.triggered.connect(self._OnClose)

        self._opinionFilter = OpinionStackFilter()
        self._view = QtWidgets.QTreeView()
        self._view.setModel(self._opinionFilter)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.addWidget(self._toolBar)
        self._layout.addWidget(self._view)
        self.setLayout(self._layout)

        policy = QtWidgets.QSizePolicy()
        policy.setHorizontalPolicy(QtWidgets.QSizePolicy.MinimumExpanding)
        policy.setVerticalPolicy(QtWidgets.QSizePolicy.MinimumExpanding)
        self.setSizePolicy(policy)

    def Launch(self, model):
        # type: (QtCore.QAbstractItemModel) -> None
        """
        Parameters
        ----------
        model : QtCore.QAbstractItemModel
        """
        self._opinionFilter.setSourceModel(model)
        self.show()

    def Close(self):
        self.hide()
        self._opinionFilter.setSourceModel(None)

    def _OnShowAllToggled(self, checked):
        self._opinionFilter.SetShowFullStack(checked)

    def _OnClose(self):
        self.Close()


class OpinionEditor(QtWidgets.QWidget):
    def __init__(self, delegate=None, parent=None):
        # type: (Optional[QtWidgets.QAbstractItemDelegate], Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        delegate : Optional[QtWidgets.QAbstractItemDelegate]
        parent : Optional[QtWidgets.QWidget]
        """
        super(OpinionEditor, self).__init__(parent=parent)
        self._menuBar = QtWidgets.QMenuBar()
        self._layout = QtWidgets.QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.addWidget(self._menuBar)

        self._view = treeView.TreeView()
        if delegate is None:
            delegate = ValueDelegate()
        self._view.setItemDelegate(delegate)
        self._view.setEditTriggers(
            QtWidgets.QAbstractItemView.CurrentChanged |
            QtWidgets.QAbstractItemView.SelectedClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed)
        self._view.setColumnWidth(0, 160)
        self._view.setColumnWidth(1, 160)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
        # TODO: Implement opinion filtering
        # self._filterLineEdit = QtWidgets.QLineEdit()
        # self._layout.addWidget(self._filterLineEdit)
        self._layout.addWidget(self._splitter)
        self._splitter.addWidget(self._view)
        self._view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        self._SetupOpinionViewWidget()

    @property
    def view(self):
        return self._view

    def _SetupOpinionViewWidget(self):
        self._opinionViewer = OpinionStackWidget()
        self._opinionViewer.hide()
        self._splitter.addWidget(self._opinionViewer)

    def LaunchOpinionViewer(self, prim, handler):
        # type: (Usd.Prim, _BaseHandler) -> None
        """
        Parameters
        ----------
        prim : Usd.Prim
        handler : _BaseHandler
        """
        self._opinionViewer.Launch(OpinionStackModel(prim, handler))

    def SetSourceModel(self, model):
        self._view.setModel(model)
        self.ResetColumnSpanned()

    def _TraverseAllDescendents(self, index):
        for i in xrange(self._view.model().rowCount(index)):
            childIndex = self._view.model().index(i, 0, index)
            yield childIndex
            for descendent in self._TraverseAllDescendents(childIndex):
                yield descendent

    def ResetColumnSpanned(self):
        for index in self._TraverseAllDescendents(QtCore.QModelIndex()):
            if type(index.internalPointer()) in (_DisplayGroupProxy, _PrimProxy):
                self._view.setFirstColumnSpanned(
                    index.row(), index.parent(), True)


class OpinionController(QtCore.QObject):
    def __init__(self, model, editor, parent=None):
        # type: (OpinionBaseModel, OpinionEditor, Optional[QtCore.QObject]) -> None
        """
        Parameters
        ----------
        model : OpinionBaseModel
        editor : OpinionEditor
        parent : Optional[QtCore.QObject]
        """
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
                self.editor.LaunchOpinionViewer(
                    attribute.GetPrim(),
                    _AttributeHandler(attribute.GetName(),
                                      Usd.TimeCode.Default()))
        elif type(proxy) == _MetadataProxy:
            if proxy.GetSize() == 1:
                objects = proxy.GetObjects()
                obj = objects[0]
                if type(obj) == Usd.Prim:
                    self.editor.LaunchOpinionViewer(
                        obj,
                        _PrimMetadataHandler(proxy.GetName()))

    def ResetPrims(self, prims):
        # type: (List[Usd.Prim]) -> None
        """
        Parameters
        ----------
        prims : List[Usd.Prim]
        """
        self.model.ResetPrims(prims)
        self.editor.ResetColumnSpanned()


class OpinionDialog(QtWidgets.QDialog):
    def __init__(self, prims=None, parent=None):
        from pxr.UsdQt.opinionModel import OpinionStandardModel
        super(OpinionDialog, self).__init__(parent=parent)

        self.editor = OpinionEditor()
        model = OpinionStandardModel(prims)
        self.editor.SetSourceModel(model)
        self.controller = OpinionController(model, self.editor)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)

        # Widget and other Qt setup
        self.setModal(False)
        self.resize(700, 500)


if __name__ == '__main__':
    import sys
    from pxr.UsdQt.opinionModel import OpinionStandardModel

    app = QtWidgets.QApplication(sys.argv)
    stage = Usd.Stage.Open('../usdQt/testenv/testUsdQtOpinionModel/simple.usda')
    prim = stage.GetPrimAtPath('/MyPrim1/Child1')

    model = OpinionStandardModel([prim])
    # modelComposition = compositionModel.CompositionStandardModel(prim)
    editor = OpinionEditor()

    controller = OpinionController(model, editor)
    editor.SetSourceModel(model)
    editor.show()

    sys.exit(app.exec_())
