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

from ._Qt import QtCore, QtWidgets, QtGui

from pxr import Gf, Tf, Usd

from ._bindings import _AttributeProxy, _DisplayGroupProxy, _MetadataProxy, \
    _MetadataDictKeyProxy, _ObjectProxy, _PrimProxy, \
    _RelationshipProxy, _VariantSetsProxy, _VariantSetProxy

from . import valueWidgets
from . import compatability
from . import roles

if False:
    from typing import *


class ValueDelegate(QtWidgets.QStyledItemDelegate):
    """This delegate provides drawing and widgets for USD Standard types.

    This delegate provides paint functionality for types like GfMatrix* and
    GfVec*.  It also will instantiate UsdQt specific editors for all types.
    For consistancy, UsdQt editors should be preferred over the standard
    editors.

    You may subclass ValueDelegate to provide your own extensions and custom
    widgets to the default UsdQt handlers or write a new StyledItemDelegate
    using ValueDelegate as a reference implementation.
    """
    # def PaintArray(self, painter, option, index, arrayData, elementSize):
    #     super(ValueEditDelegate, self).paint(painter, option, QtCore.QModelIndex())
    #     arrayOption = QtWidgets.QStyleOptionViewItem(option)
    #     self.initStyleOption(arrayOption, index)
    #     style = QtWidgets.QApplication.style()
    #     #style = option.widget.style() if option.widget else QtWidgets.QApplication.style()
    #     left = arrayOption.rect.left()
    #     top = arrayOption.rect.top()
    #     width = arrayOption.rect.width()
    #     height = arrayOption.rect.height()
    #     columns = elementSize
    #     rows = len(arrayData)
    #     cellWidth = width / columns
    #     cellHeight = height / rows
    #     #self.initStyleOption
    #     for i in xrange(rows):
    #         for j in xrange(columns):
    #             cellRect = QtCore.QRect(left + cellWidth * j, top + cellHeight * i,
    #                                     cellWidth, cellHeight)
    #             if type(arrayData[0]) == [Gf.Vec4d, Gf.Vec4f, Gf.Vec4h, Gf.Vec3d, Gf.Vec3f, Gf.Vec3h, Gf.Vec2d, Gf.Vec2f, Gf.Vec2h]:
    #             style.drawItemText(painter, cellRect, arrayOption.displayAlignment,
    # arrayOption.palette, True, Usdq.ToString(displayData[i][j]))

    def PaintColor(self, painter, option, index):
        # type: (QtGui.QPainter, QtWidgets.QStyleOptionViewItem, QtCore.QModelIndex) -> None
        """
        Parameters
        ----------
        painter : QtGui.QPainter
        option : QtWidgets.QStyleOptionViewItem
        index : QtCore.QModelIndex
        """
        super(ValueDelegate, self).paint(
            painter, option, QtCore.QModelIndex())

        vecData = index.data(QtCore.Qt.EditRole)
        if not vecData:
            return
        if len(vecData) not in (3, 4):
            raise Exception("Paint color only supports color3f and color4f.")

        vecOption = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(vecOption, index)
        style = QtWidgets.QApplication.style()
        left = vecOption.rect.left()
        top = vecOption.rect.top()
        width = vecOption.rect.width()
        height = vecOption.rect.height()
        colorWidth = 20
        pad = 5
        columns = vecData.dimension
        cellWidth = (width - colorWidth) / columns

        displayVecData = Gf.ConvertLinearToDisplay(vecData)
        painter.save()
        painter.setBrush(QtGui.QColor(*[c * 255 for c in displayVecData]))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(left, top, colorWidth, height)
        painter.restore()

        for i in xrange(columns):
            cellRect = QtCore.QRect(colorWidth + pad + left + cellWidth * i,
                                    top, cellWidth, height)
            style.drawItemText(painter, cellRect, vecOption.displayAlignment,
                               vecOption.palette, True,
                               str(vecData[i]))

    def PaintVec(self, painter, option, index):
        # type: (QtGui.QPainter, QtWidgets.QStyleOptionViewItem, QtCore.QModelIndex) -> None
        """
        Parameters
        ----------
        painter : QtGui.QPainter
        option : QtWidgets.QStyleOptionViewItem
        index : QtCore.QModelIndex
        """
        super(ValueDelegate, self).paint(
            painter, option, QtCore.QModelIndex())

        vecData = index.data(QtCore.Qt.EditRole)
        if not vecData:
            return

        vecOption = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(vecOption, index)
        style = QtWidgets.QApplication.style()
        left = vecOption.rect.left()
        top = vecOption.rect.top()
        width = vecOption.rect.width()
        height = vecOption.rect.height()
        columns = vecData.dimension
        cellWidth = width / columns

        for i in xrange(columns):
            cellRect = QtCore.QRect(left + cellWidth * i, top,
                                    cellWidth, height)
            style.drawItemText(painter, cellRect, vecOption.displayAlignment,
                               vecOption.palette, True,
                               str(vecData[i]))

    def PaintMatrix(self, painter, option, index):
        # type: (QtGui.QPainter, QtWidgets.QStyleOptionViewItem, QtCore.QModelIndex) -> None
        """
        Parameters
        ----------
        painter : QtGui.QPainter
        option : QtWidgets.QStyleOptionViewItem
        index : QtCore.QModelIndex
        """
        super(ValueDelegate, self).paint(
            painter, option, QtCore.QModelIndex())

        matrixData = index.data(QtCore.Qt.EditRole)
        if not matrixData:
            return

        matrixOption = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(matrixOption, index)
        style = QtWidgets.QApplication.style()
        left = matrixOption.rect.left()
        top = matrixOption.rect.top()
        width = matrixOption.rect.width()
        height = matrixOption.rect.height()
        rows = matrixData.dimension[0]
        columns = matrixData.dimension[1]
        cellWidth = width / columns
        cellHeight = height / rows

        for i in xrange(rows):
            for j in xrange(columns):
                component = matrixData[i][j] or ''
                cellRect = QtCore.QRect(left + cellWidth * j,
                                        top + cellHeight * i,
                                        cellWidth, cellHeight)
                style.drawItemText(painter, cellRect,
                                   matrixOption.displayAlignment,
                                   matrixOption.palette, True, str(component))

    def PaintTab(self, painter, option, index):
        # type: (QtGui.QPainter, QtWidgets.QStyleOptionViewItem, QtCore.QModelIndex) -> None
        """
        Parameters
        ----------
        painter : QtGui.QPainter
        option : QtWidgets.QStyleOptionViewItem
        index : QtCore.QModelIndex
        """
        super(ValueDelegate, self).paint(
            painter, option, QtCore.QModelIndex())

        style = QtWidgets.QApplication.style()
        defaultOption = QtWidgets.QStyleOptionViewItem(option)

        displayRole = index.data(QtCore.Qt.DisplayRole)

        self.initStyleOption(defaultOption, index)
        style.drawItemText(painter, defaultOption.rect,
                           defaultOption.displayAlignment,
                           defaultOption.palette, True,
                           displayRole)

    def paint(self, painter, option, index):
        editorHint = index.data(roles.EditorHintRole)

        if type(editorHint) is roles.EditorHintBasicValue:
            if editorHint.type in valueWidgets.matrixTypes:
                self.PaintMatrix(painter, option, index)
                return
            elif editorHint.type in valueWidgets.vecTypes:
                self.PaintVec(painter, option, index)
                return
        elif type(editorHint) is roles.EditorHintTab:
            self.PaintTab(painter, option, index)
            return
        elif type(editorHint) is roles.EditorHintColorValue:
            self.PaintColor(painter, option, index)
            return
        super(ValueDelegate, self).paint(painter, option, index)

    def CreateBasicValueEditor(self, tfType, parent):
        # type: (Tf.Type, QtWidgets.QWidget) -> QtWidgets.QWidget
        """
        Parameters
        ----------
        tfType : Tf.Type
        parent : QtWidgets.QWidget

        Returns
        -------
        QtWidgets.QWidget
        """
        if tfType == Tf.Type.FindByName('bool'):
            editor = valueWidgets.BoolEdit(parent=parent)
            editor.editFinished.connect(self.CommitAndCloseEditor)
            return editor
        elif tfType in valueWidgets.valueTypeMap:
            return valueWidgets.valueTypeMap[tfType](parent=parent)

    def CreateColorValueEditor(self, tfType, parent):
        # type: (Tf.Type, QtWidgets.QWidget) -> valueWidgets._ColorEdit
        """

        Parameters
        ----------
        tfType : Tf.Type
        parent : QtWidgets.QWidget

        Returns
        -------
        valueWidgets._ColorEdit
        """
        editor = valueWidgets.colorTypeMap[tfType](parent=parent)
        return editor

    def CreateTextComboEditor(self, allowedValues, parent):
        # type: (List[str], QtWidgets.QWidget) -> valueWidgets.TextComboEdit
        """
        Parameters
        ----------
        allowedValues : List[str]
        parent : QtWidgets.QWidget

        Returns
        -------
        valueWidgets.TextComboEdit
        """
        editor = valueWidgets.TextComboEdit(allowedValues, parent=parent)
        editor.editFinished.connect(self.CommitAndCloseEditor)
        return editor

    def createEditor(self, parent, option, index):
        editorHint = index.data(roles.EditorHintRole)

        if type(editorHint) is roles.EditorHintBasicValue:
            return self.CreateBasicValueEditor(editorHint.type, parent)
        elif type(editorHint) is roles.EditorHintTextCombo:
            return self.CreateTextComboEditor(editorHint.allowedValues, parent)
        elif type(editorHint) is roles.EditorHintColorValue:
            return self.CreateColorValueEditor(editorHint.type, parent)

    @QtCore.Slot()
    def CommitAndCloseEditor(self):
        widget = self.sender()
        self.commitData.emit(widget)
        self.closeEditor.emit(widget, QtWidgets.QAbstractItemDelegate.NoHint)

    def setEditorData(self, editor, index):
        compatability.StyledItemDelegateSetEditorData(
            ValueDelegate, self, editor, index)

    def setModelData(self, editor, model, index):
        if not editor.IsChanged():
            return
        compatability.StyledItemDelegateSetModelData(
            ValueDelegate, self, editor, model, index)

    def sizeHint(self, option, index):
        editorHint = index.data(roles.EditorHintRole)

        if (type(editorHint) == roles.EditorHintBasicValue and
                editorHint.type in valueWidgets.matrixTypes):
            size = super(ValueDelegate, self).sizeHint(option, index)
            return QtCore.QSize(size.width(),
                                size.height() *
                                editorHint.type.pythonClass.dimension[0])

        elif type(editorHint) == roles.EditorHintTab:
            size = super(ValueDelegate, self).sizeHint(option, index)
            return QtCore.QSize(size.width(), size.height() * 1.35)

        return super(ValueDelegate, self).sizeHint(option, index)


if __name__ == '__main__':

    from . import opinionModel
    import sys
    import os
    app = QtWidgets.QApplication(sys.argv)

    dir = os.path.split(__file__)[0]
    path = os.path.join(
        dir, 'testenv', 'testUsdQtOpinionModel', 'simple.usda')
    stage = Usd.Stage.Open(path)
    prim = stage.GetPrimAtPath('/MyPrim1/Child1')

    model = opinionModel.OpinionStandardModel([prim])
    valueEditDelegate = ValueDelegate()

    tv = QtWidgets.QTreeView()
    tv.setModel(model)
    tv.setItemDelegate(valueEditDelegate)
    tv.show()
    sys.exit(app.exec_())
