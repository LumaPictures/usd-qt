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


class FallbackException(Exception):
    '''Raised if a customized function fails and wants to fallback to the 
    default implementation.'''
    pass


def BlendColors(color1, color2, mix=.5):
    return QtGui.QColor(*[one * mix + two * (1 - mix)
                          for one, two in
                          zip(color1.getRgb(), color2.getRgb())])


def CopyToClipboard(text):
    cb = QtWidgets.QApplication.clipboard()
    cb.setText(text, QtGui.QClipboard.Selection)
    cb.setText(text, QtGui.QClipboard.Clipboard)


class ContextMenuCallback(object):
    '''descriptor for passing on builder selection to builder methods'''

    def __init__(self, func, supportsMultiSelection=False):
        self.func = func
        self.supportsMultiSelection = supportsMultiSelection

    def __call__(self, *args, **kwargs):
        selection = self.builder.GetSelection()
        if selection:
            if self.supportsMultiSelection:
                return self.func(self.builder, selection)
            return self.func(self.builder, selection[0])

    def __get__(self, builder, objtype):
        self.builder = builder
        return self


def passSingleSelection(f):
    '''
    decorator to get the first selection item from the outliner and pass it
    into the decorated function.

    Parameters
    ----------
    f : Callable
        This method should operate on a single Selection object.

    Returns
    -------
    Callable
    '''
    return ContextMenuCallback(f, supportsMultiSelection=False)


def passMultipleSelection(f):
    '''
    decorator to get the current selection from the outliner and pass it
    into the decorated function.

    Parameters
    ----------
    f : Callable
        This method should operate on a list of Selection objects.

    Returns
    -------
    Callable
    '''
    return ContextMenuCallback(f, supportsMultiSelection=True)


class ContextMenuBuilder(QtCore.QObject):
    '''
    Base class to customize the building of right-click context menus for 
    selected view items.
    '''
    showMenuOnNoSelection = False

    def __init__(self, view):
        super(ContextMenuBuilder, self).__init__()
        self.view = view

    def DoIt(self, event):
        '''
        Inspect view selection and create context menu.

        Views should call this from their contextMenuEvent.
        '''
        selection = self.GetSelection()
        if not selection and not self.showMenuOnNoSelection:
            return
        menu = QtWidgets.QMenu(self.view)
        menu = self.Build(menu, selection)
        if menu is None:
            return
        menu.exec_(event.globalPos())
        event.accept()

    def GetSelectedRowItems(self):
        '''
        Returns
        -------
        List[T]
        '''
        indexes = self.view.selectionModel().selectedRows()
        return [index.internalPointer() for index in indexes]

    def GetSelection(self):
        '''
        Override this to return useful selection objects to your Build.

        Returns
        -------
        List
        '''
        return self.GetSelectedRowItems()

    def Build(self, menu, selections):
        '''
        Build and return the top-level context menu for the view.

        Parameters
        ----------
        menu : QtWidgets.QMenu
        selections : List[Selection]

        Returns
        -------
        Optional[QtWidgets.QMenu]
        '''
        raise NotImplementedError


class ContextMenuMixin(object):
    '''Mix this class in with a view to bind a menu top a view'''

    def __init__(self, parent=None, contextMenuBuilder=None):
        if not contextMenuBuilder:
            raise ValueError('must provide a menu builder to this class')
        self._menuBuilder = contextMenuBuilder(self)
        super(ContextMenuMixin, self).__init__(parent=parent)

    # Qt methods ---------------------------------------------------------------
    def contextMenuEvent(self, event):
        self._menuBuilder.DoIt(event)

    # Custom methods -----------------------------------------------------------
    def GetSignal(self, name):
        # search the view and then the menu for a signal
        for obj in (self, self._menuBuilder):
            signal = getattr(obj, name, None)
            if signal and isinstance(signal, QtCore.Signal):
                return signal
        raise ValueError('Signal not found: {} in {} or {}'.format(
            name, self.__class__, self._menuBuilder.__class__))

    @property
    def menuBuilder(self):
        return self._menuBuilder


class MenuBarBuilder(object):
    '''Attach a menu bar to a dialog'''

    def __init__(self, dlg):
        self.dlg = dlg
        self._menuBar = QtWidgets.QMenuBar(dlg)
        self._menus = {}  # type: Dict[str, QtWidgets.QMenu]
        self.AddMenus()
        self.PopulateMenus()

    def AddMenu(self, name, label=None):
        '''
        Parameters
        ----------
        name : str
            name of registered menu
        label : Optional[str]
            label to display in the menu bar

        Returns
        -------
        QtWidgets.QMenu
        '''
        if label is None:
            label = name
        menu = self._menuBar.addMenu(label)
        self._menus[name] = menu
        return menu

    def GetMenu(self, name):
        '''
        Get a named menu from the application's registered menus

        Parameters
        ----------
        name : str
            name of registered menu

        Returns
        -------
        Optional[QtWidgets.QMenu]
        '''
        return self._menus.get(name.lower())

    def AddMenus(self):
        '''Create any menus needed on the bar'''
        pass

    def PopulateMenus(self):
        '''Populate Menus in the menu bar'''
        pass


class UsdQtUtilities(object):
    '''Customizable utilities for building a usdqt app.

    To overwrite the default implementation, just define a function and then
    call:
    UsdQtUtilities.register('someName', func)
    '''
    _registered = {}

    @classmethod
    def register(cls, name, func):
        cls._registered.setdefault(name, []).insert(0, func)

    @classmethod
    def exec_(cls, name, *args, **kwargs):
        for func in cls._registered[name]:
            try:
                return func(*args, **kwargs)
            except FallbackException:
                continue


def GetReferencePath(parent, stage=None):
    name, _ = QtWidgets.QInputDialog.getText(
        parent,
        'Add Reference',
        'Enter Usd Layer Identifier:')
    return name


UsdQtUtilities.register('getReferencePath', GetReferencePath)
