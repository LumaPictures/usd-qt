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

from ._Qt import QtCore, QtWidgets, QtGui
from pxr import Sdf, Tf, Usd

from ._bindings import PrimFilterCache, _HierarchyCache
from . import compatability, roles, utils


class HierarchyBaseModel(QtCore.QAbstractItemModel):
    """Base class for adapting a stage's prim hierarchy for Qt ItemViews

    Most clients will want to use a configuration of the HierachyStandardModel
    which has a standard set of columns and data or subclass this to provide
    their own custom set of columns.

    Clients are encouraged to subclass this module because it provides both
    robust handling of change notification and an efficient lazy population.
    This model listens for TfNotices and emits the appropriate Qt signals.
    """
    class __LayoutChangedContext(object):
        """context manager to ensure layout changes if exception is thrown"""
        def __init__(self, model):
            self.model = model

        def __enter__(self):
            self.model.layoutAboutToBeChanged.emit()

        def __exit__(self, exceptionType, exceptionValue, traceBack):
            if exceptionType:
                self.model._Invalidate()
            self.model.layoutChanged.emit()

    def __init__(self, stage=None, predicate=Usd.TraverseInstanceProxies(
            Usd.PrimIsDefined | ~Usd.PrimIsDefined),
            parent=None):
        """Instantiate an QAbstractItemModel adapter for a UsdStage.

        It's safe for the 'stage' to be None if the model needs to be instatiated
        without knowing the stage its interacting with.

        'predicate' specifies the prims that may be accessed via the model on
        the stage. A good policy is to be as accepting of prims as possible
        and rely on a QSortFilterProxyModel to interactively reduce the view.
        Changing the predicate is a potentially expensive operation requiring
        rebuilding internal caches, making not ideal for interactive filtering.
        """
        super(HierarchyBaseModel, self).__init__(parent)

        self.__predicate = predicate
        self.__stage = None
        self.__index = None
        self.__listener = None
        self.ResetStage(stage)

    def __IsStageValid(self):
        return self.__stage and self.__stage.GetPseudoRoot()

    def ResetStage(self, stage):
        """Resets the model for use with a new stage.

        If the stage isn't valid, this effectively becomes an empty model.
        """
        if stage == self.__stage:
            return
        self.beginResetModel()
        self.__stage = stage
        if not self.__IsStageValid():
            self.__index = None
            self.__listener = None
        else:
            self.__index = _HierarchyCache(
                stage.GetPrimAtPath('/'), self.__predicate)
            self.__listener = Tf.Notice.Register(
                Usd.Notice.ObjectsChanged, self.__OnObjectsChanged, self.__stage)
        self.endResetModel()

    def GetPredicate(self):
        """Get the predicate used in stage hierarchy traversal
        """
        return self.__index.GetPredicate()

    def GetRoot(self):
        """Retrieve the root of the current hierarchy model"""
        rootProxy = self.__index.GetRoot()
        return rootProxy.GetPrim() if rootProxy and not rootProxy.expired else None

    def __OnObjectsChanged(self, notice, sender):
        resyncedPaths = notice.GetResyncedPaths()
        resyncedPaths = [path for path in resyncedPaths if path.IsPrimPath()]

        if len(resyncedPaths) > 0:
            with self.__LayoutChangedContext(self):
                persistentIndices = self.persistentIndexList()
                indexToPath = {}
                for index in persistentIndices:
                    indexProxy = index.internalPointer()
                    indexPrim = indexProxy.GetPrim()
                    indexPath = indexPrim.GetPath()

                    for resyncedPath in resyncedPaths:
                        commonPath = resyncedPath.GetCommonPrefix(indexPath)
                        # if the paths are siblings or if the
                        # index path is a child of resynced path, you need to update
                        # any persistent indices
                        areSiblings = commonPath == resyncedPath.GetParentPath() and commonPath != indexPath
                        indexIsChild = (commonPath == resyncedPath)

                        if areSiblings or indexIsChild:
                            indexToPath[index] = indexPath

                self.__index.ResyncSubtrees(resyncedPaths)

                fromIndices = []
                toIndices = []
                for index in indexToPath:
                    path = indexToPath[index]

                    if self.__index.ContainsPath(path):
                        newProxy = self.__index.GetProxy(path)
                        newRow = self.__index.GetRow(newProxy)

                        if (index.row() != newRow):
                            for i in xrange(self.columnCount(QtCore.QModelIndex())):
                                fromIndices.append(index)
                                toIndices.append(self.createIndex(
                                    newRow, index.column(), newProxy))
                    else:
                        fromIndices.append(index)
                        toIndices.append(QtCore.QModelIndex())
                self.changePersistentIndexList(fromIndices, toIndices)

    def GetIndexForPath(self, path):
        """Given a path, retrieve the appropriate index"""
        if self.__index.ContainsPath(path):
            proxy = self.__index.GetProxy(path)
            row = self.__index.GetRow(proxy)
            return self.createIndex(row, 0, proxy)

    def _GetPrimForIndex(self, modelIndex):
        """Retrieve the prim for the input modelIndex

        External clients should use UsdQt.roles.HierarchyPrimRole to access
        the prim for an index"""
        if modelIndex.isValid():
            proxy = modelIndex.internalPointer()
            proxy = compatability.ResolveValue(proxy)
            if type(proxy) is _HierarchyCache.Proxy and not proxy.expired:
                return proxy.GetPrim()
        return None

    def parent(self, modelIndex):
        if not self.__IsStageValid():
            return QtCore.QModelIndex()
        if not modelIndex.isValid():
            return QtCore.QModelIndex()

        proxy = modelIndex.internalPointer()

        if self.__index.IsRoot(proxy):
            return QtCore.QModelIndex()

        parentProxy = self.__index.GetParent(proxy)
        parentRow = self.__index.GetRow(parentProxy)

        return self.createIndex(parentRow, 0, parentProxy)

    def data(self, modelIndex, role=QtCore.Qt.DisplayRole):
        if not modelIndex.isValid():
            return None
        if not self.__IsStageValid():
            return None

        if role == QtCore.Qt.DisplayRole:
            prim = self._GetPrimForIndex(modelIndex)
            return prim.GetName()

        if role == roles.HierarchyPrimRole:
            return self._GetPrimForIndex(modelIndex)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.__IsStageValid():
            return QtCore.QModelIndex()
        if not parent.isValid():
            # We assume the root has already been registered.
            root = self.__index.GetRoot()
            return self.createIndex(row, column, root)

        parentProxy = parent.internalPointer()
        child = self.__index.GetChild(parentProxy, row)
        return self.createIndex(row, column, child)

    def columnCount(self, parent):
        return 1

    def rowCount(self, parent):
        if not self.__IsStageValid():
            return 0

        if not parent.isValid():
            return 1

        parentProxy = parent.internalPointer()
        return self.__index.GetChildCount(parentProxy)

    def Debug(self):
        self.__index.PrintFullIndex()


class HierarchyStandardModel(HierarchyBaseModel):
    """Configurable model for common columns for displaying hierarchies"""
    Name = "Name"
    Type = "Type"
    Kind = "Kind"

    NormalColor = QtGui.QBrush(QtGui.QColor(227, 227, 227))
    InactiveDarker = 200

    ArcsIconPath = 'icons/arcs_2.xpm'
    NoarcsIconPath = 'icons/noarcs_2.xpm'

    def __init__(self, stage=None, columns=None, parent=None):
        super(HierarchyStandardModel, self).__init__(
            stage, Usd.TraverseInstanceProxies(
                Usd.PrimIsDefined | ~Usd.PrimIsDefined), parent)
        if not columns:
            # By default show all possible columns.
            self.columns = [HierarchyStandardModel.Name,
                            HierarchyStandardModel.Type,
                            HierarchyStandardModel.Kind]
        else:
            self.columns = columns

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            return self.columns[section]

        return super(HierarchyStandardModel, self).headerData(
            section, orientation, role)

    def columnCount(self, parent):
        return len(self.columns)

    def data(self, modelIndex, role=QtCore.Qt.DisplayRole):
        if not (modelIndex.isValid()):
            return None
        column = self.columns[modelIndex.column()]
        if role == QtCore.Qt.ForegroundRole:
            prim = self._GetPrimForIndex(modelIndex)
            brush = HierarchyStandardModel.NormalColor
            if not prim.IsActive():
                brush = QtGui.QBrush(brush)
                brush.setColor(brush.color().darker(
                    HierarchyStandardModel.InactiveDarker))
            return brush
        elif role == QtCore.Qt.DecorationRole:
            if modelIndex.column() == 0:
                prim = self._GetPrimForIndex(modelIndex)
                if prim.HasAuthoredInherits() or \
                        prim.HasAuthoredReferences() or \
                        prim.HasVariantSets() or \
                        prim.HasPayload() or \
                        prim.HasAuthoredSpecializes():
                    return utils.IconCache.Get(self.ArcsIconPath)
                else:
                    return utils.IconCache.Get(self.NoarcsIconPath)
        elif role == QtCore.Qt.DisplayRole:
            if column == HierarchyStandardModel.Name:
                return super(HierarchyStandardModel, self).data(modelIndex, role)
            elif column == HierarchyStandardModel.Type:
                prim = self._GetPrimForIndex(modelIndex)
                typeName = prim.GetTypeName()
                return typeName if typeName else ""
            elif column == HierarchyStandardModel.Kind:
                prim = self._GetPrimForIndex(modelIndex)
                kind = prim.GetMetadata('kind')
                return kind if kind else ""
            else:
                raise Exception("shouldn't happen")
        elif role == QtCore.Qt.ToolTipRole:
            prim = self._GetPrimForIndex(modelIndex)
            specifier = prim.GetSpecifier()
            primType = prim.GetTypeName()
            documentation = prim.GetDocumentation()
            if specifier == Sdf.SpecifierDef:
                toolTipString = "Defined %s"
            elif specifier == Sdf.SpecifierOver:
                toolTipString = "Undefined %s"
            elif specifier == Sdf.SpecifierClass:
                toolTipString = "Abstract %s"
            else:
                raise Exception("Unhandled specifier for tooltip.")

            if not primType:
                toolTipString = toolTipString % "Prim"
            else:
                toolTipString = toolTipString % primType

            if documentation:
                toolTipString = "%s\n%s" % (toolTipString, documentation)

            if prim.IsInstanceProxy():
                toolTipString = "Instance Proxy of %s" % toolTipString
            if prim.IsInstanceable():
                toolTipString = "Instance Root of %s" % toolTipString
            return toolTipString

        return super(HierarchyStandardModel, self).data(modelIndex, role)


class HierarchyStandardFilterModel(QtCore.QSortFilterProxyModel):
    """Set of standard filtering strategies for items in a hierarchy model"""

    def __init__(self, showInactive=False,
                 showUndefined=False,
                 showAbstract=False,
                 filterCachePredicate=(Usd.PrimIsDefined | ~Usd.PrimIsDefined),
                 parent=None):
        super(HierarchyStandardFilterModel, self).__init__(parent)

        self.__filterCachePredicate = filterCachePredicate
        self.__filterCache = PrimFilterCache()
        self.__filterCacheActive = False

        self.__filterAcrossArcs = True
        self.__showInactive = showInactive
        self.__showUndefined = showUndefined
        self.__showAbstract = showAbstract

    def ClearFilter(self):
        self.__filterCacheActive = False
        self.invalidateFilter()

    def SetPathContainsFilter(self, substring):
        self.__filterCache.ApplyPathContainsFilter(self.sourceModel().GetRoot(),
                                                   compatability.ResolveValue(
                                                       substring),
                                                   self.__filterCachePredicate)
        self.__filterCacheActive = True
        self.invalidateFilter()

    def TogglePrimInactive(self, value):
        self.__showInactive = bool(value)
        self.invalidateFilter()

    def TogglePrimUndefined(self, value):
        self.__showUndefined = bool(value)
        self.invalidateFilter()

    def TogglePrimAbstract(self, value):
        self.__showAbstract = bool(value)
        self.invalidateFilter()

    def ToggleFilterAcrossArcs(self, value):
        self.__filterAcrossArcs = bool(value)
        self.invalidateFilter()

    def __FilterAll(self, prim):
        if prim.GetPath() == Sdf.Path('/'):
            return True
        if not self.__showInactive and not prim.IsActive():
            return False
        if not self.__showUndefined and not prim.GetSpecifier() in (Sdf.SpecifierDef, Sdf.SpecifierClass):
            return False
        if not self.__showAbstract and not prim.GetSpecifier() in (Sdf.SpecifierDef, Sdf.SpecifierOver):
            return False

        return True

    def filterAcceptsRow(self, sourceRow, sourceParent):
        index = self.sourceModel().index(sourceRow, 0, sourceParent)
        prim = index.data(role=roles.HierarchyPrimRole)
        prim = compatability.ResolveValue(prim)
        if not prim:
            raise Exception("Retrieved invalid prim during filtering.")

        if not self.__FilterAll(prim):
            return False

        isDefinedOrInRootStack = prim.GetPrimIndex().rootNode.hasSpecs or (
            prim.IsActive() and prim.IsDefined())
        if self.__filterAcrossArcs and not isDefinedOrInRootStack:
            return False

        if self.__filterCacheActive:
            state = self.__filterCache.GetState(prim.GetPath())
            return state not in [PrimFilterCache.Reject,
                                 PrimFilterCache.Untraversed]
        return True

if __name__ == '__main__':
    import sys
    import os
    from ._Qt import QtWidgets
    app = QtWidgets.QApplication(sys.argv)
    dir = os.path.split(__file__)[0]
    path = os.path.join(
        dir, 'testenv', 'testUsdQtHierarchyModel', 'simpleHierarchy.usda')
    stage = Usd.Stage.Open(path)
    model = HierarchyStandardModel(stage)
    search = QtWidgets.QLineEdit()

    tv = QtWidgets.QTreeView()
    tv.setModel(model)

    tv.show()

    sys.exit(app.exec_())
