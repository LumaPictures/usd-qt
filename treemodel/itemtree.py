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

import collections

if False:
    from typing import *


class ItemLookupError(Exception):
    pass


class TreeItem(object):
    """Formalized data structure of an item with a hashable key"""
    __slots__ = ('key',)

    def __init__(self, key):
        """
        Parameters
        ----------
        key : Hashable
            An identifier for this item. Must be unique within any trees it is
            added to.
        """
        self.key = key

    def __repr__(self):
        return '{0.__class__.__name__}({0.key!r})'.format(self)


class ItemTree(object):
    """A basic tree of hashable items, each of which can also be looked up using
    an associated key.
    """
    def __init__(self, rootItem=None):
        """
        Parameters
        ----------
        rootItem : Optional[TreeItem]
            Explicit item to use as the root of the tree. If omitted, a new
            `TreeItem` instance will be used.
        """
        if rootItem is None:
            rootItem = TreeItem('__ROOT__')
        else:
            self._ValidateItemType(rootItem)

        self._root = rootItem
        self._parentToChildren = {rootItem: self._MakeInitialChildrenValue(rootItem)}  # type: Dict[TreeItem, List[TreeItem]]
        self._childToParent = {}  # type: Dict[TreeItem, TreeItem]
        self._keyToItem = {rootItem.key: rootItem}  # type: Dict[Hashable, TreeItem]

    def __contains__(self, item):
        return item in self._parentToChildren

    def _ValidateItemType(self, item):
        pass

    @property
    def root(self):
        return self._root

    def Empty(self):
        return len(self._parentToChildren) == 1

    def ItemCount(self):
        """Return the number of items in the tree, excluding the root item.

        Returns
        -------
        int
        """
        return len(self._parentToChildren) - 1

    def ItemByKey(self, key):
        """Directly return an item by its associated key.

        Parameters
        ----------
        key : Hashable

        Returns
        -------
        TreeItem
        """
        try:
            return self._keyToItem[key]
        except KeyError:
            raise ItemLookupError('Given item key not in tree')

    def Parent(self, item):
        """Return the given item's parent.

        Parameters
        ----------
        item : TreeItem

        Returns
        -------
        TreeItem
        """
        if item is self._root:
            raise ValueError('Root item has no parent')
        try:
            return self._childToParent[item]
        except KeyError:
            raise ItemLookupError('Given item {0!r} not in tree'.format(item))

    def _GetItemChildren(self, parent):
        """Internal method called to look up the children of the given parent
        item.

        If overridden by a subclass, this must return a (possibly empty) list of
        child items, or raise an ``ItemLookupError`` if the given parent is not
        part of the tree.

        Parameters
        ----------
        parent : TreeItem

        Returns
        -------
        List[TreeItem]
        """
        try:
            return self._parentToChildren[parent]
        except KeyError:
            raise ItemLookupError('Given parent {0!r} not in tree'.format(parent))

    def ChildCount(self, parent=None):
        """Return the number of items that are children of the given parent.

        This is useful mainly as a way to avoid the list copy associated with
        calling `len(self.Children())`.

        Parameters
        ----------
        parent : Optional[TreeItem]

        Returns
        -------
        int
        """
        if parent is None:
            parent = self._root
        return len(self._GetItemChildren(parent))

    def Children(self, parent=None):
        """Return the list of immediate children under the given parent.

        Parameters
        ----------
        parent : Optional[TreeItem]
            If None, defaults to the root item.

        Returns
        -------
        List[TreeItem]
        """
        if parent is None:
            parent = self._root
        return list(self._GetItemChildren(parent))

    def IterChildren(self, parent=None):
        """Return an iterator over the immediate children of the given parent.

        Parameters
        ----------
        parent : Optional[TreeItem]
            If None, defaults to the root item.

        Returns
        -------
        Iterator[TreeItem]
        """
        if parent is None:
            parent = self._root
        return iter(self._GetItemChildren(parent))

    def ChildAtRow(self, parent, row):
        """Return the given parent's child item at the given index.

        Parameters
        ----------
        parent : TreeItem
        row : int

        Returns
        -------
        TreeItem
        """
        return self._GetItemChildren(parent)[row]

    def RowIndex(self, item):
        """Return the index of the given item in its parent's list of children.

        Parameters
        ----------
        item : TreeItem

        Returns
        -------
        int
        """
        try:
            parent = self._childToParent[item]
        except KeyError:
            raise ItemLookupError('Given item {0!r} not in tree'.format(item))
        return self._GetItemChildren(parent).index(item)

    def _MakeInitialChildrenValue(self, parent):
        """Internal method called when adding new items to the tree to return
        the default value that should be added to `self.parentToChildren` for
        the given parent.

        The default simply returns an empty list.

        Parameters
        ----------
        parent : TreeItem

        Returns
        -------
        object
        """
        return []

    def AddItems(self, items, parent=None):
        """Add one or more items to the tree, parented under `parent`, or the
        root item if `parent` is None.

        Parameters
        ----------
        items : Union[TreeItem, Iterable[TreeItem]]
        parent : Optional[TreeItem]

        Returns
        -------
        List[TreeItem]
            The newly added items from `items`.
        """
        if not items:
            return []
        if not isinstance(items, collections.Iterable):
            items = [items]

        if parent is None:
            parent = self._root
        elif parent not in self._parentToChildren:
            raise ItemLookupError('Given parent {0!r} not in tree'.format(parent))

        newItems = []
        newKeys = set()
        for item in items:
            self._ValidateItemType(item)
            if item not in self._childToParent:
                key = item.key
                if key in self._keyToItem:
                    raise ValueError('Item key shadows existing key '
                                     '{0!r}'.format(key))
                if key in newKeys:
                    raise ValueError('Duplicate incoming item key: '
                                     '{0!r}'.format(key))
                newKeys.add(key)
                newItems.append(item)

        makeChildrenValue = self._MakeInitialChildrenValue
        for item in newItems:
            self._keyToItem[item.key] = item
            self._parentToChildren[item] = makeChildrenValue(item)
            self._childToParent[item] = parent
        if self._parentToChildren[parent] is None:
            self._parentToChildren[parent] = []
        self._parentToChildren[parent].extend(newItems)

        return newItems

    def RemoveItems(self, items, childAction='delete'):
        """Remove one or more items (and optionally their children) from the
        tree.

        Parameters
        ----------
        items : Iterable[TreeItem]
        childAction : str
            {'delete', 'reparent'}
            The action to take for children of the items that will be removed.
            If this is 'reparent', any children of a given input item will be
            re-parented to that item's parent. If this is 'delete', any children
            of the input items will be deleted as well.

        Returns
        -------
        List[TreeItem]
            The removed items from `items`.
        """
        if childAction not in ('delete', 'reparent'):
            raise ValueError('Invalid child action: {0!r}'.format(childAction))
        if isinstance(items, collections.Iterable):
            items = set(items)
        else:
            items = set((items,))

        items.discard(self._root)
        if not items:
            return []

        removeSets = [(item, self._GetItemChildren(item)) for item in items]
        removed = []
        for itemToDelete, children in removeSets:
            if children:
                if childAction == 'delete':
                    # TODO: Can we get rid of this recursion?
                    removed.extend(
                        self.RemoveItems(children, childAction='delete'))
                else:
                    newParent = self._childToParent[itemToDelete]
                    while newParent in items:
                        newParent = self._childToParent[newParent]
                    self._parentToChildren[newParent].extend(children)
                    self._childToParent.update((c, newParent) for c in children)

            itemParent = self._childToParent.pop(itemToDelete)
            self._parentToChildren[itemParent].remove(itemToDelete)
            self._keyToItem.pop(itemToDelete.key)
            del self._parentToChildren[itemToDelete]
            removed.append(itemToDelete)
        return removed

    def WalkItems(self, startParent=None):
        """Walk down the tree from the given starting item (which defaults to
        the root), recursively yielding each child item in breadth-first order.

        Parameters
        ----------
        startParent : Optional[TreeItem]

        Returns
        -------
        Iterator[TreeItem]
        """
        if startParent is None:
            startParent = self._root
        stack = collections.deque(self._GetItemChildren(startParent))
        while stack:
            item = stack.popleft()
            stack.extend(self._GetItemChildren(item))
            yield item

    def IterItems(self):
        """Return an iterator over all of the key-item pairs in the tree, in an
        undefined order.

        Returns
        -------
        Iterator[Tuple[Hashable, TreeItem]]
        """
        return self._keyToItem.iteritems()


class LazyItemTree(ItemTree):
    """Basic implementation of an `ItemTree` subclass that can fetch each item's
    children lazily as they are requested.

    This is a pretty basic approach that uses None as a placeholder value for
    each item's entry in the parent-to-children mapping when they are first
    added. Then, the first time an item's children are actually requested, the
    internal method `self._FetchItemChildren` will be called with the item as an
    argument, and its result will be stored in the parent-to-children mapping.
    """
    def __init__(self, rootItem=None):
        super(LazyItemTree, self).__init__(rootItem=rootItem)
        self.blockUpdates = False

    def _FetchItemChildren(self, parent):
        """Called by `self._GetItemChildren` to actually fetch the child items
        for the given parent.

        This is called when the given parent's placeholder value in
        `self._parentToChildren` is set to None, and should return a (possibly
        empty) list of items.

        Parameters
        ----------
        parent : TreeItem

        Returns
        -------
        List[TreeItem]
        """
        raise NotImplementedError

    def _GetItemChildren(self, parent):
        children = super(LazyItemTree, self)._GetItemChildren(parent)
        if children is None:
            if self.blockUpdates:
                # Pretend there are no children without updating internal state.
                return []
            self._parentToChildren[parent] = []
            children = self._FetchItemChildren(parent)
            if children:
                self.AddItems(children, parent=parent)
        return children

    def _MakeInitialChildrenValue(self, parent):
        return None

    def ForgetChildren(self, parent):
        """Recursively remove all children of the given parent from the tree,
        and reset its internal state so that `self._FetchItemChildren` will be
        called the next time its children are requested.

        Parameters
        ----------
        parent : TreeItem

        Returns
        -------
        List[TreeItem]
            All items removed from the tree as a result.
        """
        if parent in (None, self._root):
            raise ValueError('Cannot forget all direct children of the root '
                             'item. Maybe you just want a new tree instead?')
        self.blockUpdates = True
        try:
            children = super(LazyItemTree, self)._GetItemChildren(parent)
            if children:
                result = self.RemoveItems(children, childAction='delete')
            else:
                result = []
            self._parentToChildren[parent] = None
        finally:
            self.blockUpdates = False
        return result
