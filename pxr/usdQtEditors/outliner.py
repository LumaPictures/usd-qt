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

import usdlib.utils
import usdlib.variants
from pxr import Sdf, Usd
from pxr.UsdQt.common import DARK_ORANGE, ContextMenuAction, ContextMenuMixin, \
    MenuAction, MenuBarBuilder, MenuSeparator, UsdQtUtilities
from pxr.UsdQt.hierarchyModel import HierarchyBaseModel
from pxr.UsdQt.layers import LayerTextViewDialog, SubLayerDialog
from pxr.UsdQt.variantSets import VariantEditorDialog
from typing import NamedTuple, Optional

from ._Qt import QtCore, QtGui, QtWidgets

if False:
    from typing import *


NO_VARIANT_SELECTION = '<No Variant Selected>'

Selection = NamedTuple('Selection',
                       [('index', Optional[QtCore.QModelIndex]),
                        ('prim', Optional[Usd.Prim])])


class ActivatePrim(ContextMenuAction):
    def label(self, builder, selection):
        anyActive = any((s.prim.IsActive() for s in selection))
        return 'Deactivate' if anyActive else 'Activate'

    def do(self, builder, multiSelection):
        print 'doing!'
        anyActive = any((s.prim.IsActive() for s in multiSelection))
        for selection in multiSelection:
            if not selection.prim.IsValid():
                continue
            if selection.prim.IsActive() == anyActive:
                builder.model.TogglePrimActive(selection.index,
                                               selection.prim,
                                               item=selection.item)


class AddNewPrim(ContextMenuAction):
    def label(self, builder, selection):
        return 'Add Transform...'

    def do(self, builder, selection):
        # TODO: Right now, this doesn't override the primType passed to the
        # model's AddNewPrim method, so this only produces Xforms. May need to
        # support the ability to specify types for new prims eventually.
        name, _ = QtWidgets.QInputDialog.getText(builder.view,
                                                 'Enter Prim Name',
                                                 'Name for the new transform:')
        if not name:
            return
        newPath = selection.prim.GetPath().AppendChild(name)
        if builder.model.GetPrimSpecAtEditTarget(newPath):
            QtWidgets.QMessageBox.warning(builder.view,
                                          'Duplicate Prim Path',
                                          'A prim already exists at '
                                          '{0}'.format(newPath))
            return
        builder.model.AddNewPrim(selection.index,
                                 selection.prim,
                                 name,
                                 item=selection.item)


class RemovePrim(ContextMenuAction):
    def label(self, builder, selections):
        label = 'Remove Prims' if len(selections) > 1 else 'Remove Prim'
        for selection in selections:
            spec = builder.model.GetPrimSpecAtEditTarget(selection.prim)
            if spec:
                if spec.specifier == Sdf.SpecifierOver:
                    return 'Remove Prim Edits'
        return label

    def enable(self, builder, selections):
        for selection in selections:
            spec = builder.model.GetPrimSpecAtEditTarget(selection.prim)
            if spec:
                if (spec.specifier == Sdf.SpecifierDef or
                        spec.specifier == Sdf.SpecifierOver):
                    return True
        return False

    def do(self, builder, multiSelection):
        ask = True
        for selection in multiSelection:
            if ask:
                answer = QtWidgets.QMessageBox.question(
                    builder.view, 'Confirm Prim Removal',
                    'Remove prim (and any children) at {0}?'.format(
                        selection.prim.GetPath()),
                    buttons=(QtWidgets.QMessageBox.Yes |
                             QtWidgets.QMessageBox.Cancel |
                             QtWidgets.QMessageBox.YesToAll),
                    defaultButton=QtWidgets.QMessageBox.Yes)
                if answer == QtWidgets.QMessageBox.Cancel:
                    return
                elif answer == QtWidgets.QMessageBox.YesToAll:
                    ask = False
            builder.model.RemovePrimFromCurrentLayer(selection.index,
                                                     selection.prim,
                                                     item=selection.item)


class SelectVariants(ContextMenuAction):

    def Build(self, builder, menu, selections):
        selection = selections[0]
        if selection.prim.HasVariantSets():
            variantMenu = menu.addMenu('Variants')
            for setName, currentValue in usdlib.variants.getPrimVariants(
                    selection.prim):
                setMenu = variantMenu.addMenu(setName)
                variantSet = selection.prim.GetVariantSet(setName)
                for setValue in [NO_VARIANT_SELECTION] + \
                        variantSet.GetVariantNames():
                    a = setMenu.addAction(setValue)
                    a.setCheckable(True)
                    if setValue == currentValue or \
                            (setValue == NO_VARIANT_SELECTION
                             and currentValue == ''):
                        a.setChecked(True)

                    # Note: This is currently only valid for PySide. PyQt
                    # always passes the action's `checked` value.
                    a.triggered.connect(
                        lambda n=setName, v=setValue:
                            builder.model.PrimVariantChanged(
                                selection.index, n, v, item=selection.item))

    def shouldShow(self, builder, selections):
        return len(selections) == 1


class AddReference(ContextMenuAction):
    def label(self, builder, selections):
        return 'Add Reference...'

    def _GetNewReferencePath(self):
        return UsdQtUtilities.exec_('GetReferencePath',
                                    stage=self.model.stage)

    def do(self, builder, selection):
        '''Add a reference directly to an existing prim'''
        refPath = self._GetNewReferencePath()
        builder.model.AddNewReference(selection.index, selection.prim, refPath)


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


class OutlinerTreeView(ContextMenuMixin, QtWidgets.QTreeView):
    # Emitted with lists of selected and deselected prims
    primSelectionChanged = QtCore.Signal(list, list)

    def __init__(self, stage=None, contextMenuActions=None,
                 contextMenuBuilder=None, parent=None):
        '''
        Parameters
        ----------
        stage : Optional[Usd.Stage]
        contextMenuActions : Optional[Callable[[OutlinerTreeView], List[ContextMenuAction]]]
        contextMenuBuilder : Optional[Type[ContextMenuBuilder]]
        parent : Optional[QtGui.QWidget]
        '''
        super(OutlinerTreeView, self).__init__(
            parent=parent,
            contextMenuBuilder=contextMenuBuilder,
            contextMenuActions=contextMenuActions)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.ExtendedSelection)
        self.setEditTriggers(self.CurrentChanged | self.SelectedClicked)

        self.setUniformRowHeights(True)
        self.header().setStretchLastSection(True)

        self._dataModel = HierarchyBaseModel(stage=stage, parent=self)
        self.setModel(self._dataModel)

        # This can't be a one-liner because of a PySide refcount bug.
        selectionModel = self.selectionModel()
        selectionModel.selectionChanged.connect(self._SelectionChanged)

    # Custom methods -----------------------------------------------------------
    def ResetStage(self, stage):
        self._dataModel.ResetStage(stage)

    def _SelectionChanged(self, selected, deselected):
        '''Connected to selectionChanged'''
        model = self._dataModel
        def toPrims(qSelection):
            return [model._GetPrimForIndex(index)
                    for index in qSelection.indexes() if index.column() == 0]
        self.primSelectionChanged.emit(toPrims(selected), toPrims(deselected))

    def SelectedPrims(self):
        '''
        Returns
        -------
        List[Usd.Prim]
        '''
        model = self._dataModel
        result = []
        for index in self.selectionModel().selectedRows():
            prim = model._GetPrimForIndex(index)
            if prim:
                result.append(prim)
        return result

    def GetSelection(self):
        '''
        Returns
        -------
        List[Selection]
        '''
        model = self._dataModel
        indexes = self.selectionModel().selectedRows()
        result = []
        for index in indexes:
            prim = model._GetPrimForIndex(index)
            if prim:
                result.append(Selection(index, prim))
        return result


class OutlinerViewDelegate(QtWidgets.QStyledItemDelegate):
    '''
    Item delegate class assigned to an ``OutlinerTreeView``.
    '''

    def __init__(self, activeLayer, parent=None):
        '''
        Parameters
        ----------
        activeLayer : Sdf.Layer
        parent : Optional[QtGui.QWidget]
        '''
        super(OutlinerViewDelegate, self).__init__(parent=parent)
        self._activeLayer = activeLayer

    # Qt methods ---------------------------------------------------------------
    def paint(self, painter, options, modelIndex):
        if modelIndex.isValid():
            proxy = modelIndex.internalPointer()
            if not proxy.expired:
                prim = proxy.GetPrim()
                palette = options.palette
                textColor = palette.color(QtGui.QPalette.Text)
                if prim.HasVariantSets():
                    textColor = DARK_ORANGE
                if not prim.IsActive():
                    textColor.setAlphaF(.5)
                spec = self._activeLayer.GetPrimAtPath(prim.GetPrimPath())
                if spec:
                    specifier = spec.specifier
                    if specifier == Sdf.SpecifierDef:
                        options.font.setBold(True)
                    elif specifier == Sdf.SpecifierOver:
                        options.font.setItalic(True)
                palette.setColor(QtGui.QPalette.Text, textColor)

        return QtWidgets.QStyledItemDelegate.paint(self, painter, options,
                                                   modelIndex)

    # Custom methods -----------------------------------------------------------
    def SetActiveLayer(self, layer):
        '''
        Parameters
        ----------
        layer : Sdf.Layer
        '''
        self._activeLayer = layer


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


class UsdOutliner(QtWidgets.QDialog):
    '''UsdStage editing application which displays the hierarchy of a stage.'''
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

        view = self._GetView(stage, self.role)
        view.setColumnWidth(0, 360)
        self.view = view

        delegate = OutlinerViewDelegate(self.editTarget, parent=view)
        view.setItemDelegate(delegate)
        self.editTargetChanged.connect(delegate.SetActiveLayer)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self.menuBarBuilder._menuBar)
        layout.addWidget(view)

        self.resize(900, 600)

    @property
    def editTarget(self):
        return self.stage.GetEditTarget().GetLayer()

    def _GetView(self, stage, role):
        '''
        Get the view for the outliner

        Parameters
        ----------
        stage : Usd.Stage
        role : Type[OutlinerUserRole]

        Returns
        -------
        QtWidgets.QTreeView
        '''
        return OutlinerTreeView(
            stage=stage,
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
        '''Reset the stage for this dlg and its views'''
        self.stage = stage

        self.view.ResetStage(stage)
        self.editTargetChanged.emit(self.editTarget)
        self.view.reset()

        # close instances of child dialogs
        def close(dlg):
            if dlg:
                dlg.close()

        for layerTextDlg in self.layerTextDialogs.values():
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
