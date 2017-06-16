'''
Not currently used
'''

from __future__ import absolute_import

from treemodel.itemtree import TreeItem, ItemLookupError
from treemodel.qt.base import AbstractTreeModelMixin, Column

from typing import (Any, Dict, Generic, Iterable, Iterator, List, Optional,
                    Tuple, TypeVar, Union, TYPE_CHECKING)

from Qt import QtCore, QtGui

T = TypeVar('T')
U = TypeVar('U')

NULL_INDEX = QtCore.QModelIndex()


# TODO: Signals?
class ItemIndexMap(Generic[T]):
    '''
    Generic storage container for hashable objects which acts like an ordered
    set and provides fast index lookup.
    '''
    __slots__ = ('_itemIndexMap', '_itemList')

    def __init__(self):
        self._itemIndexMap = {}
        self._itemList = []

    def __len__(self):
        '''
        Returns
        -------
        int
        '''
        return len(self._itemList)

    def __contains__(self, item):
        return item in self._itemIndexMap

    def item(self, index):
        '''
        Parameters
        ----------
        index : int

        Returns
        -------
        T
        '''
        try:
            return self._itemList[index]
        except IndexError:
            pass

    def index(self, item):
        '''
        Parameters
        ----------
        item : T

        Returns
        -------
        int
        '''
        return self._itemIndexMap.get(item)

    def addItem(self, item):
        '''
        Add an item if it isn't already present, and return its index.

        Parameters
        ----------
        item : T

        Returns
        -------
        int
        '''
        itemIndex = self._itemIndexMap.get(item)
        if itemIndex is None:
            self._itemList.append(item)
            itemIndex = len(self._itemList) - 1
            self._itemIndexMap[item] = itemIndex
        return itemIndex

    def removeItem(self, item):
        '''
        Remove an item. Return whether it was present.

        Parameters
        ----------
        item : T

        Returns
        -------
        bool
        '''
        index = self._itemIndexMap.pop(item, None)
        if index is not None:
            replacement = self._itemList.pop()
            self._itemList[index] = replacement
            self._itemIndexMap[replacement] = index
            return True
        return False


# TODO: Break out data store class that includes flags and allows all data for
# an item to be looked up without a compound key, so it can be shared by other
# application components.
class ItemDataModel(QtCore.QAbstractTableModel):
    '''
    A table of data. Intended to be used in conjunction with a
    `QAbstractProxyModel`, such as `ProxyTreeModel`.

    Each cell of data is identified by a row item, a column, and a
    Qt display role.

    The row item can be any hashable object.
    '''
    def __init__(self, columns, itemIndexMap=None, parent=None):
        '''
        Parameters
        ----------
        columns : Iterable[Column]
            The columns to allocate in the data model.
        itemIndexMap : Optional[ItemIndexMap[T]]
            Provides the mapping between table row indices and items. If None,
            a new empty instance will be created and used.
        '''
        super(ItemDataModel, self).__init__(parent)

        self._itemIndexMap = None  # type: ItemIndexMap[T]
        self._itemIndexMap = itemIndexMap or ItemIndexMap()

        self.columns = None  # type: Tuple[Column, ...]
        self.columnNameToIndex = None  # type: Dict[str, int]
        self._dataStore = {}  # type: Dict[Tuple[T, str, int], U]

        self.setColumns(columns)

    # Qt methods ---------------------------------------------------------------
    def index(self, row, column, parentIndex):
        if parentIndex.isValid():
            raise RuntimeError('NodeDataModel.index: parent index should never '
                               'be valid')
            # return NULL_INDEX
        item = self._itemIndexMap.item(row)
        assert item, 'ItemIndexMap lookup returned None in index()'
        return QtCore.QAbstractTableModel.createIndex(self, row, column, item)

    def rowCount(self, parentIndex):
        if parentIndex.isValid():
            return 0
        return len(self._itemIndexMap)

    def columnCount(self, parentIndex):
        return len(self.columns)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.column(section).label

    def data(self, modelIndex, role=QtCore.Qt.DisplayRole):
        '''
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
        role : int
            The Qt role.

        Returns
        -------
        Optional[U]
        '''
        if modelIndex.isValid():
            column = self.column(modelIndex.column())
            if column is None:
                return
            item = self._itemIndexMap.item(modelIndex.row())
            assert item, 'ItemIndexMap lookup returned None in data()'
            return self._dataStore.get((item, column.name, role))

    def setData(self, modelIndex, value, role):
        '''
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
        value : U
        role : int
            The Qt role.

        Returns
        -------
        bool
        '''
        if modelIndex.isValid():
            column = self.column(modelIndex.column())
            if column is None:
                return False
            item = self._itemIndexMap.item(modelIndex.row())
            assert item, 'ItemIndexMap lookup returned None in setData()'
            self._dataStore[(item, column.name, role)] = value
            self.dataChanged.emit(modelIndex, modelIndex)
            return True
        return False

    # Custom methods -----------------------------------------------------------
    def setColumns(self, columns):
        '''
        Parameters
        ----------
        columns : Iterable[Column]
        '''
        self.columns = tuple(columns)
        # Map column names to indices
        self.columnNameToIndex = dict((c.name, i)
                                      for i, c in enumerate(self.columns))

    def addItem(self, item):
        '''
        Register `item` in the table.

        This gives the `item` a row index which Qt methods can use to access it.

        Parameters
        ----------
        item : T
        '''
        self._itemIndexMap.addItem(item)

    def getItemIndex(self, item, column):
        '''
        Parameters
        ----------
        item : T
        column : Union[str, int, long]

        Returns
        -------
        QtCore.QModelIndex
        '''
        row = self._itemIndexMap.index(item)
        if row is not None:
            if not isinstance(column, (int, long)):
                column = self.columnNameToIndex[str(column)]
            return QtCore.QAbstractItemModel.createIndex(self, row, column,
                                                         item)
        return NULL_INDEX

    def column(self, indexOrName):
        '''
        Return a ``Column`` instance given its name or index in the model.

        Parameters
        ----------
        indexOrName : Union[str, int, long]

        Returns
        -------
        Optional[Column]
        '''
        if isinstance(indexOrName, basestring):
            try:
                return self.columns[self.columnNameToIndex[indexOrName]]
            except KeyError:
                return
        else:
            try:
                return self.columns[indexOrName]
            except IndexError:
                return

    def getItemData(self, itemOrRow, column, role=QtCore.Qt.DisplayRole):
        '''
        Get the data for a given ``DataItem``, column, and role.

        This returns the same results as `self.data()`.

        Parameters
        ----------
        itemOrRow : Union[T, int]
            The item (i.e. row key), or its internal index.
        column : Union[str, int, long]
            The column, as a column name or index.
        role : int
            The Qt role.

        Returns
        -------
        Optional[U]
        '''
        # FIXME: this code prevents us from using an int as an `item`:
        if isinstance(itemOrRow, (int, long)):
            item = self._itemIndexMap.item(itemOrRow)
            if item is None:
                return
        else:
            item = itemOrRow

        column = self.column(column)
        if column is None:
            return
        return self._dataStore.get((item, column.name, role))

    def setItemData(self, itemOrRow, column, role, value, emit=False):
        '''
        Directly set the data for a given item, column, and role.

        NOTE: This does **not** emit any Qt signals, so connected proxy models
        and their views may not pick up the change without manual intervention.

        Parameters
        ----------
        itemOrRow : Union[T, int]
            The item (i.e. row key), or its internal index.
        column : Union[str, int, long]
            The column, as a column name or index.
        role : int
            The Qt role.
        value : U
            The data to store.

        Returns
        -------
        bool
            whether the data was successfully set
        '''
        # FIXME: this code prevents us from using an int as an `item`:
        if isinstance(itemOrRow, (int, long)):
            item = self._itemIndexMap.item(itemOrRow)
            if item is None:
                return False
        else:
            item = itemOrRow
        if item not in self._itemIndexMap:
            raise ValueError('Given item does not exist in item-index mapping')

        column = self.column(column)
        if column is None:
            return False

        self._dataStore[(item, column.name, role)] = value
        # TODO
        if emit:
            pass
        return True


class ProxyTreeModel(AbstractTreeModelMixin, QtCore.QAbstractProxyModel):
    '''
    Maps the data stored in an `ItemDataModel` to the tree structure provided by
    an `ItemTree`.  Both must contain the same `TreeItem` instances.
    '''
    def __init__(self, sourceModel, sourceColumns=None, itemTree=None,
                 parent=None):
        '''
        Parameters
        ----------
        sourceModel : ItemDataModel[TreeItem, U]
        sourceColumns : Optional[Iterable[Union[str, Column]]]
            Columns (or names of columns) within `sourceModel` which should be
            used as the columns for this model.  If None, defaults to the
            complete list of columns from `sourceModel`.
        itemTree : Optional[ItemTree]
        parent
        '''
        if parent is None:
            parent = sourceModel
        super(ProxyTreeModel, self).__init__(itemTree=itemTree, parent=parent)

        # this is just a fast lookup for QAbstractProxyModel.sourceModel()
        self._sourceModel = None  # type: ItemDataModel[TreeItem, U]
        # Maps proxy column indices to source column indices
        self._proxyToSourceColumn = None  # type: List[int]
        # Maps source column indices to proxy column indices
        self._sourceToProxyColumn = None  # type: Dict[int, int]

        self.setSourceModel(sourceModel)
        self.setSourceColumns(sourceColumns or sourceModel.columns)

    def columnCount(self, parentIndex):
        return len(self._proxyToSourceColumn)

    def data(self, modelIndex, role=QtCore.Qt.DisplayRole):
        '''
        Parameters
        ----------
        modelIndex : QtCore.QModelIndex
        role : int

        Returns
        -------
        U
        '''
        if not modelIndex.isValid():
            return
        sourceIndex = self.mapToSource(modelIndex)
        # if role == QtCore.Qt.SizeHintRole:
        #     return QtCore.QSize(10, 32)
        item = sourceIndex.internalPointer()  # type: TreeItem
        return self._sourceModel.getItemData(item, sourceIndex.column(), role)

    # TODO: Do we need to override this?
    # def setData(self, modelIndex, value, role):
    #     if modelIndex.isValid():
    #         try:
    #             columnName = self.columnIndexToName[modelIndex.column()]
    #         except IndexError:
    #             return False
    #         item = modelIndex.internalPointer()
    #         self._dataStore[(item, columnName, role)] = value
    #         self.dataChanged.emit(modelIndex, modelIndex)
    #         return True
    #     return False

    def mapFromSource(self, sourceIndex):
        '''
        Parameters
        ----------
        sourceIndex : QtCore.QModelIndex

        Returns
        -------
        QtCore.QModelIndex
        '''
        if sourceIndex.isValid():
            try:
                mappedColumn = self._sourceToProxyColumn[sourceIndex.column()]
            except KeyError:
                pass
            else:
                item = sourceIndex.internalPointer()  # type: TreeItem
                try:
                    rowIndex = self.itemTree.rowIndex(item)
                except ItemLookupError:
                    pass
                else:
                    return self.createIndex(rowIndex, mappedColumn, item)
        return NULL_INDEX

    def mapToSource(self, proxyIndex):
        '''
        Parameters
        ----------
        proxyIndex : QtCore.QModelIndex

        Returns
        -------
        QtCore.QModelIndex
        '''
        if proxyIndex.isValid():
            try:
                mappedColumn = self._proxyToSourceColumn[proxyIndex.column()]
            except IndexError:
                pass
            else:
                item = proxyIndex.internalPointer()  # type: TreeItem
                return self._sourceModel.getItemIndex(item, mappedColumn)
        return NULL_INDEX

    def setSourceModel(self, sourceModel):
        # tell QAbstractProxyModel about our source model.
        super(ProxyTreeModel, self).setSourceModel(sourceModel)
        # we record self._sourceModel to avoid calls to
        # QAbstractProxyModel.sourceModel().
        # it might be over-cautious but the sourceModel gets accessed a lot and
        # it's unclear whether it incurs a penalty for marshalling from
        # c++ -> python.
        self._sourceModel = sourceModel

    # Custom methods -----------------------------------------------------------
    def setSourceColumns(self, sourceColumns):
        '''
        Set the list of source columns that this model will present to its view,
        as indices or column names.

        Parameters
        ----------
        sourceColumns : Iterable[Union[str, Columns]]
        '''
        forwardMap = []  # type: List[int]
        for col in sourceColumns:
            if isinstance(col, basestring):
                name = col
            elif isinstance(col, Column):
                name = col.name
            else:
                raise TypeError(col)
            forwardMap.append(self._sourceModel.columnNameToIndex[name])

        self._proxyToSourceColumn = forwardMap
        self._sourceToProxyColumn = dict((val, i)
                                         for i, val in enumerate(forwardMap))

    def getItemIndex(self, item, column):
        '''
        Parameters
        ----------
        item : TreeItem
        column : Union[str, int, long]

        Returns
        -------
        QtCore.QModelIndex
        '''
        if isinstance(column, (int, long)):
            column = self._proxyToSourceColumn[column]
        return self.mapFromSource(self._sourceModel.getItemIndex(item, column))

    def column(self, indexOrName):
        '''
        Return a source ``Column`` instance using its name or proxy index.

        Parameters
        ----------
        indexOrName : Union[str, int, long]

        Returns
        -------
        Optional[Column]
        '''
        # Integers are treated as proxy column indices
        if isinstance(indexOrName, (int, long)):
            indexOrName = self._proxyToSourceColumn[indexOrName]
        return self._sourceModel.column(indexOrName)

    def columns(self):
        '''
        Returns
        -------
        List[Column]
        '''
        return [self._sourceModel.column(index)
                for index in self._proxyToSourceColumn]

    def itemsChanged(self, items, column=None):
        '''
        Parameters
        ----------
        items : List[TreeItem]
        column : Union[Union[str, int, long]]
        '''
        # Column is an optimization/simplification. May not be worth keeping.
        if column is None:
            startIndex = self.getItemIndex(items[0], 0)
            endIndex = self.getItemIndex(items[-1], len(self._proxyToSourceColumn) - 1)
        else:
            startIndex = self.getItemIndex(items[0], column)
            endIndex = self.getItemIndex(items[-1], column)
        self.dataChanged.emit(startIndex, endIndex)
