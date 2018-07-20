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

from pxr import Sdf

from ._Qt import QtCore, QtGui, QtWidgets

if False:
    from typing import *

NULL_INDEX = QtCore.QModelIndex()

NO_COLOR = QtGui.QColor(0, 0, 0, 0)
GREEN = QtGui.QColor(14, 93, 45, 200)
BRIGHT_GREEN = QtGui.QColor(14, 163, 45, 200)
YELLOW = QtGui.QColor(255, 255, 102, 200)
BRIGHT_YELLOW = QtGui.QColor(255, 255, 185, 200)
DARK_ORANGE = QtGui.QColor(186, 99, 0, 200)
LIGHT_BLUE = QtGui.QColor(78, 181, 224, 200)
BRIGHT_ORANGE = QtGui.QColor(255, 157, 45, 200)
PALE_ORANGE = QtGui.QColor(224, 150, 66, 200)
DARK_BLUE = QtGui.QColor(14, 82, 130, 200)


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


def passSingleSelection(cls):
    # type: (MenuAction) -> MenuAction
    '''
    MenuAction decorator that will make it so the first context item
     is passed to the action's do() method.

    Parameters
    ----------
    cls : MenuAction

    Returns
    -------
    MenuAction
    '''
    cls.supportsMultiSelection = False
    return cls


def passMultipleSelection(cls):
    # type: (MenuAction) -> MenuAction
    '''
    MenuAction decorator that will make it so the full context list
     is passed to the action's do() method.

    Parameters
    ----------
    cls : MenuAction

    Returns
    -------
    MenuAction
    '''
    cls.supportsMultiSelection = True
    return cls


class _MenuSeparator(object):
    '''Use with Actions to specify a separator when configuring menu actions'''
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __call__(self, *args, **kwargs):
        return self

MenuSeparator = _MenuSeparator()


# TODO: How to persist calculated values from context across methods?
class MenuAction(object):
    '''Base class for menu actions'''
    __slots__ = ('_callable',)

    def __init__(self, func=None):
        self._callable = func

    def do(self, context):
        # type: (Context) -> None
        '''Called when the action is triggered.

        Parameters
        ----------
        context : Context
        '''
        if self._callable:
            self._callable()
        else:
            raise NotImplementedError(
                'No callable provided and do() method not reimplemented by '
                'class %s' % self.__class__.__name__)

    def enable(self, context):
        # type: (Context) -> bool
        '''Return whether the menu item should be enabled.

        Parameters
        ----------
        context : Context

        Returns
        -------
        bool
        '''
        return True

    def label(self, context):
        # type: (Context) -> str
        '''Return a label for the menu item.

        Parameters
        ----------
        context : Context

        Returns
        -------
        str
        '''
        raise NotImplementedError

    def Build(self, menu, context):
        '''Add this action to a QMenu that is being built.

        This can be overridden to implement things like dynamic submenus.

        Parameters
        ----------
        menu : QtWidgets.QMenu
        context : Context
        '''
        action = menu.addAction(self.label(context))
        if self.enable(context):
            action.triggered.connect(lambda: self.do(context))
        else:
            action.setEnabled(False)


class ContextMenuBuilder(object):
    '''Class to customize the building of context menus for widgets.
    '''
    def __init__(self, owner, actions):
        # type: (ContextMenuMixin, List[MenuAction]) -> None
        '''
        Parameters
        ----------
        owner : ContextMenuMixin
        actions : List[MenuAction]
        '''
        self.owner = owner
        self.actions = actions

    # TODO: Support passing MenuAction class or instance
    def AddAction(self, menu, action, context):
        # type: (QtWidgets.QMenu, MenuAction, Context) -> None
        '''Add an action to the context menu.

        Parameters
        ----------
        menu : QtWidgets.QMenu
        action : MenuAction
        context : Context
        '''
        if isinstance(action, _MenuSeparator):
            menu.addSeparator()
            return
        action.Build(menu, context)

    def ExecMenu(self, pos):
        # type: (QtCore.QPoint) -> bool
        '''Build and show the context menu at the given position.

        If the menu is empty, nothing will be done, and this will return False.

        Parameters
        ----------
        pos : QtCore.QPoint

        Returns
        -------
        bool
            Whether the menu was actually shown.
        '''
        menu = QtWidgets.QMenu(self.owner)
        context = self.owner.GetContext()
        for action in self.actions:
            self.AddAction(menu, action, context)
        if menu.isEmpty():
            return False
        menu.exec_(pos)
        return True


class ContextMenuMixin(object):
    '''Mix this class in with a view to bind a menu to a view'''
    def __init__(self, contextMenuBuilder=None, contextMenuActions=None,
                 parent=None):
        # type: (Any, Optional[ContextMenuBuilder], Optional[Callable[[QtGui.QView], List[MenuAction]]]) -> None
        '''
        Parameters
        ----------
        contextMenuBuilder : Optional[ContextMenuBuilder]
        contextMenuActions : Optional[Callable[[QtGui.QView], List[MenuAction]]]
        parent : Optional[QtWidgets.QWidget]
        '''
        if not contextMenuBuilder:
            contextMenuBuilder = ContextMenuBuilder
        if not contextMenuActions:
            contextMenuActions = self.defaultContextMenuActions
        # bind actions to view
        contextMenuActions = contextMenuActions(self)
        self._menuBuilder = contextMenuBuilder(self, contextMenuActions)
        super(ContextMenuMixin, self).__init__(parent=parent)

    # Qt methods ---------------------------------------------------------------
    def contextMenuEvent(self, event):
        if self._menuBuilder.ExecMenu(event.globalPos()):
            event.accept()

    # Custom methods -----------------------------------------------------------
# TODO: Get rid of this
    def GetSignal(self, name):
        # type: (str) -> QtCore.Signal
        '''Search through all actions on the menu-builder for a signal object.

        Parameters
        ----------
        name : str
            name of an attribute holding a signal

        Returns
        -------
        QtCore.Signal
        '''
        # search the view and then the menu and menu actions for a signal
        toSearch = [self, self._menuBuilder] + self._menuBuilder.actions + \
                   self._menuBuilder.nonMenuActions
        for obj in toSearch:
            signal = getattr(obj, name, None)
            if signal and isinstance(signal, QtCore.Signal):
                return signal
        raise ValueError('Signal not found: {} in any of {}'.format(
            name, ', '.join([x.__class__.__name__ for x in toSearch])))

    def defaultContextMenuActions(self, view):
        # type: (QtGui.QView) -> List[MenuAction]
        '''Override with default context menu actions

        Parameters
        ----------
        view : QtGui.QView

        Returns
        -------
        List[MenuAction]
        '''
        raise ValueError('must provide context menu actions for this class')

    @property
    def menuBuilder(self):
        return self._menuBuilder

    def GetContext(self):
        # type: () -> Context
        '''Override this to return useful context information to your actions.

        Returns
        -------
        Context
        '''
        raise NotImplementedError


class SelectionContextMenuMixin(ContextMenuMixin):
    def GetSelectedRowItems(self):
        # type: () -> List[T]
        '''
        Returns
        -------
        List[T]
        '''
        indexes = self.selectionModel().selectedRows()
        return [index.internalPointer() for index in indexes]

    def GetContext(self):
        # type: () -> Context
        # FIXME: create a Context here that includes self, selection, etc
        return self.GetSelectedRowItems()


class MenuBarBuilder(object):
    '''Attach a menu bar to a dialog'''
    def __init__(self, dialog, roleGetMenuNames, roleGetMenuActions):
        # type: (QtGui.QDialog, Callable[[QtGui.QDialog], Iterable[Tuple[str, Optional[str]]]], Callable[[QtGui.QDialog], Dict[str, Iterable[MenuAction]]]) -> None
        '''
        Parameters
        ----------
        dialog : QtGui.QDialog
        roleGetMenuNames : Callable[[QtGui.QDialog], Iterable[Tuple[str, Optional[str]]]]
            Role method that will return menu bar names
        roleGetMenuActions : Callable[[QtGui.QDialog], Dict[str, Iterable[MenuAction]]]
            Role method that will return menu bar actions
        '''
        self.dialog = dialog
        self._menuBar = QtWidgets.QMenuBar(dialog)
        self._menus = {}  # type: Dict[str, QtWidgets.QMenu]
        self.AddMenus(roleGetMenuNames(dialog))
        self.actions = roleGetMenuActions(dialog)
        self.PopulateMenus(self.actions)

    def AddMenu(self, name, label=None):
        # type: (str, Optional[str]) -> QtWidgets.QMenu
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
        # type: (str) -> Optional[QtWidgets.QMenu]
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

    def AddMenus(self, menus):
        # type: (Iterable[Tuple[str, Optional[str]]]) -> Any
        '''Create any menus needed on the bar

        Parameters
        ----------
        menus : Iterable[Tuple[str, Optional[str]]]
        '''
        for name, text in menus:
            self.AddMenu(name, text)

    def CallAction(self, action):
        # type: (MenuAction) -> Any
        '''Call the menu action.

        Parameters
        ----------
        action : MenuAction
        '''
        return action.do(self)

    def AddAction(self, menu, action):
        # type: (QtWidgets.QMenu, MenuAction) -> Any
        '''Add action to the menu if it should be displayed.

        Parameters
        ----------
        menu : QtWidgets.QMenu
        action : MenuAction
        '''
        if isinstance(action, MenuSeparator):
            menu.addSeparator()
            return
        if not action.shouldShow(self):
            return
        action.Build(self, menu)

    def PopulateMenus(self, actions):
        # type: (Dict[str, Iterable[MenuAction]]) -> Any
        '''Populate Menus in the menu bar

        Parameters
        ----------
        actions : Dict[str, Iterable[MenuAction]]
        '''
        # FIXME: order is not guaranteed with dict
        for menuName, menuActions in actions.iteritems():
            menu = self.GetMenu(menuName)
            for action in menuActions:
                self.AddAction(menu, action)


class UsdQtUtilities(object):
    '''
    Aggregator for customizable utilities in a usdQt app.

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
    '''
    Overrideable func for getting the path for a new reference from a user.

    Use UsdQtUtilities to provide your pipeline specific file browser ui.
    '''
    name, _ = QtWidgets.QInputDialog.getText(
        parent,
        'Add Reference',
        'Enter Usd Layer Identifier:')
    return name


def GetId(layer):
    '''
    Overrideable func to get the unique key used to store the original
    contents of a layer.

    Use UsdQtUtilities to provide support for pipeline specific resolvers that
    may need special handling.
    '''
    if isinstance(layer, Sdf.Layer):
        return layer.identifier
    else:
        return layer


UsdQtUtilities.register('GetReferencePath', GetReferencePath)
UsdQtUtilities.register('GetId', GetId)
