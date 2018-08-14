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

from collections import OrderedDict, defaultdict

from pxr import Usd, UsdUtils, Sdf
from pxr.UsdQt.hierarchyModel import HierarchyStandardFilterModel
from pxr.UsdQt import roles

from ._Qt import QtWidgets, QtCore

if False:
    from typing import *
    from pxr.UsdQt.hierarchyModel import HierarchyBaseModel


class HierarchyStandardContextMenuStrategy(object):
    """A simple context menu"""
    def __init__(self, hierarchyEditor):
        self.hierarchyEditor = hierarchyEditor

    def Construct(self, point):
        # type: (QtCore.QPoint) -> None
        """
        Parameters
        ----------
        point : QtCore.QPoint
        """
        prims = self._GetSelectedPrims()
        if len(prims) == 1:
            name = prims[0].GetName()
        else:
            name = "%i selected prims" % len(prims)
        menu = QtWidgets.QMenu()
        activateAction = menu.addAction("Activate %s" % name)
        activateAction.triggered.connect(self.ActivateSelection)
        deactivateAction = menu.addAction("Deactivate %s" % name)
        deactivateAction.triggered.connect(self.DeactivateSelection)
        clearActiveAction = menu.addAction("Clear Activation for %s" % name)
        clearActiveAction.triggered.connect(self.ClearActiveForSelection)
        loadAction = menu.addAction("Load %s" % name)
        loadAction.triggered.connect(self.LoadSelection)
        unloadAction = menu.addAction("Unload %s" % name)
        unloadAction.triggered.connect(self.UnloadSelection)
        menu.exec_(self.hierarchyEditor.mapToGlobal(point))

    def _GetSelectedPrims(self):
        # type: () -> List[Usd.Prim]
        """
        Returns
        -------
        List[Usd.Prim]
        """
        selection = self.hierarchyEditor.GetSelectedPrims()
        selection.sort(key=lambda prim: prim.GetPath(), reverse=True)
        return selection

    def ActivateSelection(self):
        with Sdf.ChangeBlock():
            prims = self._GetSelectedPrims()
            for prim in prims:
                prim.SetActive(True)

    def DeactivateSelection(self):
        with Sdf.ChangeBlock():
            prims = self._GetSelectedPrims()
            for prim in prims:
                prim.SetActive(False)

    def ClearActiveForSelection(self):
        with Sdf.ChangeBlock():
            prims = self._GetSelectedPrims()
            for prim in prims:
                prim.ClearActive()

    def _BuildStageMap(self, prims):
        # type: (Any) -> Dict[Usd.Stage, Set[Sdf.Path]]
        """All prims are likely on the same stage, but in the event that we
        allow for hybrid models, this should ensure everything still works.

        Parameters
        ----------
        Iterable[Usd.Prim]

        Returns
        -------
        Dict[Usd.Stage, Set[Sdf.Path]]
        """
        stageMap = defaultdict(set)
        for prim in prims:
            stageMap[prim.GetStage()].add(prim.GetPath())
        return stageMap

    def LoadSelection(self):
        prims = self._GetSelectedPrims()
        stageMap = self._BuildStageMap(prims)
        for stage in stageMap:
            stage.LoadAndUnload(stageMap[stage], [])

    def UnloadSelection(self):
        prims = self._GetSelectedPrims()
        stageMap = self._BuildStageMap(prims)
        for stage in stageMap:
            stage.LoadAndUnload([], stageMap[stage])


class HierarchyEditor(QtWidgets.QWidget):
    """The hierarchy editor provides a filterable tree view of the prim
    hierarchy.  This class may be used as is for simple/standard uses cases.

    For more specialized use cases, this class should be used as an exmaple of
    how to build an editor around the UsdQt hierarchy components and not
    directly subclassed.
    """
    ShowInactive = "Show Inactive"
    ShowUndefined = "Show Undefined (Overs)"
    ShowAbstract = "Show Abstract (Classes)"
    FilterAcrossArcs = "Filter Across Arcs"

    # A context menu strategy takes the editor as an input
    ContextMenuStrategy = HierarchyStandardContextMenuStrategy
    FilterModel = HierarchyStandardFilterModel

    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(HierarchyEditor, self).__init__(parent=parent)

        self.menuBar = QtWidgets.QMenuBar()

        self.showMenu = QtWidgets.QMenu("Show")
        self.menuBar.addMenu(self.showMenu)

        self._filterLineEdit = QtWidgets.QLineEdit()
        self._hierarchyView = QtWidgets.QTreeView()

        self._showMenuItems = OrderedDict([
            (HierarchyEditor.ShowInactive, QtWidgets.QAction(
                HierarchyEditor.ShowInactive, self)),
            (HierarchyEditor.ShowUndefined, QtWidgets.QAction(
                HierarchyEditor.ShowUndefined, self)),
            (HierarchyEditor.ShowAbstract, QtWidgets.QAction(
                HierarchyEditor.ShowAbstract, self)),
            (HierarchyEditor.FilterAcrossArcs, QtWidgets.QAction(
                HierarchyEditor.FilterAcrossArcs, self)),
        ])

        for item in self._showMenuItems:
            self._showMenuItems[item].setCheckable(True)
            self.showMenu.addAction(self._showMenuItems[item])

        self._filterModel = HierarchyStandardFilterModel()

        self._showMenuItems[HierarchyEditor.ShowInactive].toggled.connect(
            self._filterModel.TogglePrimInactive)
        self._showMenuItems[HierarchyEditor.ShowUndefined].toggled.connect(
            self._filterModel.TogglePrimUndefined)
        self._showMenuItems[HierarchyEditor.ShowAbstract].toggled.connect(
            self._filterModel.TogglePrimAbstract)
        self._showMenuItems[HierarchyEditor.FilterAcrossArcs].toggled.connect(
            self._filterModel.ToggleFilterAcrossArcs)

        self._showMenuItems[HierarchyEditor.FilterAcrossArcs].setChecked(True)
        self._showMenuItems[HierarchyEditor.ShowInactive].setChecked(False)
        self._showMenuItems[HierarchyEditor.ShowUndefined].setChecked(False)
        self._showMenuItems[HierarchyEditor.ShowAbstract].setChecked(False)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.addWidget(self.menuBar)
        self._layout.addWidget(self._filterLineEdit)
        self._layout.addWidget(self._hierarchyView)

        self._hierarchyView.setModel(self._filterModel)
        self._hierarchyView.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)

        self._filterLineEdit.returnPressed.connect(
            self._OnFilterReturnPressed)

        self.setLayout(self._layout)
        self._SetupContextMenu()

    def _SetupContextMenu(self):
        self._contextMenu = self.ContextMenuStrategy(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu.Construct)

    def _OnFilterReturnPressed(self):
        self._filterModel.SetPathContainsFilter(self._filterLineEdit.text())

    @property
    def primSelectionChanged(self):
        """Provides access to the internal QItemSelectionModel's
        selectionChanged signal for callbacks on prim selection changes."""
        return self._hierarchyView.selectionModel().selectionChanged

    def SelectPaths(self, paths):
        # type: (Iterable[Sdf.Path]) -> None
        """
        Parameters
        ----------
        paths : Iterable[Sdf.Path]
        """
        itemSelection = QtCore.QItemSelection()
        sourceModel = self._filterModel.sourceModel()
        for path in paths:
            index = sourceModel.GetIndexForPath(path)
            if index and index.isValid():
                itemSelection.select(index, index)
        mappedSelection = self._filterModel.mapSelectionFromSource(
            itemSelection)
        self._hierarchyView.selectionModel().select(mappedSelection,
                                                    QtCore.QItemSelectionModel.ClearAndSelect)

    def GetSelectedPrims(self):
        # type: () -> List[Usd.Prim]
        """
        Returns
        -------
        List[Usd.Prim]
        """
        selectedIndices = self._hierarchyView.selectedIndexes()
        orderedPrims = []
        unorderedPrims = set()
        for index in selectedIndices:
            prim = index.data(role=roles.HierarchyPrimRole)
            if prim not in unorderedPrims:
                unorderedPrims.add(prim)
                orderedPrims.append(prim)
        return orderedPrims

    def GetPrimSelectedIndices(self):
        # type: () -> List[QtCore.QModelIndex]
        """Provides access to the internal selected indices.

        Returns
        -------
        List[QtCore.QModelIndex]
        """
        return self._hierarchyView.selectedIndexes()

    def SetSourceModel(self, model):
        # type: (HierarchyBaseModel) -> None
        """Replaces the current editor's current model with the new model.
        The model must be a subclass of HierarchyBaseModel.

        Parameters
        ----------
        model : HierarchyBaseModel
        """
        self._filterModel.setSourceModel(model)


if __name__ == "__main__":
    import sys
    from pxr.UsdQt.hierarchyModel import HierarchyBaseModel

    app = QtWidgets.QApplication(sys.argv)

    with Usd.StageCacheContext(UsdUtils.StageCache.Get()):
        stage = Usd.Stage.Open(
            '../usdQt/testenv/testUsdQtHierarchyModel/simpleHierarchy.usda')

    model = HierarchyBaseModel(stage)

    class Listener(QtCore.QObject):

        def __init__(self, parent=None):
            super(Listener, self).__init__(parent=parent)

        @QtCore.Slot()
        def OnPrimSelectionChanged(self, selected=None, deselected=None):
            for index in self.sender().selectedIndexes():
                prim = index.data(role=roles.HierarchyPrimRole)
                # print(prim)

    editor = HierarchyEditor()
    editor.SetSourceModel(model)
    editor.show()

    listener = Listener()
    editor.primSelectionChanged.connect(listener.OnPrimSelectionChanged)

    sys.exit(app.exec_())
