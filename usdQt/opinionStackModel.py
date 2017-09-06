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
from __future__ import print_function

import os.path

from ._Qt import QtCore
from pxr import Usd, Tf


class _AttributeHandler(object):

    def __init__(self, attributeName, timeCode):
        self.attributeName = attributeName
        self.timeCode = timeCode

    def IsSpecified(self, primSpec):
        if self.attributeName in primSpec.attributes:
            if self.timeCode != Usd.TimeCode.Default() and \
                    primSpec.attributes[self.attributeName].HasInfo('timeSamples'):
                return True
            return primSpec.attributes[self.attributeName].HasInfo('default')
        return False

    def GetValue(self, primSpec):
        if primSpec.attributes[self.attributeName].HasInfo('default'):
            return str(primSpec.attributes[self.attributeName].default)
        elif primSpec.attributes[self.attributeName].HasInfo('timeSamples'):
            return "TODO!"
        else:
            return None


class _PrimMetadataHandler(object):

    def __init__(self, metadataName):
        self.metadataName = metadataName

    def IsSpecified(self, primSpec):
        return primSpec.HasInfo(self.metadataName)

    def GetValue(self, primSpec):
        if primSpec.HasInfo(self.metadataName):
            return primSpec.GetInfo(self.metadataName)
        return None


class _PropertyMetadataHandler(object):

    def __init__(self, propertyName, metadataName):
        self.propertyName = propertyName
        self.metadataName = metadataName

    def IsSpecified(self, primSpec):
        if self.propertyName in primSpec.properties:
            return primSpec.properties[self.propertyName].HasInfo(self.metadataName)
        return False

    def GetValue(self, primSpec):
        if primSpec.properties[self.propertyName]:
            return primSpec.GetInfo(self.metadataName)
        return None


class _VariantSetsHandler(object):

    def __init__(self):
        pass

    def IsSpecified(self, primSpec):
        return bool(primSpec.variantSets)

    def GetValue(self, primSpec):
        return primSpec.variantSets


class _VariantSetHandler(object):

    def __init__(self, variantSet):
        self.variantSet = variantSet

    def IsSpecified(self, primSpec):
        return self.variantSet in primSpec.variantSelections

    def GetValue(self, primSpec):
        return primSpec.variantSelections[self.variantSets]


class _LayerItem(object):

    def __init__(self, layer, row):
        self.layer = layer
        self.strongestPrim = None
        self.children = []
        self.row = row


class _PrimItem(object):

    def __init__(self, primSpec, parent):
        self.primSpec = primSpec
        self.parent = parent


class OpinionStackFilter(QtCore.QSortFilterProxyModel):

    def __init__(self, parent=None):
        super(OpinionStackFilter, self).__init__(parent)
        self.__shouldShowFullStack = False

    def ToggleShowFullStack(self):
        self.__shouldShowFullStack = not self.__shouldShowFullStack
        self.invalidateFilter()

    def SetShowFullStack(self, shouldShowFullStack):
        if bool(shouldShowFullStack) != self.__shouldShowFullStack:
            self.__shouldShowFullStack = bool(shouldShowFullStack)
            self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        if self.__shouldShowFullStack:
            return True
        index = self.sourceModel().index(row, OpinionStackModel.OpinionColumn, parent)
        if self.sourceModel().data(index, QtCore.Qt.DisplayRole) is None:
            return False
        return True


class OpinionStackModel(QtCore.QAbstractItemModel):
    SourceColumn = 0
    OpinionColumn = 1

    def __init__(self, prim, handler, parent=None):
        super(OpinionStackModel, self).__init__(parent)
        self.__handler = handler
        self.ResetPrim(prim)

    def __OnObjectsChanged(self, notice, sender):
        resyncedPaths = notice.GetResyncedPaths()
        changedInfoOnlyPaths = notice.GetChangedInfoOnlyPaths()

        if not self.__prim and self.__valid:
            # some change has caused the prim to expire
            self.ResetPrim(None)
            return

        primPath = self.__prim.GetPath()
        if primPath in resyncedPaths:
            self.ResetPrim(self.__prim)
        elif primPath in changedInfoOnlyPaths:
            self.ResetPrim(self.__prim)

    def _GetPrimTree(self, prim):
        primStack = prim.GetPrimStack()
        primDefinition = prim.GetPrimDefinition()
        if primDefinition:
            primStack.append(primDefinition)
        primTree = []
        for prim in primStack:
            layer = prim.layer
            if len(primTree) == 0 or layer != primTree[-1].layer:
                primTree.append(_LayerItem(layer, len(primTree)))
            primTree[-1].children.append(
                _PrimItem(prim, primTree[-1]))
            if not primTree[-1].strongestPrim:
                if self.__handler.IsSpecified(prim):
                    primTree[-1].strongestPrim = len(primTree[-1].children) - 1
        return primTree

    def ResetPrim(self, prim):
        self.beginResetModel()
        if prim is None:
            self.__valid = False
            self.__prim = Usd.Prim()
        else:
            self.__valid = True
            self.__prim = prim
            self.__listener = Tf.Notice.Register(
                Usd.Notice.ObjectsChanged, self.__OnObjectsChanged, self.__prim.GetStage())

        if self.__prim:
            self.__primTree = self._GetPrimTree(prim)
        else:
            self.__primTree = []
        self.endResetModel()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        internalPointer = index.internalPointer()
        if type(internalPointer) == _LayerItem:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(internalPointer.parent.row, 0, internalPointer.parent)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                if section == OpinionStackModel.SourceColumn:
                    return "Source"
                elif section == OpinionStackModel.OpinionColumn:
                    return "Opinion"
                else:
                    raise Exception("invalid.")

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            return len(self.__primTree)
        internalPointer = parent.internalPointer()
        if type(internalPointer) == _LayerItem:
            return len(parent.internalPointer().children)
        elif type(internalPointer) == _PrimItem:
            return 0

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2

    def data(self, modelIndex, role=QtCore.Qt.DisplayRole):
        if (not modelIndex.isValid()):
            return super(OpinionStackModel, self).data(modelIndex, role)

        if role == QtCore.Qt.DisplayRole:
            internalPointer = modelIndex.internalPointer()
            if type(internalPointer) == _LayerItem:
                internalPointer = modelIndex.internalPointer()
                layer = internalPointer.layer
                strongestPrim = internalPointer.children[internalPointer.strongestPrim].primSpec \
                    if internalPointer.strongestPrim is not None else None

                if modelIndex.column() == self.SourceColumn:
                    if layer == self.__prim.GetStage().GetSessionLayer():
                        return "session"
                    elif layer == Usd.SchemaRegistry.GetSchematics():
                        return "registry"
                    return os.path.split(os.path.splitext(layer.identifier)[0])[-1]
                elif modelIndex.column() == self.OpinionColumn:
                    if strongestPrim is not None:
                        return self.__handler.GetValue(strongestPrim)
                    else:
                        return None
                else:
                    raise Exception("unknown column.")
            elif type(internalPointer) == _PrimItem:
                primSpec = modelIndex.internalPointer().primSpec
                if modelIndex.column() == self.SourceColumn:
                    return primSpec.path.pathString
                elif modelIndex.column() == self.OpinionColumn:
                    if self.__handler.IsSpecified(primSpec):
                        return self.__handler.GetValue(primSpec)
                    else:
                        return None
                else:
                    raise Exception("unknown column.")
        if role == QtCore.Qt.ToolTipRole:
            internalPointer = modelIndex.internalPointer()
            if type(internalPointer) == _LayerItem:
                return internalPointer.layer.identifier
            elif type(internalPointer) == _PrimItem:
                return internalPointer.primSpec.path.pathString
        return None

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            return self.createIndex(row, column, self.__primTree[row])
        else:
            return self.createIndex(row, column,
                                    parent.internalPointer().children[row])

    def flags(self, index):
        internalPointer = index.internalPointer()
        if type(internalPointer) == _LayerItem:
            primSpec = internalPointer.children[internalPointer.strongestPrim].primSpec \
                if internalPointer.strongestPrim is not None else None
        elif type(internalPointer) == _PrimItem:
            primSpec = internalPointer.primSpec
        else:
            primSpec = None
        if not primSpec or not self.__handler.IsSpecified(primSpec):
            return ~QtCore.Qt.ItemIsEnabled & \
                super(OpinionStackModel, self).flags(index)
        return super(OpinionStackModel, self).flags(index)

if __name__ == '__main__':
    from ._Qt import QtWidgets
    import sys
    app = QtWidgets.QApplication(sys.argv)

    stage = Usd.Stage.Open('testenv/testUsdQtOpinionModel/simple.usda')
    prim = stage.GetPrimAtPath('/MyPrim1/Child1')
    handler = _AttributeHandler("x", Usd.TimeCode.Default())
    model = OpinionStackModel(prim, handler)
    modelFilter = OpinionStackFilter()
    modelFilter.setSourceModel(model)
    tv = QtWidgets.QTreeView()
    tv.setModel(modelFilter)
    tv.show()
    sys.exit(app.exec_())
