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


def passSingleSelection(cls):
    '''
    ContextMenuAction decorator that will make it so the first selection item
     is passed to the action's do() method.

    Parameters
    ----------
    cls : ContextMenuAction

    Returns
    -------
    ContextMenuAction
    '''
    cls.supportsMultiSelection = False
    return cls


def passMultipleSelection(cls):
    '''
    ContextMenuAction decorator that will make it so the full selection list
     is passed to the action's do() method.

    Parameters
    ----------
    cls : ContextMenuAction

    Returns
    -------
    ContextMenuAction
    '''
    cls.supportsMultiSelection = True
    return cls


class MenuSeparator(object):
    '''Use with Actions to specify a separator when configuring menu actions'''
    pass


class Action(QtCore.QObject):

    def __init__(self, label=None, enable=None, func=None):
        super(Action, self).__init__()
        self._callable = func
        self._label = label
        self._enable = enable


class MenuAction(Action):

    def do(self, builder):
        if self._callable:
            self._callable()
        else:
            raise NotImplementedError('No callable given and no do() method '
                                      'implemented for %s'
                                      % self.__class__.__name__)

    def shouldShow(self, builder):
        return True

    def enable(self, builder):
        '''Returns whether the menu item should be enabled'''
        return True

    def label(self, builder):
        raise NotImplementedError

    def Build(self, builder, menu):
        '''Add action to menu bar (override this for dynamically generated menus)
        '''
        a = menu.addAction(self.label(builder))
        enable = self.enable(builder)
        if enable:
            a.triggered.connect(lambda: self.do(builder))
        a.setEnabled(enable)


class ContextMenuAction(Action):
    '''
    - know how to trigger an action
    - know whether they should be drawn, enabled based on selection
    '''
    def do(self, builder, selection):
        raise NotImplementedError

    def shouldShow(self, builder, selections):
        return bool(selections)

    def enable(self, builder, selections):
        '''Returns whether the menu item should be enabled based on selection'''
        return len(selections) == 1 or self.supportsMultiSelection

    def label(self, builder, selection):
        raise NotImplementedError

    def Build(self, builder, menu, selection):
        '''Add action to menu, override this for dynamically generated menus'''
        a = menu.addAction(self.label(builder, selection))
        enable = self.enable(builder, selection)
        if enable:
            a.triggered.connect(lambda: builder.CallAction(self))
        a.setEnabled(enable)


class ContextMenuBuilder(QtCore.QObject):
    '''
    Class to customize the building of right-click context menus for
    selected view items.
    '''
    def __init__(self, view, actions):
        '''
        Parameters
        ----------
        view : QtGui.QView
        actions : List[ContextMenuActions]
        '''
        super(ContextMenuBuilder, self).__init__()
        self.view = view
        self.actions = actions
        # add any actions here if you want to use their signals
        self.nonMenuActions = []

    @property
    def model(self):
        return self.view.model()

    def DoIt(self, event):
        '''
        Inspect view selection and create context menu.
        
        Views should call this from their contextMenuEvent.
        '''
        selection = self.GetSelection()
        menu = QtWidgets.QMenu(self.view)
        for action in self.actions:
            self.AddAction(menu, action, selection)
        if menu.isEmpty():
            return
        menu.exec_(event.globalPos())
        event.accept()

    def CallAction(self, action):
        '''
        Execute an action and provide it with the current view selection.
        '''
        selection = self.GetSelection()
        if selection:
            if action.supportsMultiSelection:
                return action.do(self, selection)
            return action.do(self, selection[0])
        else:
            return action.do(self)

    def AddAction(self, menu, action, selection):
        '''
        Add action to the context menu if it should be displayed.

        Parameters
        ----------
        menu : QMenu
        action : ContextMenuAction
        selection : List[Selection]
        '''
        if isinstance(action, MenuSeparator):
            menu.addSeparator()
            return
        if not action.shouldShow(self, selection):
            return
        action.Build(self, menu, selection)

    def AddNonMenuAction(self, action):
        '''
        Register an action that doesnt need to be Built or added to a menu
        (Example: double click).

        Parameters
        ----------
        action : ContextMenuAction

        Returns
        -------
        func : callable that you should connect to the appropriate qt signal.
        '''
        self.nonMenuActions.append(action)

        def func():
            self.CallAction(action)

        return func

    def GetSelection(self):
        '''
        Get the Selection list that should be handed to the actions (Uses
        the view's configured selection method by default)
        '''
        return self.view.GetSelection()


class ContextMenuMixin(object):
    '''Mix this class in with a view to bind a menu to a view'''

    def __init__(self, parent=None, contextMenuBuilder=None, contextMenuActions=None):
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
        self._menuBuilder.DoIt(event)

    # Custom methods -----------------------------------------------------------
    def GetSignal(self, name):
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
        '''Override with default context menu actions'''
        raise ValueError('must provide context menu actions for this class')

    @property
    def menuBuilder(self):
        return self._menuBuilder

    def GetSelectedRowItems(self):
        '''
        Returns
        -------
        List[T]
        '''
        indexes = self.selectionModel().selectedRows()
        return [index.internalPointer() for index in indexes]

    def GetSelection(self):
        '''
        Override this to return useful selection objects to your actions.

        Returns
        -------
        List
        '''
        return self.GetSelectedRowItems()


class MenuBarBuilder(object):
    '''Attach a menu bar to a dialog'''

    def __init__(self, dlg, roleGetMenuNames, roleGetMenuActions):
        '''
        Parameters
        ----------
        dlg : QDialog
        roleGetMenuNames : Callable
            Role method that will return menu bar names
        roleGetMenuActions : Callable
            Role method that will return menu bar actions
        '''
        self.dlg = dlg
        self._menuBar = QtWidgets.QMenuBar(dlg)
        self._menus = {}  # type: Dict[str, QtWidgets.QMenu]
        self.AddMenus(roleGetMenuNames(dlg))
        self.actions = roleGetMenuActions(dlg)
        self.PopulateMenus(self.actions)

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

    def AddMenus(self, menus):
        '''Create any menus needed on the bar'''
        for name, text in menus:
            self.AddMenu(name, text)

    def CallAction(self, action):
        '''
        Call the menu action.
        '''
        return action.do(self)

    def AddAction(self, menu, action):
        '''
        Add action to the menu if it should be displayed.

        Parameters
        ----------
        menu : QMenu
        action : MenuAction
        '''
        if isinstance(action, MenuSeparator):
            menu.addSeparator()
            return
        if not action.shouldShow(self):
            return
        action.Build(self, menu)

    def PopulateMenus(self, actions):
        '''Populate Menus in the menu bar'''
        for menuName, menuActions in actions.iteritems():
            menu = self.GetMenu(menuName)
            for action in menuActions:
                self.AddAction(menu, action)


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


def GetId(layer):
    '''Overrideable way to get the unique key used to store the original
    contents of a layer'''
    if isinstance(layer, Sdf.Layer):
        return layer.identifier
    else:
        return layer


UsdQtUtilities.register('GetReferencePath', GetReferencePath)
UsdQtUtilities.register('GetId', GetId)
