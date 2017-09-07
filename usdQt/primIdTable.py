#
# Copyright 2016 Pixar
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

from __future__ import absolute_import, print_function
import sys
import logging
import bisect
from pxr import Usd, Sdf, Tf

from typing import Dict, List, NamedTuple, Set

_ItemInfo = NamedTuple('_ItemInfo', [
    ('path', Sdf.Path),   # The path represented by the item id.
    ('children', List[Sdf.Path])
])

_InternalId = int

_logger = logging.getLogger(__name__)


def binarySearch(a, x):
    i = bisect.bisect_left(a, x)
    return i < len(a)


class _PrimIdTable(object):
    def __init__(self, stage, root, predicate=Usd.PrimDefaultPredicate,
                 maxId=sys.maxint):
        """
        Parameters
        ----------
        stage : Usd.Stage
        root : Usd.Prim
        predicate: Usd.PrimDefaultPredicate
        maxId : _InternalId 

        Returns
        -------
        None
        """
        self._stage = stage
        self._predicate = predicate
        self._root = root.GetPath()
        self._nextAvailableId = 1
        self._maxId = maxId
        self._pathToId = {}  # type: Dict[Sdf.Path, _InternalId]
        self._idToItem = {}  # type: Dict[_InternalId, _ItemInfo]
        #    TfDebug.Enable(USDQT_DEBUG_PRIMIDTABLE)

        assert self._maxId > self._nextAvailableId
        self._RegisterPrim(root)

    def _RegisterPrim(self, prim):
        """
        Parameters
        ----------
        prim : Usd.Prim

        Returns
        -------
        None
        """
        path = prim.GetPath()
        assert self._nextAvailableId < self._maxId
        if path not in self._pathToId:
            self._pathToId[path] = self._nextAvailableId
            info = _ItemInfo(path, [])
            for child in prim.GetFilteredChildren(self._predicate):
                info.children.append(child.GetPath())

            self._idToItem[self._nextAvailableId] = info
            self._nextAvailableId += 1

    def GetPredicate(self):
        """
        Returns
        -------
        Usd.PrimFlagsPredicate
        """
        return self._predicate

    def IsRoot(self, id):
        """
        Parameters
        ----------
        id : _InternalId

        Returns
        -------
        bool
        """
        return self._idToItem.get(id) == self._root

    def GetRootPath(self):
        """
        Returns
        -------
        Sdf.Path
        """
        return self._root

    def ContainsPath(self, path):
        """
        Parameters
        ----------
        path : Sdf.Path

        Returns
        -------
        bool
        """
        return path in self._pathToId

    def ContainsId(self, id):
        """
        Parameters
        ----------
        id : _InternalId

        Returns
        -------
        bool
        """
        return id in self._idToItem

    def GetIdFromPath(self, path):
        """
        Parameters
        ----------
        path : Sdf.Path

        Returns
        -------
        _InternalId
        """
        id = self._pathToId.get(path)
        if id is None:
            raise Tf.ErrorException("Cannot find '%s' in PrimIdTable" % path)
        return id

    def GetPathFromId(self, id):
        """
        Parameters
        ----------
        id : _InternalId

        Returns
        -------
        Sdf.Path
        """
        item = self._idToItem.get(id)
        if item is None:
            raise Tf.ErrorException("Cannot find '%d' in PrimIdTable" % id)
        return item.path

    def GetChildCount(self, id):
        """
        Parameters
        ----------
        id : _InternalId

        Returns
        -------
        int
        """
        item = self._idToItem.get(id)
        if item is None:
            raise Tf.ErrorException("Cannot find '%d' in PrimIdTable" % id)
        return len(item.children)

    def GetChildPath(self, id, index):
        """
        Parameters
        ----------
        id : _InternalId
        index : int

        Returns
        -------
        Sdf.Path
        """
        item = self._idToItem.get(id)
        if item is None:
            raise Tf.ErrorException("Cannot find '%d' in PrimIdTable" % id)

        if index >= len(item.children):
            raise Tf.ErrorException(
                "Index '%d' exceeds number of children of '%s' in PrimIdTable" %
                (index, item.path))

        return item.children[index]

    def GetParentId(self, id):
        """
        Parameters
        ----------
        id : _InternalId

        Returns
        -------
        _InternalId
        """
        item = self._idToItem.get(id)
        if item is None:
            raise Tf.ErrorException("Cannot find '%d' in PrimIdTable" % id)

        path = item.path
        if path == self._root:
            return 0

        parent = path.GetParentPath()
        parentId = self._pathToId.get(parent)
        if parentId is None:
            raise Tf.ErrorException(
                "Cannot find parent '%s' of '%s' in PrimIdTable" %
                (parent, path))

        return parentId

    def GetLastId(self):
        """
        Returns
        -------
        _InternalId
        """
        return self._nextAvailableId - 1

    def GetRow(self, id):
        """
        Parameters
        ----------
        id : _InternalId

        Returns
        -------
        int
        """
        item = self._idToItem.get(id)
        if item is None:
            raise Tf.ErrorException("Cannot find '%d' in PrimIdTable" % id)

        parentId = self.GetParentId(id)
        path = self.GetPathFromId(id)
        if path == self._root:
            return 0

        parentItem = self._idToItem.get(parentId)
        if parentItem is None:
            raise Tf.ErrorException(
                "Cannot find parent '%d' of '%d' in PrimIdTable" %
                (parentId, id))

        return parentItem.index(path)
        # # Run a search to find the index.
        # rowIterator = std.find(parentItem.children.begin(),
        #                        parentItem.children.end(), path)
        #
        # return rowIterator - parentItem.children.begin()

    def RegisterChild(self, id, index):
        """
        Parameters
        ----------
        id : _InternalId
        index : int

        Returns
        -------
        bool
        """
        item = self._idToItem.get(id)
        if item is None:
            raise Tf.ErrorException("Cannot find '%d' in PrimIdTable" % id)

        if index >= len(item.children):
            raise Tf.ErrorException(
                "Index '%d' exceeds number of children of '%s' in PrimIdTable" %
                (index, item.path))

        path = item.children[index]

        if path in self._pathToId:
            # already registered.
            return True

        prim = self._stage.GetPrimAtPath(path)
        if not prim:
            raise Tf.ErrorException(
                "Expected child (%d) of id (%d) has expired.", (index, id))

        if self._nextAvailableId >= self._maxId:
            _logger.warn("out of indices.")
            return False

        self._RegisterPrim(prim)
        return True

    def _DeleteSubtree(self, path):
        """
        Parameters
        ----------
        path : Sdf.Path

        Returns
        -------
        None
        """
        if path in self._pathToId:
            _logger.debug("Deleting instantiated path: '%s'", path)
            id = self._pathToId.pop(path)
            for childPath in self._idToItem[id].children:
                self._DeleteSubtree(childPath)
            self._idToItem.pop(id)
        else:
            _logger.debug(
                "Skipping deletion of uninstantiated path: '%s'", path)

    def _InvalidateSubtree(self, path):
        """
        Parameters
        ----------
        path : Sdf.Path

        Returns
        -------
        None
        """
        id = self._pathToId.get(path)
        if id is not None:
            prim = self._stage.GetPrimAtPath(path)
            if prim.IsValid() and self._predicate(prim):
                _logger.debug("Keeping '%s' during invalidation.", path)
                for childPath in self._idToItem[id].children:
                    self._InvalidateSubtree(childPath)

                _logger.debug("Original size: %d children.",
                              len(self._idToItem[id].children))
                self._idToItem[id].children[:] = []
                for child in prim.GetFilteredChildren(self._predicate):
                    self._idToItem[id].children.append(child.GetPath())

                _logger.debug("New size: %d children.\n",
                              len(self._idToItem[id].children))
            else:
                _logger.debug("Rejecting '%s' during invalidation.", path)
                self._DeleteSubtree(path)

        else:
            _logger.debug("Skipping invalidation of uninstantiated path '%s'",
                          path)

    def ResyncSubtrees(self, paths):
        """
        Parameters
        ----------
        paths : List[Sdf.Path]

        Returns
        -------
        None
        """
        # TODO: Is there a way to optimize the paths that need to be traversed
        # if there are redundancies? (say, /World/foo and /World/foo/bar)
        sortedPaths = paths[:]
        sortedPaths.sort()

        # Uniquify the list of parents.
        uniqueParents = set()  # type: Set[Sdf.Path]
        for path in sortedPaths:
            uniqueParents.add(path.GetParentPath())

        outOfSyncPaths = set()  # type: Set[Sdf.Path]

        # Update the list of children per unique parent.
        for parentPath in uniqueParents:
            _logger.debug("Updating children of parent: '%s'\n", parentPath)

            parentId = self.GetIdFromPath(parentPath)
            sortedOriginalChildren = self._idToItem[parentId].children
            sortedOriginalChildren.sort()

            newChildren = []  # type: List[Sdf.Path]

            # Look through the new children to find any paths aren't in the
            # original
            # children and not in sorted paths.  These have gotten out of sync.
            parentPrim = self._stage.GetPrimAtPath(parentPath)
            for child in parentPrim.GetFilteredChildren(self._predicate):
                inOriginalChildren = binarySearch(sortedOriginalChildren,
                                                  child.GetPath())
                inResyncPaths = binarySearch(sortedPaths, child.GetPath())

                if inOriginalChildren or inResyncPaths:
                    _logger.debug("Keeping child: '%s'", child.GetPath())
                    newChildren.append(child.GetPath())
                else:
                    _logger.debug(
                        "Out of sync new child: '%s'", child.GetPath())
                    outOfSyncPaths.add(child.GetPath())

            sortedNewChildren = newChildren[:]
            # std.sort(sortedNewChildren.begin(), sortedNewChildren.end())
            sortedNewChildren.sort()
            # Look through the original children to find any paths are missing
            # and not in sorted paths.  These have gotten out of sync, likely
            # because ResyncSubtrees has been called with an incomplete list.
            # This isn't strictly necessary other than for error checking.
            for childPath in sortedOriginalChildren:
                inNewChildren = binarySearch(sortedNewChildren, childPath)
                inResyncPaths = binarySearch(sortedPaths, childPath)
                if not inNewChildren and not inResyncPaths:
                    _logger.debug(
                        "Out of sync original child: '%s'", childPath)
                    outOfSyncPaths.add(childPath)

            # Assign the new children vector to the parent.
            self._idToItem[parentId].children[:] = newChildren
            _logger.debug("Total children count: '%d'",
                          len(self._idToItem[parentId].children))

        if outOfSyncPaths:
            raise Tf.ErrorException("Indices may have been lost during "
                                    "index resync.")
        for path in sortedPaths:
            self._InvalidateSubtree(path)

    def PrintFullIndex(self):
        """
        Returns
        -------
        None
        """
        print("Root: %s " % self._root)
        for id, item in self._idToItem:
            if item.path in self._pathToId:
                if self._pathToId[item.path] == id:
                    pathMapInfo = "correct"
                else:
                    pathMapInfo = "out of sync path map entry: %s" % \
                                  self._pathToId[item.path]
            else:
                pathMapInfo = "Missing Path Map Entry."
            print("[id]: %d [path]: %s [path map]: %s [child count]: %d" %
                  (id, item.path, pathMapInfo, len(item.children)))

        for path, id in self._pathToId.items():
            if id not in self._idToItem:
                print("Dangling path: %s" % path)

    def PrintSubtreeIndex(self, path):
        """
        Parameters
        ----------
        path : Sdf.Path

        Returns
        -------
        None
        """
        if path not in self._pathToId:
            print("(uninstantiated) %s" % path)
        else:
            id = self.GetIdFromPath(path)
            print("%s id: %d row: %d" % (path, id, self.GetRow(id)))
            for child in self._idToItem[id].children:
                self.PrintSubtreeIndex(child)
