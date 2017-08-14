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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from ._Qt import QtCore

# UsdQt is currently architected to work with PySide2.  The compatability
# module is designed as a place to provide compatability with other vesions of
# Qt.  When adding a function here, try to document the reason that it's being
# added and if there's any path to deprecating it

def GetEditRole(index):
   model = index.model()
   data = model.data(index, QtCore.Qt.EditRole)
   editRole = ResolveValue(data)
   return editRole

def StyledItemDelegateSetEditorData(cls, delegate, editor, index):
    """PySide appears to force types that can behave as lists 
    (ie. GfMatrix*, GfVec*) to be converted to lists when accessed via
    index.data(). Interestingly, model.data() in Pyside doesn't do this 
    so there's a simple work around.
    """
    model = index.model()
    data = model.data(index, QtCore.Qt.EditRole)
    setattr(editor, editor.metaObject().userProperty().name(), data)

def StyledItemDelegateSetModelData(cls, delegate, editor, model, index):
    """PySide appears to force types that can behave as lists 
    (ie. GfMatrix*, GfVec*) to be converted to lists when accessed via
    index.data(). Interestingly, model.data() in Pyside doesn't do this, 
    so there's a simple work around.
    """
    value = getattr(editor, str(editor.metaObject().userProperty().name()))
    model.setData(index, value, role = QtCore.Qt.EditRole)

def HeaderViewSetResizeMode(header, mode):
    """This function appears to have been renamed in Qt 5.  For backwards,
    compatability with Qt4"""
    if QtCore.qVersion().startswith('4.'):
        header.setResizeMode(mode)
    elif QtCore.qVersion().startswith('5.'):
        header.setSectionResizeMode(mode)

def ResolveValue(value):
    """A unified wrapper for unpacking into PySide2 conventions."""
    if type(value).__name__ == 'QVariant':
        value = value.toPyObject()
    if type(value).__name__ == 'QString':
        value = str(value)
    return value

def EmitDataChanged(model, topLeft, bottomRight):
    """ The data changed API has changed between Qt4 and Qt5 """
    if QtCore.qVersion().startswith('4.'):
        model.dataChanged.emit(topLeft, bottomRight)
    elif QtCore.qVersion().startswith('5.'):
        model.dataChanged.emit(topLeft, bottomRight, [])
