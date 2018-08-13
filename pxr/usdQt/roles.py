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
Contains UsdQt-specific Qt user roles, as well as some hint types for custom
editor widgets.
"""
from __future__ import absolute_import

from ._Qt import QtCore

# The editor hint role is used to provide additional information for UI
# instantiation that the value of the edit role alone may not be sufficient to
# provide.  For example, we may need to differentiate between a GfVec3f that
# represents a 3-tuple and a GfVec3f that represents a color.
# All UsdQt EditorHints are defined below and are prefixed with EditorHint.
EditorHintRole = QtCore.Qt.UserRole + 2

# Used to retrieve the prim object in hierarchy models.
HierarchyPrimRole = QtCore.Qt.UserRole + 3

# Specializations that leverage UsdQt at its core can use UsdQtUserRole as the
# first safe index for additional user roles
UsdQtUserRole = QtCore.Qt.UserRole + 16


class EditorHintBasicValue(object):
    """Used for values whose editor can be inferred soley from the TfType"""
    __slots__ = ('__type',)

    def __init__(self, tfType):
        self.__type = tfType

    @property
    def type(self):
        return self.__type


class EditorHintColorValue(object):
    """Hint for when a color editor needs to be instantiated"""
    __slots__ = ('__type',)

    def __init__(self, tfType):
        self.__type = tfType

    @property
    def type(self):
        return self.__type


class EditorHintTextCombo(object):
    """Used for a string/token editor restricted by a list of allowed values"""
    __slots__ = ('__allowedValues',)

    def __init__(self, allowedValues):
        self.__allowedValues = allowedValues

    @property
    def allowedValues(self):
        return self.__allowedValues


class EditorHintTab(object):
    """Used when an item should be drawn as a tab"""
    __slots__ = ()

    def __init__(self):
        pass
