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

from Qt import QtCore, QtGui, QtWidgets

NULL_INDEX = QtCore.QModelIndex()

NO_COLOR = QtGui.QColor(0, 0, 0, 0)
GREEN = QtGui.QColor(14, 93, 45, 64)
DARK_ORANGE = QtGui.QColor(186, 99, 0, 200)
LIGHT_BLUE = QtGui.QColor(78, 181, 224, 128)
BRIGHT_ORANGE = QtGui.QColor(255, 157, 45, 200)
PALE_ORANGE = QtGui.QColor(224, 150, 66, 200)
DARK_BLUE = QtGui.QColor(14, 82, 130, 128)


def BlendColors(color1, color2, mix=.5):
    return QtGui.QColor(*[one * mix + two * (1 - mix)
                          for one, two in
                          zip(color1.getRgb(), color2.getRgb())])


def CopyToClipboard(text):
    cb = QtWidgets.QApplication.clipboard()
    cb.setText(text, QtGui.QClipboard.Selection)
    cb.setText(text, QtGui.QClipboard.Clipboard)
