import collections
# import pylib.types

from typing import (Any, Dict, Generic, Hashable, Iterable, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union, TYPE_CHECKING)


class ItemLookupError(Exception):
    pass


class TreeItem(object):
    '''Formalized data structure of an item with a hashable key'''
    __slots__ = ('key',)

    def __init__(self, key):
        '''
        Parameters
        ----------
        key : Hashable
            An identifier for this item. Must be unique within any trees it is
            added to.
        '''
        self.key = key

    def __repr__(self):
        return '{0.__class__.__name__}({0.key!r})'.format(self)


# any instance of a TreeItem subclass
T = TypeVar('T', bound=TreeItem)


class ItemTree(Generic[T]):
    '''
    A basic tree of items.
    '''
    def __init__(self, rootItem=None):
        '''
        Parameters
        ----------
        rootItem : Optional[T]
            Explicit item to use as the root of the tree. If omitted, a new
            ``TreeItem`` instance will be used.
        '''
        # self._itemBase = pylib.types.get_generic_type(self.__class__, T)

        if rootItem is None:
            rootItem = TreeItem('__ROOT__')
        else:
            self._validateItemType(rootItem)

        self._root = rootItem
        self._parentToChildren = {rootItem: self._makeInitialChildrenValue(rootItem)}  # type: Dict[T, List[T]]
        self._childToParent = {}  # type: Dict[T, T]
        self._keyToItem = {rootItem.key: rootItem}  # type: Dict[Hashable, T]

    def __contains__(self, item):
        return item in self._parentToChildren

    def _validateItemType(self, item):
        pass
#         if not issubclass(type(item), self._itemBase):
#             raise TypeError('Item class {0!r} does not inherit base tree item '
#                             'class {1!r}'.format(item.__class__, self._itemBase))

    @property
    def root(self):
        return self._root

    def empty(self):
        return len(self._parentToChildren) == 1

    def itemCount(self):
        '''
        Return the number of items in the tree, excluding the root item.

        Returns
        -------
        int
        '''
        return len(self._parentToChildren) - 1

    def itemByKey(self, key):
        '''
        Directly return an item by its associated key.

        Parameters
        ----------
        key : Hashable

        Returns
        -------
        T
        '''
        try:
            return self._keyToItem[key]
        except KeyError:
            raise ItemLookupError('Given item key not in tree')

    def parent(self, item):
        '''
        Return the parent of `item`.

        Parameters
        ----------
        item : T

        Returns
        -------
        T
        '''
        if item is self._root:
            raise ValueError('Root item has no parent')
        try:
            return self._childToParent[item]
        except KeyError:
            raise ItemLookupError('Given item {0!r} not in tree'.format(item))

    def _getItemChildren(self, parent):
        '''
        Internal method called to look up the children of the given parent item.

        If overridden by a subclass, this must return a (possibly empty) list of
        child items, or raise an ``ItemLookupError`` if the given parent is not
        part of the tree.

        Parameters
        ----------
        parent : T

        Returns
        -------
        List[T]
        '''
        try:
            return self._parentToChildren[parent]
        except KeyError:
            raise ItemLookupError('Given parent {0!r} not in tree'.format(parent))

    def childCount(self, parent=None):
        '''
        Return the number of items that are children of the given parent.

        This is useful mainly as a way to avoid the list copy associated with
        calling `len(self.children())`.

        Parameters
        ----------
        parent : Optional[T]

        Returns
        -------
        int
        '''
        if parent is None:
            parent = self._root
        return len(self._getItemChildren(parent))

    def children(self, parent=None):
        '''
        Return the list of immediate children under `parent`.

        Parameters
        ----------
        parent : Optional[T]
            if None, defaults to the root item

        Returns
        -------
        List[T]
        '''
        if parent is None:
            parent = self._root
        return list(self._getItemChildren(parent))

    def childAtRow(self, parent, row):
        '''
        Return the parent's child at the given index. 

        Parameters
        ----------
        parent : T
        row : int

        Returns
        -------
        T
        '''
        return self._getItemChildren(parent)[row]

    def rowIndex(self, item):
        '''
        Return the index of the given item in its parent's list of children.

        Parameters
        ----------
        item : T

        Returns
        -------
        int
        '''
        try:
            parent = self._childToParent[item]
        except KeyError:
            raise ItemLookupError('Given item {0!r} not in tree'.format(item))
        return self._getItemChildren(parent).index(item)

    def _makeInitialChildrenValue(self, parent):
        '''
        Internal method called when adding new items to the tree to return the
        default value that should be added to `self.parentToChildren` for the
        given parent.

        The default simply returns an empty list.

        Parameters
        ----------
        parent : T

        Returns
        -------
        object
        '''
        return []

    def addItems(self, items, parent=None):
        '''
        Add one or more items to the tree, parented under `parent`, or the root
        item if `parent` is None.

        Parameters
        ----------
        items : Iterable[T]
        parent : Optional[T]

        Returns
        -------
        List[T]
            newly added items from `items`
        '''
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
            self._validateItemType(item)
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

        makeChildrenValue = self._makeInitialChildrenValue
        for item in newItems:
            self._keyToItem[item.key] = item
            self._parentToChildren[item] = makeChildrenValue(item)
            self._childToParent[item] = parent
        self._parentToChildren[parent].extend(newItems)

        return newItems

    def removeItems(self, items, childAction='delete'):
        '''
        Remove one or more items (and optionally their children) from the tree.

        Parameters
        ----------
        items : Iterable[T]
        childAction : str
            {'delete', 'reparent'}
            The action to take for children of the items that will be removed.
            If this is 'reparent', any children of a given input item will be
            re-parented to that item's parent. If this is 'delete', any children
            of the input items will be deleted as well.

        Returns
        -------
        List[T]
            removed items from `items`
        '''
        if childAction not in ('delete', 'reparent'):
            raise ValueError('Invalid child action: {0!r}'.format(childAction))
        if isinstance(items, collections.Iterable):
            items = set(items)
        else:
            items = set((items,))

        items.discard(self._root)
        if not items:
            return []

        removeSets = [(item, self._getItemChildren(item)) for item in items]
        removed = []
        for itemToDelete, children in removeSets:
            if children:
                if childAction == 'delete':
                    # TODO: Can we get rid of this recursion?
                    removed.extend(
                            self.removeItems(children, childAction='delete'))
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

    def walkItems(self, startParent=None):
        '''
        Walk down the tree from `startParent` (which defaults to the root),
        recursively yielding each child item in breadth-first order.

        Parameters
        ----------
        startParent : Optional[T]

        Returns
        -------
        Iterator[T]
        '''
        if startParent is None:
            startParent = self._root
        stack = collections.deque(self._getItemChildren(startParent))
        while stack:
            item = stack.popleft()
            stack.extend(self._getItemChildren(item))
            yield item

    def iterItems(self):
        return self._keyToItem.iteritems()


class LazyItemTree(ItemTree[T]):
    '''
    Basic implementation of an ``ItemTree`` subclass that can fetch each item's
    children lazily as they are requested.

    This is a pretty basic approach that uses None as a placeholder value for
    each item's entry in the parent-to-children mapping when they are first
    added. Then, the first time an item's children are actually requested, the
    internal method `self._fetchItemChildren` will be called with the item as an
    argument, and its result will be stored in the parent-to-children mapping.
    '''

    def __init__(self, rootItem=None):
        super(LazyItemTree, self).__init__(rootItem=rootItem)
        self.blockUpdates = False

    def _fetchItemChildren(self, parent):
        '''
        Called by `self._getItemChildren` to actually fetch the child items for
        the given parent.

        This is called when the given parent's placeholder value in
        `self._parentToChildren` is set to None, and should return a (possibly
        empty) list of items.

        Parameters
        ----------
        parent : T

        Returns
        -------
        List[T]
        '''
        raise NotImplementedError

    def _getItemChildren(self, parent):
        children = super(LazyItemTree, self)._getItemChildren(parent)
        if children is None:
            if self.blockUpdates:
                # Pretend there are no children without updating internal state.
                return []
            self._parentToChildren[parent] = []
            children = self._fetchItemChildren(parent)
            if children:
                self.addItems(children, parent=parent)
        return children

    def _makeInitialChildrenValue(self, parent):
        return None

    def forgetChildren(self, parent):
        '''
        Recursively remove all children of `parent` from the tree, and reset its
        internal state so that `self._fetchItemChildren` will be called the next
        time the given parent's children are requested.

        Parameters
        ----------
        parent : T

        Returns
        -------
        List[T]
            All items removed from the tree as a result.
        '''
        if parent in (None, self._root):
            raise ValueError('Cannot forget all direct children of the root '
                             'item. Maybe you just want a new tree instead?')
        self.blockUpdates = True
        try:
            children = super(LazyItemTree, self)._getItemChildren(parent)
            if children:
                result = self.removeItems(children, childAction='delete')
            else:
                result = []
            self._parentToChildren[parent] = None
        finally:
            self.blockUpdates = False
        return result
