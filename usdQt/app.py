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

from pxr import Sdf, Usd
from Qt import QtCore, QtGui, QtWidgets
from usdQt.outliner import (OutlinerTreeView, OutlinerViewDelegate,
                            OutlinerStageModel, OutlinerContextMenuBuilder)
from usdQt.layers import LayerTextViewDialog, SubLayerDialog
from usdQt.variantSets import VariantEditorDialog
from usdQt.common import MenuBarBuilder

from typing import (Any, Dict, Iterable, Iterator, List, Optional,
                    Tuple, TypeVar, Union)


class AppMenuBarBuilder(MenuBarBuilder):
    '''Menu Bar for UsdOutliner that adds saving changes and populates a tools
    menu.'''

    def __init__(self, dlg):
        super(AppMenuBarBuilder, self).__init__(dlg)
        self.editTargetOriginalContents = \
            {self.GetId(dlg.editTarget): self._GetDiskContents(dlg.editTarget)}
        dlg.editTargetChanged.connect(self.EditTargetChanged)

    def AddMenus(self):
        self.AddMenu('file', '&File')
        self.AddMenu('tools', '&Tools')

    def PopulateMenus(self):
        fileMenu = self.GetMenu('file')
        saveAction = fileMenu.addAction('Save Current Edit Layer')
        saveAction.triggered.connect(self.SaveEditLayer)
        toolsMenu = self.GetMenu('tools')
        a = toolsMenu.addAction('Show Current Layer Text')
        a.triggered.connect(self.dlg.ShowEditTargetLayerText)
        a = toolsMenu.addAction('Change Edit Target')
        a.triggered.connect(self.dlg.ChangeEditTarget)
        a = toolsMenu.addAction('Edit Variants')
        a.triggered.connect(self.dlg.ShowVariantEditor)

    def _GetDiskContents(self, layer):
        '''Fetch the usd layer's contents on disk.'''
        # with USD Issue #253 solved, we can do a cheaper check of just
        # comparing time stamps and getting contents only if needed.

        if not layer.realPath:
            # New() or anonymous layer that cant be loaded from disk.
            return None

        currentContents = layer.ExportToString()
        # fetch on disk contents for comparison
        layer.Reload()
        diskContents = layer.ExportToString()
        # but then restore users edits
        if diskContents != currentContents:
            layer.ImportFromString(currentContents)
        # reset stage to avoid any problems with references to stale prims
        self.dlg.dataModel.ResetStage()
        return diskContents

    def _CheckOriginalContents(self, editLayer):
        import difflib

        diskContents = self._GetDiskContents(editLayer)
        originalContents = self.GetOriginalContents(editLayer)
        if originalContents and originalContents != diskContents:
            diff = difflib.unified_diff(originalContents.split('\n'),
                                        diskContents.split('\n'),
                                        fromfile="original",
                                        tofile="on disk",
                                        n=10)
            dlg = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning,
                                        'Contents changed!',
                                        'The contents on disk have changed '
                                        'since your began editing them. Save '
                                        'Anyway and risk overwriting changes?',
                                        buttons=(QtWidgets.QMessageBox.Cancel |
                                                 QtWidgets.QMessageBox.Yes),
                                        detailedText='\n'.join(diff))
            if dlg.exec_() != QtWidgets.QMessageBox.Yes:
                return False
        return True

    def SaveEditLayer(self):
        '''
        Save the current edit target to the appropriate place. 
        '''
        editTarget = self.dlg.editTarget
        if not self.dlg.editTarget.dirty:
            print 'Nothing to save'
            return
        if not self._CheckOriginalContents(editTarget):
            return

        self._SaveLayer(editTarget)

    def _SaveLayer(self, layer):
        layer.Save()
        self.editTargetOriginalContents[self.GetId(layer)] = \
            layer.ExportToString()

    def EditTargetChanged(self, layer):
        self.editTargetOriginalContents.setdefault(self.GetId(layer),
                                                   layer.ExportToString())

    def GetId(self, layer):
        '''Overrideable way to get the unique key used to store the original 
        contents of a layer'''
        return layer.identifier

    def GetOriginalContents(self, layer):
        return self.editTargetOriginalContents[self.GetId(layer)]

    def SaveOriginalContents(self, layer, contents=None):
        if not contents:
            contents = layer.ExportToString()
        self.editTargetOriginalContents[self.GetId(layer)] = contents


class UsdOutliner(QtWidgets.QDialog):
    # emitted with the new edit layer when the edit target is changed
    editTargetChanged = QtCore.Signal(Sdf.Layer)

    def __init__(self, stage, contextMenuBuilder=None, menuBarBuilder=None,
                 parent=None):
        '''
        Parameters
        ----------
        stage : Usd.Stage
        contextMenuBuilder : Optional[Type[ContextMenuBuilder]]
        parent : Optional[QtGui.QWidget]
        '''
        assert isinstance(stage, Usd.Stage), 'A Stage instance is required'
        super(UsdOutliner, self).__init__(parent=parent)

        self.stage = stage
        self.dataModel = self._GetModel()

        # instances of child dialogs
        self.layerTextDialogs = {}
        self.editTargetDlg = None
        self.variantEditorDlg = None

        # Widget and other Qt setup
        self.setModal(False)
        self.UpdateTitle()

        # populate menu bar
        if menuBarBuilder is None:
            menuBarBuilder = AppMenuBarBuilder
        self.menuBarBuilder = menuBarBuilder(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self.menuBarBuilder._menuBar)
        view = self._GetView(self.dataModel, contextMenuBuilder)
        delegate = OutlinerViewDelegate(self.editTarget,
                                        parent=self)
        self.editTargetChanged.connect(delegate.SetActiveLayer)
        self.editTargetChanged.connect(self.dataModel.ActiveLayerChanged)
        view.setItemDelegate(delegate)
        layout.addWidget(view)

        view.setColumnWidth(0, 360)
        self.view = view
        self.resize(900, 600)

    @property
    def editTarget(self):
        return self.stage.GetEditTarget().GetLayer()

    def _GetModel(self):
        '''
        Get the model for the outliner

        Returns
        -------
        QtCore.QAbstractItemModel
        '''
        return OutlinerStageModel(self.stage, parent=self)

    def _GetView(self, model, contextMenuBuilder):
        '''
        Get the view for the outliner

        Parameters
        ----------
        model : QtCore.QAbstractItemModel
        contextMenuBuilder : Optional[Type[ContextMenuBuilder]]

        Returns
        -------
        QtWidgets.QTreeView
        '''
        return OutlinerTreeView(model,
                                contextMenuBuilder=contextMenuBuilder,
                                parent=self)

    def UpdateTitle(self, identifier=None):
        '''
        Parameters
        ----------
        identifier : Optional[str]
            If not provided, acquired from the curent edit target
        '''
        if not identifier:
            identifier = self.editTarget.identifier
        self.setWindowTitle('Outliner - %s' % identifier)

    def UpdateEditTarget(self, layer):
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        '''
        currentLayer = self.stage.GetEditTarget().GetLayer()
        if layer == currentLayer or not layer.permissionToEdit:
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

        self.stage.SetEditTarget(layer)
        self.editTargetChanged.emit(layer)
        self.UpdateTitle()

    def ShowEditTargetLayerText(self, layer=None):
        # only allow one window per layer
        # may need to hook this bookkeeping up to hideEvent
        self.layerTextDialogs = \
            dict(((lyr, dlg)
                  for lyr, dlg in self.layerTextDialogs.iteritems()
                  if dlg.isVisible()))
        if not isinstance(layer, Sdf.Layer):
            layer = self.stage.GetEditTarget().GetLayer()
        try:
            dlg = self.layerTextDialogs[layer]
        except KeyError:
            dlg = LayerTextViewDialog(layer, parent=self)
            dlg.layerEdited.connect(self.dataModel.ResetStage)
            self.layerTextDialogs[layer] = dlg
        dlg.Refresh()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def ChangeEditTarget(self):
        # only allow one window
        if not self.editTargetDlg:
            dlg = SubLayerDialog(self.stage, parent=self)
            dlg.view.GetSignal('editTargetChanged').connect(self.UpdateEditTarget)
            dlg.view.GetSignal('showLayerContents').connect(self.ShowEditTargetLayerText)
            dlg.view.GetSignal('openLayer').connect(self.OpenLayerInOutliner)
            self.editTargetDlg = dlg
        self.editTargetDlg.show()
        self.editTargetDlg.raise_()
        self.editTargetDlg.activateWindow()

    def ShowVariantEditor(self):
        # only allow one window
        if not self.variantEditorDlg:
            dlg = VariantEditorDialog(self.stage,
                                      self.view.SelectedPrims(),
                                      parent=self)
            self.view.GetSignal('primSelectionChanged').connect(dlg.dataModel.PrimSelectionChanged)
            self.editTargetChanged.connect(dlg.dataModel.EditTargetChanged)
            self.variantEditorDlg = dlg
        self.variantEditorDlg.show()
        self.variantEditorDlg.raise_()
        self.variantEditorDlg.activateWindow()
        self.dataModel.ResetStage()

    @classmethod
    def FromUsdFile(cls, usdFile, parent=None):
        with Usd.StageCacheContext(Usd.BlockStageCaches):
            stage = Usd.Stage.Open(usdFile, Usd.Stage.LoadNone)
            assert stage
            stage.SetEditTarget(stage.GetSessionLayer())
        return cls(stage, parent=parent)

    def OpenLayerInOutliner(self, layer):
        dlg = self.FromUsdFile(layer.identifier)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        dlg.exec_()


if __name__ == '__main__':
    # simple test
    import sys

    app = QtWidgets.QApplication(sys.argv)

    usdFileArg = sys.argv[1]

    dialog = UsdOutliner.FromUsdFile(usdFileArg)
    dialog.show()
    dialog.exec_()
