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

"""
An extensible Usd stage outliner.
"""
from __future__ import absolute_import

from collections import namedtuple
from functools import partial

from ._Qt import QtCore, QtGui, QtWidgets

from pxr import Sdf, Tf, Usd
from pxr.UsdQt.hierarchyModel import HierarchyBaseModel
from pxr.UsdQt.hooks import UsdQtHooks
from pxr.UsdQt.layerModel import LayerStackBaseModel
from pxr.UsdQt.qtUtils import DARK_ORANGE, MenuAction, MenuSeparator, \
    MenuBuilder, ContextMenuMixin, MenuBarBuilder, CopyToClipboard
from pxr.UsdQt.usdUtils import GetPrimVariants
from pxr.UsdQtEditors.layerTextEditor import LayerTextEditorDialog

if False:
    from typing import *
    ContextProvider = Any


NO_VARIANT_SELECTION = '<No Variant Selected>'

NULL_INDEX = QtCore.QModelIndex()

FONT_BOLD = QtGui.QFont()
FONT_BOLD.setBold(True)


class LayerStackModel(LayerStackBaseModel):
    """Layer stack model for the outliner's edit target selection dialog."""
    headerLabels = ('Name', 'Path', 'Resolved Path')

    def __init__(self, stage, includeSessionLayers=True, parent=None):
        # type: (Usd.Stage, bool, Optional[QtCore.QObject]) -> None
        """
        Parameters
        ----------
        stage : Usd.Stage
        includeSessionLayers : bool
        parent : Optional[QtCore.QObject]
        """
        super(LayerStackModel, self).__init__(
            stage,
            includeSessionLayers=includeSessionLayers,
            parent=parent)
        self._listener = Tf.Notice.Register(Usd.Notice.StageEditTargetChanged,
                                            self._OnEditTargetChanged, stage)

    # Qt methods ---------------------------------------------------------------
    def columnCount(self, parentIndex):
        return 3

    def flags(self, modelIndex):
        if modelIndex.isValid():
            item = modelIndex.internalPointer()
            if item.layer.permissionToEdit:
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        return QtCore.Qt.NoItemFlags

    def data(self, modelIndex, role=QtCore.Qt.DisplayRole):
        if not modelIndex.isValid():
            return
        if role == QtCore.Qt.DisplayRole:
            column = modelIndex.column()
            item = modelIndex.internalPointer()
            if column == 0:
                if item.layer.anonymous:
                    return '<anonymous>'
                return item.layer.identifier.split('/')[-1]
            elif column == 1:
                return item.layer.identifier
            elif column == 2:
                return item.layer.realPath
        elif role == QtCore.Qt.FontRole:
            item = modelIndex.internalPointer()
            if item.layer == self._stage.GetEditTarget().GetLayer():
                return FONT_BOLD

    # Custom Methods -----------------------------------------------------------
    def ResetStage(self, stage):
        # type: (Usd.Stage) -> None
        """
        Parameters
        ----------
        stage : Usd.Stage
        """
        super(LayerStackModel, self).ResetStage(stage)
        if self._stage:
            self._listener = Tf.Notice.Register(Usd.Notice.StageEditTargetChanged,
                                                self._OnEditTargetChanged, stage)
        else:
            self._listener = None

    def _OnEditTargetChanged(self, notice, stage):
        self.dataChanged.emit(NULL_INDEX, NULL_INDEX)


LayerStackDialogContext = namedtuple('LayerStackDialogContext',
                                     ['qtParent', 'layerDialog', 'stage',
                                      'selectedLayer', 'editTargetLayer'])


class ShowLayerText(MenuAction):
    defaultText = 'Show Layer Text'

    def Do(self):
        context = self.GetCurrentContext()
        if not context.selectedLayer:
            return
        qtParent = context.qtParent
        if qtParent and hasattr(qtParent, 'ShowLayerTextDialog'):
            # a parent dialog is in charge of tracking layers
            qtParent.ShowLayerTextDialog(context.selectedLayer)
        else:
            # use global shared instance registry
            dialog = LayerTextEditorDialog.GetSharedInstance(
                context.selectedLayer,
                parent=qtParent or context.layerDialog)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()


class CopyLayerPath(MenuAction):
    defaultText = 'Copy Layer Identifier'

    def Do(self):
        context = self.GetCurrentContext()
        if context.selectedLayer:
            CopyToClipboard(context.selectedLayer.identifier)


class OpenLayer(MenuAction):
    defaultText = 'Open Layer in Outliner'

    def Do(self):
        context = self.GetCurrentContext()
        if context.selectedLayer:
            # Role is currently lost
            dlg = UsdOutlinerDialog.FromUsdFile(context.selectedLayer.identifier)
            dlg.show()
            dlg.raise_()
            dlg.activateWindow()


class LayerStackTreeView(ContextMenuMixin, QtWidgets.QTreeView):
    def __init__(self, contextProvider, parent=None):
        # type: (ContextProvider, Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        contextProvider : ContextProvider
        parent : Optional[QtWidgets.QWidget]
        """
        contextMenuActions = [ShowLayerText, CopyLayerPath, OpenLayer]
        super(LayerStackTreeView, self).__init__(
            contextMenuActions=contextMenuActions,
            contextProvider=contextProvider,
            parent=parent)

    def GetSelectedLayer(self):
        # type: () -> Optional[Sdf.Layer]
        """
        Returns
        -------
        Optional[Sdf.Layer]
        """
        selectionModel = self.selectionModel()
        indexes = selectionModel.selectedRows()
        if indexes:
            index = indexes[0]
            if index.isValid():
                return index.internalPointer().layer


class EditTargetEditor(QtWidgets.QWidget):
    def __init__(self, stage, editTargetChangeCallback=None, parent=None):
        # type: (Usd.Stage, Optional[Callable[[Sdf.Layer], bool]], Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        stage : Usd.Stage
        editTargetChangeCallback : Optional[Callable[[Sdf.Layer], bool]]
            Optional validation callback that will be called with the new layer
            when the user attempts to change the current edit target (by
            double-clicking a layer). If this is provided and returns False, the
            edit target will not be changed.
        parent : Optional[QtWidgets.QWidget]
        """
        super(EditTargetEditor, self).__init__(parent=parent)
        self._stage = stage
        self._dataModel = LayerStackModel(stage, parent=self)
        self._editTargetChangeCallback = editTargetChangeCallback

        # Widget and other Qt setup
        self.view = LayerStackTreeView(self, parent=self)
        self.view.setModel(self._dataModel)
        self.view.doubleClicked.connect(self.ChangeEditTarget)
        self.view.setColumnWidth(0, 160)
        self.view.setColumnWidth(1, 300)
        self.view.setColumnWidth(2, 100)
        self.view.setExpandsOnDoubleClick(False)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self.view)
        self.view.expandAll()

    def GetMenuContext(self):
        # type: () -> LayerStackDialogContext
        """
        Returns
        -------
        LayerStackDialogContext
        """
        stage = self._stage
        return LayerStackDialogContext(
            qtParent=self.parent() or self,
            layerDialog=self,
            stage=stage,
            selectedLayer=self.view.GetSelectedLayer(),
            editTargetLayer=stage.GetEditTarget().GetLayer())

    @QtCore.Slot(QtCore.QModelIndex)
    def ChangeEditTarget(self, modelIndex):
        # type: (QtCore.QModelIndex) -> None
        """
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
        """
        if not modelIndex.isValid():
            return
        item = modelIndex.internalPointer()
        newLayer = item.layer

        if self._editTargetChangeCallback is None \
                or self._editTargetChangeCallback(newLayer):
            self._stage.SetEditTarget(newLayer)

    def ResetStage(self, stage):
        self._dataModel.ResetStage(stage)
        self._stage = stage


class EditTargetDialog(QtWidgets.QDialog):
    """Dialog for the edit target editor."""
    def __init__(self, stage, editTargetChangeCallback=None, parent=None):
        super(EditTargetDialog, self).__init__(parent=parent)
        self.setWindowTitle('Select Edit Target')
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.editor = EditTargetEditor(
            stage,
            editTargetChangeCallback=editTargetChangeCallback,
            parent=self)
        layout.addWidget(self.editor)
        self.resize(700, 200)


OutlinerContext = namedtuple('OutlinerContext',
                             ['qtParent', 'outliner', 'stage',
                              'editTargetLayer', 'selectedPrim',
                              'selectedPrims'])


class ActivatePrims(MenuAction):
    defaultText = 'Activate'

    def Update(self, action, context):
        action.setEnabled(bool(context.selectedPrims))

    def Do(self):
        context = self.GetCurrentContext()
        with Sdf.ChangeBlock():
            for prim in context.selectedPrims:
                prim.SetActive(True)


class DeactivatePrims(MenuAction):
    defaultText = 'Deactivate'

    def Update(self, action, context):
        action.setEnabled(bool(context.selectedPrims))

    def Do(self):
        context = self.GetCurrentContext()
        with Sdf.ChangeBlock():
            for prim in context.selectedPrims:
                prim.SetActive(False)


class MakeVisible(MenuAction):
    defaultText = 'Make Visible'

    def Update(self, action, context):
        action.setEnabled(bool(context.selectedPrims))

    def Do(self):
        from pxr import UsdGeom
        context = self.GetCurrentContext()
        for prim in context.selectedPrims:
            UsdGeom.Imageable(prim).MakeVisible()


class MakeInvisible(MenuAction):
    defaultText = 'Make Invisible'

    def Update(self, action, context):
        action.setEnabled(bool(context.selectedPrims))

    def Do(self):
        from pxr import UsdGeom
        context = self.GetCurrentContext()
        for prim in context.selectedPrims:
            UsdGeom.Imageable(prim).MakeInvisible()


class AddTransform(MenuAction):
    defaultText = 'Add Transform...'

    def Update(self, action, context):
        action.setEnabled(bool(context.selectedPrim))

    def Do(self):
        context = self.GetCurrentContext()
        # TODO: Right now this only produces Xforms. May need to support the
        # ability to specify types for new prims eventually.
        name, _ = QtWidgets.QInputDialog.getText(context.qtParent,
                                                 'Add New Transform',
                                                 'Transform Name:')
        if not name:
            return
        if not Sdf.Path.IsValidIdentifier(name):
            QtWidgets.QMessageBox.warning(context.qtParent,
                                          'Invalid Prim Name',
                                          '{0!r} is not a valid prim '
                                          'name'.format(name))
            return

        newPath = context.selectedPrim.GetPath().AppendChild(name)
        if context.stage.GetEditTarget().GetPrimSpecForScenePath(newPath):
            QtWidgets.QMessageBox.warning(context.qtParent,
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

    def Do(self):
        context = self.GetCurrentContext()
        ask = True
        buttons = QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel
        if len(context.selectedPrims) > 1:
            buttons |= QtWidgets.QMessageBox.YesToAll
        for prim in context.selectedPrims:
            primPath = prim.GetPath()
            if ask:
                answer = QtWidgets.QMessageBox.question(
                    context.qtParent,
                    'Confirm Prim Removal',
                    'Remove prim/prim edits (and any children) at {0}?'.format(primPath),
                    buttons=buttons,
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

        menu = QtWidgets.QMenu('Variants', context.qtParent)
        for setName, currentValue in GetPrimVariants(prim):
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
                a.triggered.connect(partial(self._ApplyVariant,
                                            prim, setName, setValue))
        return menu.menuAction()


class AddReference(MenuAction):
    defaultText = 'Add Reference...'

    def Update(self, action, context):
        context = self.GetCurrentContext()
        action.setEnabled(bool(context.selectedPrim))

    def Do(self):
        context = self.GetCurrentContext()
        refPath = UsdQtHooks.Call('GetReferencePath', stage=context.stage)
        if refPath:
            stage = context.stage
            prim = context.selectedPrim
            editLayer = context.editTargetLayer
            if not stage.HasLocalLayer(editLayer):
                # We use a temporary stage here to get around the local layer
                # restriction for variant edit contexts.
                editTargetStage = Usd.Stage.Open(editLayer)
                # this assumes prim path is the same in edit target
                prim = editTargetStage.GetPrimAtPath(prim.GetPath())

            prim.GetReferences().SetReferences([Sdf.Reference(refPath)])


class SaveState(object):
    """State tracker for layer contents in an outliner app"""
    def __init__(self, outliner):
        # type: (UsdOutliner) -> None
        """
        Parameters
        ----------
        outliner : UsdOutliner
        """
        self.outliner = outliner
        editTarget = outliner.GetEditTargetLayer()
        self.origLayerContents = \
            {self.GetId(editTarget): self._GetDiskContents(editTarget)}
        self._listener = Tf.Notice.Register(Usd.Notice.StageEditTargetChanged,
                                            self._OnEditTargetChanged,
                                            outliner.stage)

    def _OnEditTargetChanged(self, notice, stage):
        layer = stage.GetEditTarget().GetLayer()
        self.origLayerContents.setdefault(self.GetId(layer),
                                          layer.ExportToString())

    def GetOriginalContents(self, layer):
        # type: (Sdf.Layer) -> str
        """
        Parameters
        ----------
        layer : Sdf.Layer

        Returns
        -------
        str
        """
        return self.origLayerContents[self.GetId(layer)]

    def SaveOriginalContents(self, layer, contents=None):
        if not contents:
            contents = layer.ExportToString()
        self.origLayerContents[self.GetId(layer)] = contents

    def _GetDiskContents(self, layer):
        # type: (Sdf.Layer) -> str
        """Fetch the usd layer's contents on disk.

        Parameters
        ----------
        layer : Sdf.Layer

        Returns
        -------
        str
        """
        # with USD Issue #253 solved, we can do a cheaper check of just
        # comparing time stamps and getting contents only if needed.

        if not layer.realPath:
            # New() or anonymous layer that cant be loaded from disk.
            return None

        # TODO: Is it safe to ChangeBlock this content swapping?
        currentContents = layer.ExportToString()
        # fetch on disk contents for comparison
        layer.Reload()
        diskContents = layer.ExportToString()
        # but then restore users edits
        if diskContents != currentContents:
            layer.ImportFromString(currentContents)
        return diskContents

    def CheckOriginalContents(self, editLayer):
        # type: (Sdf.Layer) -> bool
        """
        Parameters
        ----------
        editLayer : Sdf.Layer

        Returns
        -------
        bool
        """
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
        # type: (Sdf.Layer) -> str
        """
        Parameters
        ----------
        layer : Sdf.Layer

        Returns
        -------
        str
        """
        return UsdQtHooks.Call('GetId', layer)


class SaveEditLayer(MenuAction):
    defaultText = 'Save Current Edit Layer'

    def __init__(self, state):
        self.state = state

    def Do(self):
        context = self.GetCurrentContext()
        """
        Save the current edit target to the appropriate place.
        """
        editTarget = context.editTargetLayer
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
    defaultText = 'Show Current Layer Text'

    def Do(self):
        context = self.GetCurrentContext()
        context.outliner.ShowLayerTextDialog()


class ShowEditTargetDialog(MenuAction):
    defaultText = 'Change Edit Target'

    def Do(self):
        context = self.GetCurrentContext()
        context.outliner.ShowEditTargetDialog()


class ShowOpinionEditor(MenuAction):
    defaultText = 'Show Opinion Editor'

    def Do(self):
        context = self.GetCurrentContext()
        context.outliner.ShowOpinionEditor(context.selectedPrims)


class OutlinerTreeView(ContextMenuMixin, QtWidgets.QTreeView):
    # Emitted with lists of selected and deselected prims
    primSelectionChanged = QtCore.Signal(list, list)

    def __init__(self, contextMenuActions, contextProvider=None, parent=None):
        # type: (List[MenuAction], Optional[ContextProvider], Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        contextMenuActions : List[MenuAction]
        contextProvider : Optional[ContextProvider]
        parent : Optional[QtWidgets.QWidget]
        """
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

        self._dataModel = None

    def setModel(self, model):
        """
        Parameters
        ----------
        model : QtCore.QAbstractItemModel
        """
        if model == self._dataModel:
            return

        oldSelectionModel = self.selectionModel()
        super(OutlinerTreeView, self).setModel(model)
        self._dataModel = model

        # This can't be a one-liner because of a PySide refcount bug.
        selectionModel = self.selectionModel()
        selectionModel.selectionChanged.connect(self._SelectionChanged)
        if oldSelectionModel:
            oldSelectionModel.deleteLater()

    # Custom methods -----------------------------------------------------------
    @QtCore.Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def _SelectionChanged(self, selected, deselected):
        """Connected to selectionChanged"""
        model = self._dataModel

        def toPrims(qSelection):
            return [model._GetPrimForIndex(index)
                    for index in qSelection.indexes() if index.column() == 0]
        self.primSelectionChanged.emit(toPrims(selected), toPrims(deselected))

    def SelectedPrims(self):
        # type: () -> List[Usd.Prim]
        """
        Returns
        -------
        List[Usd.Prim]
        """
        model = self._dataModel
        result = []
        for index in self.selectionModel().selectedRows():
            prim = model._GetPrimForIndex(index)
            if prim:
                result.append(prim)
        return result


class OutlinerViewDelegate(QtWidgets.QStyledItemDelegate):
    """
    Item delegate class assigned to an ``OutlinerTreeView``.
    """
    def __init__(self, stage, parent=None):
        # type: (Usd.Stage, Optional[QtGui.QWidget]) -> None
        """
        Parameters
        ----------
        stage : Usd.Stage
        parent : Optional[QtGui.QWidget]
        """
        super(OutlinerViewDelegate, self).__init__(parent=parent)
        self._activeLayer = None
        self._listener = None
        self.ResetStage(stage)

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
    def ResetStage(self, stage):
        if stage:
            self._activeLayer = stage.GetEditTarget().GetLayer()
            self._listener = \
                Tf.Notice.Register(Usd.Notice.StageEditTargetChanged,
                                   self._OnEditTargetChanged, stage)
        else:
            self._listener = None
            self._activeLayer = None

    def _OnEditTargetChanged(self, notice, stage):
        self.SetActiveLayer(stage.GetEditTarget().GetLayer())

    def SetActiveLayer(self, layer):
        # type: (Sdf.Layer) -> None
        """
        Parameters
        ----------
        layer : Sdf.Layer
        """
        self._activeLayer = layer


class OutlinerRole(object):
    """Helper which provides standard hooks for defining the context menu
    actions and menu bar menus that should be added to an outliner.
    """
    @classmethod
    def GetContextMenuActions(cls, outliner):
        # type: (UsdOutliner) -> List[Union[MenuAction, Type[MenuAction]]]
        """
        Parameters
        ----------
        outliner : UsdOutliner

        Returns
        -------
        List[Union[MenuAction, Type[MenuAction]]]
        """
        return [ActivatePrims, DeactivatePrims, SelectVariants, MenuSeparator,
                RemovePrim, MakeVisible, MakeInvisible]

    @classmethod
    def GetMenuBarMenuBuilders(cls, outliner):
        # type: (UsdOutliner) -> List[MenuBuilder]
        """
        Parameters
        ----------
        outliner : UsdOutliner

        Returns
        -------
        List[MenuBuilder]
        """
        saveState = SaveState(outliner)
        return [MenuBuilder('&File', [SaveEditLayer(saveState)]),
                MenuBuilder('&Tools', [ShowEditTargetLayerText,
                                       ShowEditTargetDialog,
                                       ShowOpinionEditor])]

class UsdOutliner(QtWidgets.QWidget):
    """UsdStage editing application which displays the hierarchy of a stage."""
    # Emitted when a new stage should be loaded into the outliners models
    stageChanged = QtCore.Signal(Usd.Stage)

    def __init__(self, stage, role=None, parent=None):
        # type: (Usd.Stage, Optional[Union[Type[OutlinerRole], OutlinerRole]], Optional[QtGui.QWidget]) -> None
        """
        Parameters
        ----------
        stage : Usd.Stage
        role : Optional[Union[Type[OutlinerRole], OutlinerRole]]
        parent : Optional[QtGui.QWidget]
        """
        super(UsdOutliner, self).__init__(parent=parent)

        self._stage = None
        self._listener = None
        self._dataModel = HierarchyBaseModel(stage=stage, parent=self)
        self.ResetStage(stage)

        if role is None:
            role = OutlinerRole
        self.role = role

        view = self._CreateView(stage, self.role)
        view.setColumnWidth(0, 360)
        view.setModel(self._dataModel)
        self.view = view

        delegate = OutlinerViewDelegate(stage, parent=view)
        view.setItemDelegate(delegate)
        self.stageChanged.connect(delegate.ResetStage)

        self.menuBarBuilder = MenuBarBuilder(
            self,
            menuBuilders=role.GetMenuBarMenuBuilders(self),
            parent=self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self.menuBarBuilder.menuBar)
        layout.addWidget(view)

        # Instances of child dialogs (for reference-counting purposes)
        self._sharedLayerTextEditors = {}
        self.editTargetDialog = None
        self.variantEditorDialog = None

    def _CreateView(self, stage, role):
        # type: (Usd.Stage, Union[Type[OutlinerRole], OutlinerRole]) -> QtWidgets.QAbstractItemView
        """Create the hierarchy view for the outliner.

        This is provided as a convenience for subclass implementations.

        Parameters
        ----------
        stage : Usd.Stage
        role : Union[Type[OutlinerRole], OutlinerRole]

        Returns
        -------
        QtWidgets.QAbstractItemView
        """
        return OutlinerTreeView(
            contextMenuActions=role.GetContextMenuActions(self),
            contextProvider=self,
            parent=self)

    @property
    def stage(self):
        return self._stage

    def _LayerDialogEditTargetChangeCallback(self, newLayer):
        currentLayer = self.GetEditTargetLayer()
        if newLayer == currentLayer or not newLayer.permissionToEdit:
            return False

        if currentLayer.dirty:
            box = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                'Unsaved Layer Changes',
                'The current edit target layer contains unsaved edits which '
                'will not be accessible after changing edit targets. Are you '
                'sure you want to switch?',
                buttons=QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes,
                parent=self)
            if box.exec_() != QtWidgets.QMessageBox.Yes:
                return False
        return True

    def GetMenuContext(self):
        # type: () -> OutlinerContext
        """
        Returns
        -------
        OutlinerContext
        """
        selectedPrims = self.view.SelectedPrims()
        selectedPrim = selectedPrims[0] if selectedPrims else None
        return OutlinerContext(qtParent=self, outliner=self, stage=self._stage,
                               editTargetLayer=self.GetEditTargetLayer(),
                               selectedPrim=selectedPrim,
                               selectedPrims=selectedPrims)

    def GetEditTargetLayer(self):
        # type: () -> Sdf.Layer
        """
        Returns
        -------
        Sdf.Layer
        """
        if self._stage:
            return self._stage.GetEditTarget().GetLayer()

    def ResetStage(self, stage):
        """Reset the stage for this outliner and child dialogs.

        Parameters
        ----------
        stage : Union[Usd.Stage, None]
            If None is given, this will clear the current stage
        """
        self._stage = stage
        self._dataModel.ResetStage(stage)
        self.stageChanged.emit(stage)

    def _OnLayerTextEditorFinished(self, layer):
        dialog = self._sharedLayerTextEditors.pop(layer, None)
        if dialog:
            dialog.deleteLater()

    def GetSharedLayerTextEditorInstance(self, layer):
        # type: (Sdf.Layer, bool, Optional[QtWidgets.QWidget]) -> LayerTextEditorDialog
        """Convenience method to get or create a shared editor dialog instance.

        Parameters
        ----------
        key : Any
        parent : Optional[QtWidgets.QWidget]

        Returns
        -------
        LayerTextEditorDialog
        """
        dialog = self._sharedLayerTextEditors.get(layer)
        if dialog is None:
            readOnly = not layer.permissionToEdit
            dialog = LayerTextEditorDialog(layer,
                                           readOnly=readOnly,
                                           parent=self)
            self._sharedLayerTextEditors[layer] = dialog
            dialog.finished.connect(
                lambda result: self._OnLayerTextEditorFinished(layer))
        return dialog

    def ShowLayerTextDialog(self, layer=None):
        if layer is None:
            layer = self.GetEditTargetLayer()
        dialog = self.GetSharedLayerTextEditorInstance(layer)
        self.stageChanged.connect(dialog.close)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def ShowEditTargetDialog(self):
        if not self.editTargetDialog:
            dialog = EditTargetDialog(
                self._stage,
                editTargetChangeCallback=self._LayerDialogEditTargetChangeCallback,
                parent=self)
            self.stageChanged.connect(dialog.editor.ResetStage)
            self.editTargetDialog = dialog
        self.editTargetDialog.show()
        self.editTargetDialog.raise_()
        self.editTargetDialog.activateWindow()

    def ShowOpinionEditor(self, prims=None):
        from pxr.UsdQt.opinionModel import OpinionStandardModel
        from pxr.UsdQtEditors.opinionEditor import OpinionDialog

        # only allow one window
        if not prims:
            prims = self.view.SelectedPrims()

        dialog = OpinionDialog(prims=prims, parent=self)
        self.view.primSelectionChanged.connect(
            dialog.controller.ResetPrims)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()


class UsdOutlinerDialog(QtWidgets.QDialog):
    """UsdStage editing application which displays the hierarchy of a stage."""
    stageChanged = QtCore.Signal(object)

    def __init__(self, stage, role=None, parent=None):
        super(UsdOutlinerDialog, self).__init__(parent=parent)

        self._listener = None
        self._stage = None
        self.ResetStage(stage)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.outliner = UsdOutliner(stage, role=role, parent=self)
        layout.addWidget(self.outliner)
        self.stageChanged.connect(self.outliner.ResetStage)

        self.setModal(False)
        self.resize(900, 600)

    # Qt Methods ---------------------------------------------------------------
    def closeEvent(self, event):
        # clearing stage to make sure no listeners are called as the qt objects
        # are being destroyed.
        self.ResetStage(None)

    # Custom Methods ------------------------------------------------------------
    @classmethod
    def FromUsdFile(cls, usdFile, role=None, parent=None):
        # type: (str, Optional[Union[Type[OutlinerRole], OutlinerRole]], Optional[QtGui.QWidget]) -> UsdOutliner
        """
        Parameters
        ----------
        usdFile : str
        role : Optional[Union[Type[OutlinerRole], OutlinerRole]]
        parent : Optional[QtGui.QWidget]

        Returns
        -------
        UsdOutliner
        """
        with Usd.StageCacheContext(Usd.BlockStageCaches):
            stage = Usd.Stage.Open(usdFile, Usd.Stage.LoadNone)
            assert stage, 'Failed to open stage'
            stage.SetEditTarget(stage.GetSessionLayer())
        return cls(stage, role=role, parent=parent)

    def UpdateTitle(self, identifier=None):
        # type: (Optional[str]) -> None
        """
        Parameters
        ----------
        identifier : Optional[str]
            If not provided, it is acquired from the curent edit target.
        """
        if not identifier and self._stage:
            identifier = self._stage.GetEditTarget().GetLayer().identifier
        self.setWindowTitle('Outliner - %s' % identifier)

    def _OnEditTargetChanged(self, notice, stage):
        self.UpdateTitle()

    def ResetStage(self, stage):
        if stage:
            self._listener = \
                Tf.Notice.Register(Usd.Notice.StageEditTargetChanged,
                                   self._OnEditTargetChanged, stage)
        else:
            if self._listener:
                # we revoke the listener here because timing is critical and
                # we cant wait for garbage collection.
                self._listener.Revoke()
            self._listener = None
        self._stage = stage

        self.UpdateTitle()
        self.stageChanged.emit(stage)


if __name__ == '__main__':
    # simple test
    import sys

    app = QtWidgets.QApplication(sys.argv)

    usdFileArg = sys.argv[1]

    dialog = UsdOutlinerDialog.FromUsdFile(usdFileArg)
    dialog.show()
    dialog.exec_()
