#
# Copyright 2016 Pixar
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

"""
UsdQt is currently architected to work with PySide2's API. This module is used
to provide compatability with other Qt APIs.

If you need to add a function here, try to document the reason it is being
added, and if there is any known path to deprecating it.
"""
from __future__ import absolute_import

from ._Qt import QtCore

if False:
    from typing import *
    from ._Qt import QtGui, QtWidgets


QT_VERSION_STR = QtCore.qVersion()
QT_VERSION_PARTS = map(int, QT_VERSION_STR.split('.'))
QT_VERSION_MAJOR, QT_VERSION_MINOR, QT_VERSION_RELEASE = QT_VERSION_PARTS


def StyledItemDelegateSetEditorData(cls, delegate, editor, index):
    # type: (Type[QtWidgets.QStyledItemDelegate], QtWidgets.QStyledItemDelegate, QtWidgets.QWidget, QtCore.QModelIndex) -> Any
    """PySide appears to force types that can behave as lists
    (ie. GfMatrix*, GfVec*) to be converted to lists when accessed via
    index.data(). Interestingly, model.data() in Pyside doesn't do this
    so there's a simple work around.

    Parameters
    ----------
    cls : Type[QtWidgets.QStyledItemDelegate]
        Unused
    delegate : QtWidgets.QStyledItemDelegate
        Unused
    editor : QtWidgets.QWidget
    index : QtCore.QModelIndex
    """
    data = index.data(QtCore.Qt.EditRole)
    setattr(editor, editor.metaObject().userProperty().name(), data)


def StyledItemDelegateSetModelData(cls, delegate, editor, model, index):
    # type: (Type[QtWidgets.QStyledItemDelegate], QtWidgets.QStyledItemDelegate, QtWidgets.QWidget, QtCore.QAbstractItemModel, QtCore.QModelIndex) -> Any
    """PySide appears to force types that can behave as lists
    (ie. GfMatrix*, GfVec*) to be converted to lists when accessed via
    index.data(). Interestingly, model.data() in Pyside doesn't do this,
    so there's a simple work around.

    Parameters
    ----------
    cls : Type[QtWidgets.QStyledItemDelegate]
        Unused
    delegate : QtWidgets.QStyledItemDelegate
        Unused
    editor : QtWidgets.QWidget
    model : QtCore.QAbstractItemModel
    index : QtCore.QModelIndex
    """
    value = getattr(editor, str(editor.metaObject().userProperty().name()))
    model.setData(index, value, role=QtCore.Qt.EditRole)


def HeaderViewSetResizeMode(header, mode):
    # type: (QtGui.QHeaderView, QtGui.QHeaderView.ResizeMode) -> Any
    """This method appears to have been renamed in Qt 5. For backwards,
    compatability with Qt4.

    Parameters
    ----------
    header : QtGui.QHeaderView
    mode : QtGui.QHeaderView.ResizeMode
    """
    if QT_VERSION_MAJOR == 4:
        header.setResizeMode(mode)
    elif QT_VERSION_MAJOR == 5:
        header.setSectionResizeMode(mode)


def EmitDataChanged(model, topLeft, bottomRight):
    # type: (QtCore.QAbstractItemModel, QtCore.QModelIndex, QtCore.QModelIndex) -> Any
    """The data changed API has changed between Qt4 and Qt5.

    Parameters
    ----------
    model : QtCore.QAbstractItemModel
    topLeft : QtCore.QModelIndex
    bottomRight : QtCore.QModelIndex
    """
    if QT_VERSION_MAJOR == 4:
        model.dataChanged.emit(topLeft, bottomRight)
    elif QT_VERSION_MAJOR == 5:
        model.dataChanged.emit(topLeft, bottomRight, [])
