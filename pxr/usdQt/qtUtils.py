#
# Copyright 2018 Luma Pictures
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

import os
from functools import partial
from inspect import isclass

from ._Qt import QtCore, QtGui, QtWidgets

if False:
    from typing import *


ICONSPATH = os.path.dirname(os.path.realpath(__file__))

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


def BlendColors(color1, color2, mix=.5):
    return QtGui.QColor(*[one * mix + two * (1 - mix)
                          for one, two in
                          zip(color1.getRgb(), color2.getRgb())])


def CopyToClipboard(text):
    cb = QtWidgets.QApplication.clipboard()
    cb.setText(text, QtGui.QClipboard.Selection)
    cb.setText(text, QtGui.QClipboard.Clipboard)


class IconCache(object):
    __cache = {}

    @staticmethod
    def Get(path):
        if path not in IconCache.__cache:
            icon = QtGui.QIcon(os.path.join(ICONSPATH, path))
            IconCache.__cache[path] = icon
        return IconCache.__cache[path]


class _MenuSeparator(object):
    '''Use with Actions to specify a separator when configuring menu actions'''
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __call__(self, *args, **kwargs):
        return self

    def AddToMenu(self, menu, context):
        menu.addSeparator()


MenuSeparator = _MenuSeparator()


class MenuAction(object):
    '''Base class for menu actions'''
    defaultText = None

    def Build(self, context):
        '''Create and return a `QAction` to add to a menu that is being built.

        This can be overridden to implement things like dynamic submenus. It is
        also valid to return None to avoid adding an action to the menu.

        Parameters
        ----------
        context : Context

        Returns
        -------
        Optional[QAction]
        '''
        text = self.defaultText
        if text is None:
            text = self.__class__.__name__
        action = QtWidgets.QAction(text, None)
        self.Update(action, context)
        action.triggered.connect(lambda: self.Do(context))
        return action

    def Update(self, action, context):
        '''Update a `QAction` that was generated by this `MenuAction` instance.

        This is called by the default implementation of `Build`, and may also be
        called by the owner of a persistent menu immediately before it is shown.
        It can be used to update things like the enabled state, text, or even
        visibility of the given action.

        The default implementation does nothing.

        Parameters
        ----------
        action : QtWidgets.QAction
        context : Context
        '''
        pass

    def AddToMenu(self, menu, context):
        '''Add this action to a `QMenu` that is being built.

        This calls `self.Build()` to create a `QAction`, and if the result is
        not None, adds it to the given menu and attaches this `MenuAction`
        instance to it as custom data.

        This is the preferred method for adding `MenuAction` instances to menus,
        and is used by the `MenuBuilder` class.

        Parameters
        ----------
        menu : QtWidgets.QMenu
        context : Context
        '''
        action = self.Build(context)
        if action is not None:
            action.setData(self)
            menu.addAction(action)
            action.setParent(menu)

    def Do(self, context):
        # type: (Context) -> None
        '''Called when the action is triggered.

        Subclasses must reimplement this.

        Parameters
        ----------
        context : Context
        '''
        raise NotImplementedError


class SimpleMenuAction(MenuAction):
    '''Simple MenuAction subclass that allows its Do and Update callbacks to be
    provided as __init__ arguments.
    '''
    def __init__(self, defaultText, actionCallback, updateCallback=None):
        # type: (str, Callable[[Any], None], Optional[Callable[[MenuAction, Any], None]]) -> None
        '''
        Parameters
        ----------
        defaultText : str
        actionCallback : Callable[[Any], None]
        updateCallback : Optional[Callable[[MenuAction, Any], None]]
        '''
        if not callable(actionCallback):
            raise TypeError('actionCallback must be a callable')
        if updateCallback and not callable(updateCallback):
            raise TypeError('updateCallback must be a callable if given')
        self.actionCallback = actionCallback
        self.updateCallback = updateCallback
        self.defaultText = str(defaultText)

    def Update(self, action, context):
        if self.updateCallback:
            self.updateCallback(action, context)

    def Do(self, context):
        self.actionCallback(context)


class MenuBuilder(object):
    '''Container class for a menu definition.'''
    def __init__(self, name, actions):
        '''
        Parameters
        ----------
        name : str
        actions : List[Union[MenuAction, Type[MenuAction]]]
        '''
        name = name.strip()
        assert name
        self.name = name
        actionInstances = []
        for action in actions:
            if isinstance(action, (MenuAction, _MenuSeparator)):
                actionInstances.append(action)
            elif isclass(action) and \
                    (action is _MenuSeparator or issubclass(action, MenuAction)):
                actionInstances.append(action())
            else:
                raise TypeError('Invalid action {0!r}: an instance or subclass '
                                'of MenuAction is required'.format(action))
        self.actions = actionInstances

    def Build(self, context, parent=None):
        '''Build and return a new `QMenu` instance using the current list of
        actions and the given context, and parented to the given Qt parent.

        Returns None if the resulting menu is empty.

        Parameters
        ----------
        context : Context
        parent : Optional[QtWidgets.QWidget]

        Returns
        -------
        Optional[QtWidgets.QMenu]
        '''
        menu = QtWidgets.QMenu(self.name, parent)
        for action in self.actions:
            action.AddToMenu(menu, context)
        if not menu.isEmpty():
            return menu


class ContextMenuMixin(object):
    '''Mix this class in with a widget to bind a context menu to it.'''
    def __init__(self, contextMenuActions, contextProvider=None, parent=None):
        '''
        Parameters
        ----------
        contextMenuActions : List[MenuAction]
        contextProvider : Optional[Any]
            Object which implements a `GetMenuContext` method. If None,
            `self.GetMenuContext` must be reimplemented.
        parent : Optional[QtWidgets.QWidget]
        '''
        super(ContextMenuMixin, self).__init__(parent=parent)
        assert isinstance(self, QtWidgets.QWidget)
        self._contextProvider = contextProvider
        self._contextMenuBuilder = MenuBuilder('_context_', contextMenuActions)

    # Qt methods ---------------------------------------------------------------
    def contextMenuEvent(self, event):
        context = self.GetMenuContext()
        menu = self._contextMenuBuilder.Build(context, parent=self)
        if menu:
            menu.exec_(event.globalPos())
            event.accept()

    # Custom methods -----------------------------------------------------------
    def GetMenuContext(self):
        # type: () -> Context
        '''Override this to return contextual information to your menu actions.

        Returns
        -------
        Context
        '''
        if self._contextProvider is not None:
            return self._contextProvider.GetMenuContext()
        raise NotImplementedError('No context provider set and GetMenuContext '
                                  'not reimplemented')


class MenuBarBuilder(object):
    '''Creates a menu bar that can be added to UIs'''
    def __init__(self, contextProvider, menuBuilders=None, parent=None):
        # type: (Any, Optional[QtWidgets.QWidget]) -> None
        '''
        Parameters
        ----------
        contextProvider : Any
            Object which implements a `GetMenuContext` method.
        menuBuilders : Optional[Iterable[MenuBuilder]]
            MenuBuilder instances to add to the menu bar.
        parent : Optional[QtWidgets.QWidget]
            Optional parent for the created `QMenuBar`.
        '''
        self._contextProvider = contextProvider
        self._menus = {}  # type: Dict[str, QtWidgets.QMenu]
        self._menuBuilders = {}  # type: Dict[str, MenuBuilder]
        self._menuBar = QtWidgets.QMenuBar(parent=parent)
        if menuBuilders:
            for builder in menuBuilders:
                self.AddMenu(builder)

    @property
    def menuBar(self):
        return self._menuBar

    def _menuAboutToShow(self, menuName):
        '''Slot function called when an owned menu is about to be shown. This
        dispatches `Update` calls to each `QAction`'s associated `MenuAction`
        instance.
        '''
        menu = self._menus[menuName]
        context = self._contextProvider.GetMenuContext()
        for action in menu.actions():
            if action.isSeparator():
                continue
            actionData = action.data()
            if actionData and isinstance(actionData, MenuAction):
                actionData.Update(action, context)

    def AddMenu(self, menuBuilder):
        '''Register a new menu from a `MenuBuilder`.

        Parameters
        ----------
        menuBuilder : MenuBuilder

        Returns
        -------
        bool
            Whether a new menu was added to the menu bar.
        '''
        name = menuBuilder.name
        if name in self._menus:
            raise ValueError('A menu named %s already exists' % name)
        context = self._contextProvider.GetMenuContext()
        menu = menuBuilder.Build(context, parent=self._menuBar)
        if menu:
            self._menuBar.addMenu(menu)
            menu.aboutToShow.connect(partial(self._menuAboutToShow, name))
            self._menus[name] = menu
            self._menuBuilders[name] = menuBuilder
            return True
        return False

    def GetMenu(self, name):
        # type: (str) -> Optional[QtWidgets.QMenu]
        '''Get a registered menu by name.

        Parameters
        ----------
        name : str

        Returns
        -------
        Optional[QtWidgets.QMenu]
        '''
        return self._menus.get(name)

    def GetMenuBuilder(self, name):
        # type: (str) -> Optional[MenuBuilder]
        '''Get a registered menu builder by name.

        Parameters
        ----------
        name : str

        Returns
        -------
        Optional[MenuBuilder]
        '''
        return self._menuBuilders.get(name)