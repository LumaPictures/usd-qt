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
                            OutlinerStageModel, ActivatePrim, SelectVariants,
                            RemovePrim)
from usdQt.layers import LayerTextViewDialog, SubLayerDialog
from usdQt.variantSets import VariantEditorDialog
from usdQt.common import MenuBarBuilder, ContextMenuAction, MenuAction, \
    MenuSeparator, UsdQtUtilities

from typing import (Any, Dict, Iterable, Iterator, List, Optional,
                    Tuple, TypeVar, Union)


class OutlinerUserRole(object):
    '''
    Base implementation for a customized outliner app that manages which
    menu actions are available.

    Views and dialogs will support getting their menu actions from calling one
    of these methods with themselves as an argument.
    '''
    @classmethod
    def OutlinerViewContextActions(cls, view):
        '''
        Parameters
        ----------
        view : OutlinerTreeView

        Returns
        -------
        List[ContextMenuAction]
        '''
        return [ActivatePrim(),
                SelectVariants(),
                MenuSeparator(),
                RemovePrim()]

    @classmethod
    def MenuBarMenus(cls, dlg):
        '''
        Parameters
        ----------
        dlg : UsdOutliner

        Returns
        -------
        List[Tuple[str, str]]
        '''
        return [('file', '&File'),
                ('tools', '&Tools')]

    @classmethod
    def MenuBarActions(cls, dlg):
        '''
        Parameters
        ----------
        dlg : UsdOutliner

        Returns
        -------
        List[MenuAction]
        '''
        saveState = SaveState(dlg)

        return {'file': [SaveEditLayer(saveState)],
                'tools': [ShowEditTargetLayerText(),
                          ChangeEditTarget(),
                          ShowVariantEditor()]}


class SaveState(object):
    '''State tracker for layer contents in an outliner app'''

    def __init__(self, dlg):
        self.dlg = dlg
        self.editTargetOriginalContents = \
            {self.GetId(dlg.editTarget): self._GetDiskContents(dlg.editTarget)}
        dlg.editTargetChanged.connect(self.EditTargetChanged)

    def EditTargetChanged(self, layer):
        self.editTargetOriginalContents.setdefault(self.GetId(layer),
                                                   layer.ExportToString())

    def GetOriginalContents(self, layer):
        return self.editTargetOriginalContents[self.GetId(layer)]

    def SaveOriginalContents(self, layer, contents=None):
        if not contents:
            contents = layer.ExportToString()
        self.editTargetOriginalContents[self.GetId(layer)] = contents

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

    def CheckOriginalContents(self, editLayer):
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
                                        'since your began editing them. '
                                        '\n\t%s\n '
                                        'Save Anyway and risk overwriting '
                                        'changes?' % editLayer.identifier,
                                        buttons=(QtWidgets.QMessageBox.Cancel |
                                                 QtWidgets.QMessageBox.Yes),
                                        detailedText='\n'.join(diff))
            if dlg.exec_() != QtWidgets.QMessageBox.Yes:
                return False
        return True

    def GetId(self, layer):
        return UsdQtUtilities.exec_('GetId', layer)


class SaveEditLayer(MenuAction):

    def __init__(self, state, label=None, enable=None, func=None):
        super(SaveEditLayer, self).__init__(label=label, enable=enable, func=None)
        self.state = state

    def label(self, builder):
        return 'Save Current Edit Layer'

    def do(self, builder):
        '''
        Save the current edit target to the appropriate place. 
        '''
        editTarget = builder.dlg.editTarget
        if not builder.dlg.editTarget.dirty:
            print 'Nothing to save'
            return
        if not self.state.CheckOriginalContents(editTarget):
            return

        self._SaveLayer(editTarget)

    def _SaveLayer(self, layer):
        layer.Save()
        self.state.SaveOriginalContents(layer)


class ShowEditTargetLayerText(MenuAction):
    def label(self, builder):
        return 'Show Current Layer Text'

    def do(self, builder):
        return builder.dlg.ShowEditTargetLayerText()


class ChangeEditTarget(MenuAction):
    def label(self, builder):
        return 'Change Edit Target'

    def do(self, builder):
        return builder.dlg.ChangeEditTarget()


class ShowVariantEditor(MenuAction):
    def label(self, builder):
        return 'Edit Variants'

    def do(self, builder):
        return builder.dlg.ShowVariantEditor()


class UsdOutliner(QtWidgets.QDialog):
    # emitted with the new edit layer when the edit target is changed
    editTargetChanged = QtCore.Signal(Sdf.Layer)

    def __init__(self, stage, role=None, parent=None):
        '''
        Parameters
        ----------
        stage : Usd.Stage
        role : Any
            Optionally provide an object with methods for getting custom
            menu action configurations.
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

        if role is None:
            role = OutlinerUserRole
        self.role = role
        # populate menu bar
        self.menuBarBuilder = MenuBarBuilder(self,
                                             self.role.MenuBarMenus,
                                             self.role.MenuBarActions)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self.menuBarBuilder._menuBar)
        view = self._GetView(self.dataModel, self.role)
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

    def _GetView(self, model, role):
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
        return OutlinerTreeView(
            model,
            contextMenuActions=role.OutlinerViewContextActions,
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

    def SetNewStage(self, stage):
        '''Reset the stage for this dlg'''
        self.stage = stage
        self.dataModel = self._GetModel()

        self.view.setModel(self.dataModel)
        self.editTargetChanged.emit(self.editTarget)
        self.view.reset()

        # close instances of child dialogs
        def close(dlg):
            if dlg:
                dlg.close()

        for layerTextDlg in self.layerTextDialogs:
            close(layerTextDlg)
        self.layerTextDialogs = {}
        close(self.editTargetDlg)
        self.editTargetDlg = None
        close(self.variantEditorDlg)
        self.variantEditorDlg = None

        self.UpdateTitle()

if __name__ == '__main__':
    # simple test
    import sys

    app = QtWidgets.QApplication(sys.argv)

    usdFileArg = sys.argv[1]

    dialog = UsdOutliner.FromUsdFile(usdFileArg)
    dialog.show()
    dialog.exec_()
