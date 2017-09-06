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

EditorHintRole = QtCore.Qt.UserRole + 2
LayerStackDepthRole = QtCore.Qt.UserRole + 3
HierarchyPrimRole = QtCore.Qt.UserRole + 4
UsdQtUserRole = QtCore.Qt.UserRole + 16 

class EditorHintBasicValue(object):
    """Used for values whose editor can be inferred soley from the TfType"""
    def __init__(self, tfType):
        self.__type = tfType

    @property
    def type(self):
        return self.__type

class EditorHintTextCombo(object):
    """Used for a string/token editor restricted by a list of allowed values"""
    def __init__(self, allowedValues):
        self.__allowedValues = allowedValues

    @property
    def allowedValues(self):
        return self.__allowedValues

class EditorHintTab(object):
    """Used when an item should be drawn as a tab"""
    def __init__(self):
        pass