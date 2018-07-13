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

from ._Qt import QtWidgets, QtCore
from pxr import Usd, UsdUtils, Sdf
from pxr import UsdQt


class HierarchyStandardContextMenuStrategy:
    """A simple context menu"""

    def __init__(self, hierarchyEditor):
        self.hierarchyEditor = hierarchyEditor

    def Construct(self, point):
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

    def __BuildStageMap(self, prims):
        """All prims are likely on the same stage, but in the event that we
        allow for hybrid models, this should ensure everything still works"""
        stageMap = defaultdict(set)
        for prim in prims:
            stageMap[prim.GetStage()].add(prim.GetPath())
        return stageMap

    def LoadSelection(self):
        prims = self._GetSelectedPrims()
        stageMap = self.__BuildStageMap(prims)
        for stage in stageMap:
            stage.LoadAndUnload(stageMap[stage], [])

    def UnloadSelection(self):
        prims = self._GetSelectedPrims()
        stageMap = self.__BuildStageMap(prims)
        for stage in stageMap:
            stage.LoadAndUnload([], stageMap[stage])


class HierarchyEditor(QtWidgets.QWidget):
    '''The hierarchy editor provides a filterable tree view of the prim
    hierarchy.  This class may be used as is for simple/standard uses cases.

    For more specialized use cases, this class should be used as an exmaple of
    how to build an editor around the UsdQt hierarchy components and not
    directly subclassed.
    '''
    ShowInactive = "Show Inactive"
    ShowUndefined = "Show Undefined (Overs)"
    ShowAbstract = "Show Abstract (Classes)"
    FilterAcrossArcs = "Filter Across Arcs"

    # A context menu strategy takes the editor as an input
    ContextMenuStrategy = HierarchyStandardContextMenuStrategy
    FilterModel = UsdQt.HierarchyStandardFilterModel

    def __init__(self, parent=None):
        super(HierarchyEditor, self).__init__(parent=parent)

        self.menuBar = QtWidgets.QMenuBar()

        self.showMenu = QtWidgets.QMenu("Show")
        self.menuBar.addMenu(self.showMenu)

        self.__filterLineEdit = QtWidgets.QLineEdit()
        self.__hierarchyView = QtWidgets.QTreeView()

        self.__showMenuItems = OrderedDict([
            (HierarchyEditor.ShowInactive, QtWidgets.QAction(
                HierarchyEditor.ShowInactive, self)),
            (HierarchyEditor.ShowUndefined, QtWidgets.QAction(
                HierarchyEditor.ShowUndefined, self)),
            (HierarchyEditor.ShowAbstract, QtWidgets.QAction(
                HierarchyEditor.ShowAbstract, self)),
            (HierarchyEditor.FilterAcrossArcs, QtWidgets.QAction(
                HierarchyEditor.FilterAcrossArcs, self)),
        ])

        for item in self.__showMenuItems:
            self.__showMenuItems[item].setCheckable(True)
            self.showMenu.addAction(self.__showMenuItems[item])

        self.__filterModel = UsdQt.HierarchyStandardFilterModel()

        self.__showMenuItems[HierarchyEditor.ShowInactive].toggled.connect(
            self.__filterModel.TogglePrimInactive)
        self.__showMenuItems[HierarchyEditor.ShowUndefined].toggled.connect(
            self.__filterModel.TogglePrimUndefined)
        self.__showMenuItems[HierarchyEditor.ShowAbstract].toggled.connect(
            self.__filterModel.TogglePrimAbstract)
        self.__showMenuItems[HierarchyEditor.FilterAcrossArcs].toggled.connect(
            self.__filterModel.ToggleFilterAcrossArcs)

        self.__showMenuItems[HierarchyEditor.FilterAcrossArcs].setChecked(True)
        self.__showMenuItems[HierarchyEditor.ShowInactive].setChecked(False)
        self.__showMenuItems[HierarchyEditor.ShowUndefined].setChecked(False)
        self.__showMenuItems[HierarchyEditor.ShowAbstract].setChecked(False)

        self.__layout = QtWidgets.QVBoxLayout()
        self.__layout.addWidget(self.menuBar)
        self.__layout.addWidget(self.__filterLineEdit)
        self.__layout.addWidget(self.__hierarchyView)

        self.__hierarchyView.setModel(self.__filterModel)
        self.__hierarchyView.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)

        self.__filterLineEdit.returnPressed.connect(
            self.__OnFilterReturnPressed)

        self.setLayout(self.__layout)
        self.__SetupContextMenu()

    def __SetupContextMenu(self):
        self.__contextMenu = self.ContextMenuStrategy(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__contextMenu.Construct)

    def __OnFilterReturnPressed(self):
        self.__filterModel.SetPathContainsFilter(self.__filterLineEdit.text())

    @property
    def primSelectionChanged(self):
        '''Provides access to the internal QItemSelectionModel's
        selectionChanged signal for callbacks on prim selection changes.'''
        return self.__hierarchyView.selectionModel().selectionChanged

    def SelectPaths(self, paths):
        itemSelection = QtCore.QItemSelection()
        sourceModel = self.__filterModel.sourceModel()
        for path in paths:
            index = sourceModel.GetIndexForPath(path)
            if index and index.isValid():
                itemSelection.select(index, index)
        mappedSelection = self.__filterModel.mapSelectionFromSource(
            itemSelection)
        self.__hierarchyView.selectionModel().select(mappedSelection,
                                                     QtCore.QItemSelectionModel.ClearAndSelect)

    def GetSelectedPrims(self):
        selectedIndices = self.__hierarchyView.selectedIndexes()
        orderedPrims = []
        unorderedPrims = set()
        for index in selectedIndices:
            prim = index.data(role=UsdQt.roles.HierarchyPrimRole)
            if prim not in unorderedPrims:
                unorderedPrims.add(prim)
                orderedPrims.append(prim)
        return orderedPrims

    def GetPrimSelectedIndices(self):
        '''Provides access to the internal selected indices'''
        return self.__hierarchyView.selectedIndexes()

    def SetSourceModel(self, model):
        '''Replaces the current editor's current model with the new model.
        The model must be a subclass of HierarchyBaseModel.'''
        self.__filterModel.setSourceModel(model)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    with Usd.StageCacheContext(UsdUtils.StageCache.Get()):
        stage = Usd.Stage.Open(
            '../usdQt/testenv/testUsdQtHierarchyModel/simpleHierarchy.usda')

    model = UsdQt.HierarchyBaseModel(stage)

    class Listener(QtCore.QObject):

        def __init__(self, parent=None):
            super(Listener, self).__init__(parent=parent)

        @QtCore.Slot()
        def OnPrimSelectionChanged(self, selected=None, deselected=None):
            for index in self.sender().selectedIndexes():
                prim = index.data(role=UsdQt.roles.HierarchyPrimRole)
                # print(prim)

    editor = HierarchyEditor()
    editor.SetSourceModel(model)
    editor.show()

    listener = Listener()
    editor.primSelectionChanged.connect(listener.OnPrimSelectionChanged)

    sys.exit(app.exec_())
