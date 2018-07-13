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

from ._Qt import QtCore, QtGui, QtWidgets
from pxr import Sdf, Usd, UsdQt
from typing import NamedTuple, Optional

import usdlib.utils
import usdlib.variants
from .common import DARK_ORANGE, passSingleSelection, passMultipleSelection, \
    ContextMenuBuilder, ContextMenuMixin, ContextMenuAction, UsdQtUtilities

if False:
    from typing import *


NO_VARIANT_SELECTION = '<No Variant Selected>'


Selection = NamedTuple('Selection',
                       [('index', Optional[QtCore.QModelIndex]),
                        ('prim', Optional[Usd.Prim])])


@passMultipleSelection
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


@passSingleSelection
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


@passMultipleSelection
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


@passSingleSelection
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


@passSingleSelection
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

        self._dataModel = UsdQt.HierarchyBaseModel(stage=stage, parent=self)
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
