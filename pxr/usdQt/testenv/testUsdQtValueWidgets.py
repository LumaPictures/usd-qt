#!/pxrpythonsubst
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

from __future__ import print_function
from __future__ import absolute_import

import os
import unittest

import pxr.UsdQt.valueWidgets as valueWidgets
from pxr import Gf, Sdf
from pxr.UsdQt._Qt import QtCore, QtWidgets


def setUpModule():
    global app
    app = QtWidgets.QApplication([])


class TestMetaclass(unittest.TestCase):

    def testObject(self):
        class MyEditor(QtWidgets.QWidget):
            __metaclass__ = valueWidgets._ValueEditMetaclass
            valueType = float

            def __init__(self):
                super(MyEditor, self).__init__()
                self.__value = 5

            def GetValue(self):
                return self.__value

            def SetValue(self, value):
                self.__value = value
                x = MyEditor()
                self.assertEqual(x.value, 5)
                self.assertEqual(x.metaObject().userProperty().name(), 'value')

    def testNoValueType(self):
        """verify that the metaclass doesn't fail if value type isn't set"""
        class MyEditor(QtWidgets.QWidget):
            __metaclass__ = valueWidgets._ValueEditMetaclass

            def __init__(self):
                super(MyEditor, self).__init__()
                x = MyEditor()
                self.assertEqual(x.metaObject().userProperty().name(), None)

    def testValueTypeIsNone(self):
        class MyEditor(QtWidgets.QWidget):
            __metaclass__ = valueWidgets._ValueEditMetaclass
            valueType = None

            def __init__(self):
                super(MyEditor, self).__init__()
                x = MyEditor()
                self.assertEqual(x.metaObject().userProperty().name(), None)


class _Base:
    """
    Namespace to prevent test from being executed
    """
    class TestValueEdit(unittest.TestCase):
        AttributeErrorValues = []

        def setUp(self):
            self.longMessage = True

        def testUserProperty(self):
            """verify the Qt user property has been setup.
            using the user property gets a lot of nice behavior for free
            when interacting with Qt ItemModels so its important that
            all our widgets have this setup correctly.
            """
            widget = self.Widget()
            self.assertEqual(widget.metaObject().userProperty().name(), 'value')

        def testSuccess(self):
            """verifying that the widget can set and get a value without loss of equality"""
            widget = self.Widget()
            for value in self.SuccessValues:
                widget.value = value
                self.assertEqual(widget.value, value)

        def testSuccessCasted(self):
            """verify that the widget can set values, but there may be some transformation

            ie. it may go in as a string and out as an int, so its not strictly equal
            to the orignal value
            """
            widget = self.Widget()
            for value in self.SuccessCastedValues:
                widget.value = value
                self.assertEqual(widget.value, self.SuccessCastedValues[value])

        def testValueErrors(self):
            """verify that some values are unsettable [raise ValueError]"""
            widget = self.Widget()
            for value in self.ValueErrorValues:
                with self.assertRaises(ValueError):
                    widget.value = value

        def testTypeErrors(self):
            """verify that some values are unsettable [raise TypeError]"""
            widget = self.Widget()
            for value in self.TypeErrorValues:
                with self.assertRaises(TypeError):
                    widget.value = value

        def testAttributeErrors(self):
            """verify that some values are unsettable [raise TypeError]"""
            widget = self.Widget()
            for value in self.AttributeErrorValues:
                with self.assertRaises(AttributeError):
                    widget.value = value

        def testKeySequence(self):
            """verify a series of keystrokes when the widget has focus"""
            if 'PXR_USDQT_ALLOW_TEST_KEYS' in os.environ and \
                    os.environ['PXR_USDQT_ALLOW_TEST_KEYS'] != '0':
                from pixar.UsdQt._Qt import QtTest
                for sequence in self.KeySequences:
                    widget = self.Widget()
                    widget.show()
                    widget.window().activateWindow()
                    widget.setFocus(QtCore.Qt.MouseFocusReason)
                    for keyClick in sequence:
                        focusWidget = widget.window().focusWidget()
                    QtTest.QTest.keyClick(focusWidget, keyClick)
                    self.assertEqual(widget.value, self.KeySequences[sequence])


class TestStringEdit(_Base.TestValueEdit):
    Widget = valueWidgets.StringEdit
    SuccessValues = ['abcd', '', '-490', 'a', 'the quick brown fox']
    KeySequences = {('a', 'b', 'c', 'd', QtCore.Qt.Key_Return): 'abcd',
                    ('a', 'b', 'c', 'd',): 'abcd'}
    SuccessCastedValues = {None: ''}
    ValueErrorValues = []
    TypeErrorValues = [['a', 'b', 'c'], -490, 10.0]


class TestPathEdit(_Base.TestValueEdit):
    Widget = valueWidgets.PathEdit
    SuccessValues = [Sdf.Path('/World'), Sdf.Path(),
                     Sdf.Path('Relative'), Sdf.Path('/World.property')]
    KeySequences = {}
    SuccessCastedValues = {'/World': Sdf.Path('/World'), '': Sdf.Path(),
                           '/World/Child': Sdf.Path('/World/Child'),
                           None: Sdf.Path.emptyPath}
    # TODO: Consider implementing fixup to cleanup /World/Child/
    ValueErrorValues = ['//World', '////', '/World..property', '/World/Child/']
    TypeErrorValues = []


class TestIntEdit(_Base.TestValueEdit):
    Widget = valueWidgets.IntEdit
    SuccessValues = [1, -10000, 10000, 123456789, long(10000)]
    KeySequences = {('1', '0', '0', QtCore.Qt.Key_Return): 100,
                    ('1', '.', '0', '0',): 100,
                    ('1', 'e', 'e', '-', '2',): 12
                    }
    SuccessCastedValues = {"1": 1, None: 0}
    ValueErrorValues = ["-1.0", 'one', 1.0, [1]]
    TypeErrorValues = []


class TestFloatEdit(_Base.TestValueEdit):
    Widget = valueWidgets.FloatEdit
    SuccessValues = [1, 1.0, 1e100, -10000, 10000, 123456789, 1.0, long(10000)]
    KeySequences = {('1', '.', '0', '0', QtCore.Qt.Key_Return): 1.0,
                    ('1', 'e', 'e', '-', '2',): 1e-2}
    SuccessCastedValues = {"1.0": 1, '1e100': 1e100, "-100": -100, "+100": 100,
                           None: 0.0}
    ValueErrorValues = ['one', [1.0], '1e', '-', '+']
    TypeErrorValues = []


class TestVec2dEdit(_Base.TestValueEdit):
    Widget = valueWidgets.Vec2dEdit
    SuccessValues = [Gf.Vec2f(1.0, 2.0), Gf.Vec2d(
        1.0, 2.0), Gf.Vec2h(1.0, 2.0), (1.0, 2.0), [1.0, 2.0]]
    SuccessCastedValues = {('1.0', '2.0'): (1.0, 2.0),
                           ('1e10', 1.0): (1e10, 1.0),
                           None: Gf.Vec2d(0.0)}
    KeySequences = {('1', '.', '0', QtCore.Qt.Key_Tab,
                     '2', '.', '0'): (1.0, 2.0), }
    ValueErrorValues = [(1.0, None), (None, 1.0), ("1.0", "one"),
                        (1.0, 2.0, 3.0), (1.0,), Gf.Vec3f(1.0, 2.0, 3.0), "(1.0, 2.0)"]
    TypeErrorValues = []


class TestMatrix2dEdit(_Base.TestValueEdit):
    Widget = valueWidgets.Matrix2dEdit
    SuccessValues = [Gf.Matrix2f(1.0, 2.0, 3.0, 4.0),
                     Gf.Matrix2d(1.0, 2.0, 3.0, 4.0)]
    SuccessCastedValues = {(('1.0', '2.0'), ('3.0', '4.0')): Gf.Matrix2f(1.0, 2.0, 3.0, 4.0),
                           None: Gf.Matrix2d(0.0)}
    KeySequences = {('1', '.', '0', QtCore.Qt.Key_Tab, '2', '.', '0', QtCore.Qt.Key_Tab,
                     '3', '.', '0', QtCore.Qt.Key_Tab, '4', '.', '0'): Gf.Matrix2f(1.0, 2.0, 3.0, 4.0), }
    ValueErrorValues = [((1.0, None), (None, 1.0)), Gf.Matrix3f(), "(1.0, 2.0)"]
    TypeErrorValues = []


class TestBoolEdit(_Base.TestValueEdit):
    Widget = valueWidgets.BoolEdit
    SuccessValues = [True, False, 1, 0]
    SuccessCastedValues = {None: False, "0": True,
                           "1": True, "one": True, (0,): True, (1,): True}
    KeySequences = {(): False,
                    (QtCore.Qt.Key_Down,): True,
                    (QtCore.Qt.Key_Down, QtCore.Qt.Key_Up): False}
    ValueErrorValues = []
    TypeErrorValues = []


class TestTextComboBoxEdit(_Base.TestValueEdit):
    Widget = lambda self: valueWidgets.TextComboEdit(
        ['value1', 'value2', 'value3'])
    SuccessValues = ['value1', 'value2', 'value3', 'invalidValue']
    SuccessCastedValues = {None: ''}
    KeySequences = {(): 'value1',
                    (QtCore.Qt.Key_Down,): 'value2',
                    (QtCore.Qt.Key_Down, QtCore.Qt.Key_Up): 'value1',
                    (QtCore.Qt.Key_Down, QtCore.Qt.Key_Down): 'value3'}
    ValueErrorValues = []
    TypeErrorValues = [1.0, 1, ['mylist'], ('bla',)]


class TestColor4dEdit(_Base.TestValueEdit):
    Widget = valueWidgets.Color4dEdit
    SuccessValues = [Gf.Vec4d(.1, .2, .3, .4), (.5, .6, .7, .8)]
    SuccessCastedValues = {None: Gf.Vec4d()}
    KeySequences = {}
    ValueErrorValues = ['red', 'blue', ['red']]
    TypeErrorValues = [1.0, 1]


class TestAssetEdit(_Base.TestValueEdit):
    Widget = valueWidgets.AssetEdit
    SuccessValues = [Sdf.AssetPath('/path/to/file.ext'),
                     Sdf.AssetPath('./relativePath.ext')]
    SuccessCastedValues = {None: Sdf.AssetPath()}
    KeySequences = {}
    ValueErrorValues = []
    TypeErrorValues = []
    AttributeErrorValues = [1.0, 1, '/string/path.ext']

if __name__ == '__main__':
    unittest.main(verbosity=2)
