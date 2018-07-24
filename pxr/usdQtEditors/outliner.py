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

from functools import partial

import usdlib.utils
import usdlib.variants
from pxr import Sdf, Usd
from pxr.UsdQt.common import DARK_ORANGE, MenuAction, MenuSeparator, \
    MenuBuilder, MenuBarBuilder, UsdQtUtilities
from pxr.UsdQt.hierarchyModel import HierarchyBaseModel
from pxr.UsdQt.layers import LayerTextViewDialog, SubLayerDialog
from pxr.UsdQt.variantSets import VariantEditorDialog
from typing import NamedTuple, Optional

from ._Qt import QtCore, QtGui, QtWidgets

if False:
    from typing import *


NO_VARIANT_SELECTION = '<No Variant Selected>'


OutlinerContext = NamedTuple('OutlinerContext',
                             [('outliner', QtWidgets.QWidget),
                              ('stage', Usd.Stage),
                              ('selectedPrim', Optional[Usd.Prim]),
                              ('selectedPrims', List[Usd.Prim])])


class ActivatePrims(MenuAction):
    defaultText = 'Activate'

    def Update(self, action, context):
        action.setEnabled(bool(context.selectedPrims))

    def Do(self, context):
        with Sdf.ChangeBlock():
            for prim in context.selectedPrims:
                prim.SetActive(True)


class DeactivatePrims(MenuAction):
    defaultText = 'Dectivate'

    def Update(self, action, context):
        action.setEnabled(bool(context.selectedPrims))

    def Do(self, context):
        with Sdf.ChangeBlock():
            for prim in context.selectedPrims:
                prim.SetActive(False)


class AddTransform(MenuAction):
    defaultText = 'Add Transform...'

    def Update(self, action, context):
        action.setEnabled(bool(context.selectedPrim))

    def Do(self, context):
        # TODO: Right now this only produces Xforms. May need to support the
        # ability to specify types for new prims eventually.
        name, _ = QtWidgets.QInputDialog.getText(context.outliner,
                                                 'Add New Transform',
                                                 'Transform Name:')
        if not name:
            return
        if not Sdf.Path.IsValidIdentifier(name):
            QtWidgets.QMessageBox.warning(context.outliner,
                                          'Invalid Prim Name',
                                          '{0!r} is not a valid prim '
                                          'name'.format(name))
            return

        newPath = context.selectedPrim.GetPath().AppendChild(name)
        if context.stage.GetEditTarget().GetPrimSpecForScenePath(newPath):
            QtWidgets.QMessageBox.warning(context.outliner,
                                          'Duplicate Prim Path',
                                          'A prim already exists at '
                                          '{0!r}'.format(newPath))
            return
        context.stage.DefinePrim(newPath, 'Xform')


class RemovePrim(MenuAction):
    def Update(self, action, context):
        prims = context.selectedPrims
        action.setEnabled(bool(prims))
        text = 'Remove Prims' if len(prims) > 1 else 'Remove Prim'
        editTarget = context.stage.GetEditTarget()
        for prim in prims:
            spec = editTarget.GetPrimSpecForScenePath(prim.GetPath())
            if spec and spec.specifier == Sdf.SpecifierOver:
                text = 'Remove Prim Edits'
                break
        action.setText(text)

    def Do(self, context):
        ask = True
        for prim in context.selectedPrims:
            primPath = prim.GetPath()
            if ask:
                answer = QtWidgets.QMessageBox.question(
                    context.outliner,
                    'Confirm Prim Removal',
                    'Remove prim (and any children) at {0}?'.format(primPath),
                    buttons=(QtWidgets.QMessageBox.Yes |
                             QtWidgets.QMessageBox.Cancel |
                             QtWidgets.QMessageBox.YesToAll),
                    defaultButton=QtWidgets.QMessageBox.Yes)
                if answer == QtWidgets.QMessageBox.Cancel:
                    return
                elif answer == QtWidgets.QMessageBox.YesToAll:
                    ask = False
            context.stage.RemovePrim(primPath)


class SelectVariants(MenuAction):
    @staticmethod
    def _ApplyVariant(prim, variantSetName, variantValue):
        if prim:
            variantSet = prim.GetVariantSet(variantSetName)
            if variantValue == NO_VARIANT_SELECTION:
                variantSet.ClearVariantSelection()
            else:
                variantSet.SetVariantSelection(variantValue)

    def Build(self, context):
        prims = context.selectedPrims
        if len(prims) != 1:
            return
        prim = prims[0]
        if not prim.HasVariantSets():
            return

        menu = QtWidgets.QMenu('Variants', context.outliner)
        for setName, currentValue in usdlib.variants.getPrimVariants(prim):
            setMenu = menu.addMenu(setName)
            variantSet = prim.GetVariantSet(setName)
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
                a.triggered.connect(partial(self._ApplyVariant,
                                            prim, setName, setValue))
        return menu.menuAction()


class AddReference(MenuAction):
    defaultText = 'Add Reference...'

    def Update(self, action, context):
        action.setEnabled(bool(context.selectedPrim))

    def Do(self, context):
        refPath = UsdQtUtilities.exec_('GetReferencePath', stage=context.stage)
        if refPath:
            stage = context.stage
            prim = context.selectedPrim
            editLayer = stage.GetEditTarget().GetLayer()
            if not stage.HasLocalLayer(editLayer):
                # We use a temporary stage here to get around the local layer
                # restriction for variant edit contexts.
                editTargetStage = Usd.Stage.Open(editLayer)
                # this assumes prim path is the same in edit target
                prim = editTargetStage.GetPrimAtPath(prim.GetPath())

            prim.GetReferences().SetReferences([Sdf.Reference(refPath)])


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
        self.dlg._dataModel.ResetStage()
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
            dlg = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                'Layer Contents Changed!',
                'Layer contents have changed on disk since you started '
                'editing.\n    %s\n'
                'Save anyway and risk overwriting changes?' % editLayer.identifier,
                buttons=QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes,
                detailedText='\n'.join(diff))
            if dlg.exec_() != QtWidgets.QMessageBox.Yes:
                return False
        return True

    def GetId(self, layer):
        return UsdQtUtilities.exec_('GetId', layer)


class SaveEditLayer(MenuAction):
    __slots__ = ('state',)

    defaultText = 'Save Current Edit Layer'

    def __init__(self, state):
        self.state = state

    def Do(self, context):
        '''
        Save the current edit target to the appropriate place.
        '''
        editTarget = context.stage.GetEditTarget().GetLayer()
        if not editTarget.dirty:
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

    def __init__(self, contextMenuActions=None, contextProvider=None,
                 parent=None):
        super(OutlinerTreeView, self).__init__(
            contextMenuActions=contextMenuActions,
            contextProvider=contextProvider,
            parent=parent)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.ExtendedSelection)
        self.setEditTriggers(self.CurrentChanged | self.SelectedClicked)

        self.setUniformRowHeights(True)
        self.header().setStretchLastSection(True)

        # This can't be a one-liner because of a PySide refcount bug.
        selectionModel = self.selectionModel()
        selectionModel.selectionChanged.connect(self._SelectionChanged)

    # Custom methods -----------------------------------------------------------
    @QtCore.Slot(QtCore.QItemSelection, QtCore.QItemSelection)
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


class OutlinerRole(object):
    '''Helper which provides standard hooks for defining the context menu
    actions and menu bar menus that should be added to an outliner.
    '''
    @classmethod
    def GetContextMenuActions(cls, outliner):
        '''
        Parameters
        ----------
        outliner : UsdOutliner

        Returns
        -------
        List[Union[MenuAction, Type[MenuAction]]]
        '''
        return [ActivatePrims, DeactivatePrims, SelectVariants, MenuSeparator,
                RemovePrim]

    @classmethod
    def GetMenuBarMenuBuilders(cls, outliner):
        '''
        Parameters
        ----------
        outliner : UsdOutliner

        Returns
        -------
        List[MenuBuilder]
        '''
        saveState = SaveState(outliner)
        return [MenuBuilder('&File', [SaveEditLayer(saveState)]),
                MenuBuilder('&Tools', [ShowEditTargetLayerText,
                                       ChangeEditTarget, ShowVariantEditor])]


class UsdOutliner(QtWidgets.QDialog):
    '''UsdStage editing application which displays the hierarchy of a stage.'''
    # emitted with the new edit layer when the edit target is changed
    editTargetChanged = QtCore.Signal(Sdf.Layer)

    def __init__(self, stage, role=None, parent=None):
        '''
        Parameters
        ----------
        stage : Usd.Stage
        role : Optional[Union[Type[OutlinerRole], OutlinerRole]]
        parent : Optional[QtGui.QWidget]
        '''
        assert isinstance(stage, Usd.Stage), 'A Stage instance is required'
        super(UsdOutliner, self).__init__(parent=parent)

        self.stage = stage
        self._dataModel = HierarchyBaseModel(stage=stage, parent=self)

        # instances of child dialogs
        self.layerTextDialogs = {}
        self.editTargetDlg = None
        self.variantEditorDlg = None

        # Widget and other Qt setup
        self.setModal(False)
        self.UpdateTitle()

        if role is None:
            role = OutlinerRole
        self.role = role

        self.menuBarBuilder = MenuBarBuilder(
            self,
            menuBuilders=role.GetMenuBarMenuBuilders(),
            parent=self)

        view = self._CreateView(stage, self.role)
        view.setColumnWidth(0, 360)
        view.setModel(self._dataModel)
        self.view = view

        delegate = OutlinerViewDelegate(self.editTarget, parent=view)
        view.setItemDelegate(delegate)
        self.editTargetChanged.connect(delegate.SetActiveLayer)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self.menuBarBuilder.menuBar)
        layout.addWidget(view)

        self.resize(900, 600)

    def _CreateView(self, stage, role):
        '''Create the hierarchy view for the outliner.

        This is provided as a convenience for subclass implementations.

        Parameters
        ----------
        stage : Usd.Stage
        role : Union[Type[OutlinerRole], OutlinerRole]

        Returns
        -------
        QtWidgets.QAbstractItemView
        '''
        return OutlinerTreeView(contextMenuActions=role.GetContextMenuActions(),
                                contextProvider=self, parent=self)

    def GetMenuContext(self):
        selectedPrims = self.view.SelectedPrims()
        return OutlinerContext(outliner=self, stage=self.stage,
                               selectedPrim=selectedPrims[0],
                               selectedPrims=selectedPrims)

    def ResetStage(self, stage=None):
        if stage is None:
            stage = self.stage
        self._dataModel.ResetStage(stage)

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
