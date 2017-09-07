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

import os

from ._Qt import QtCore, QtWidgets, QtGui

from pxr import Sdf

ICONSPATH = os.path.dirname(os.path.realpath(__file__))


class IconCache(object):
    __cache = {}

    @staticmethod
    def Get(path):
        if path not in IconCache.__cache:
            icon = QtGui.QIcon(os.path.join(ICONSPATH, path))
            IconCache.__cache[path] = icon
        return IconCache.__cache[path]


def SpecifierToString(specifier):
    if specifier is Sdf.SpecifierDef:
        return "def"
    elif specifier is Sdf.SpecifierOver:
        return "over"
    elif specifier is Sdf.SpecifierClass:
        return "class"
    else:
        raise Exception("Unknown specifier.")
