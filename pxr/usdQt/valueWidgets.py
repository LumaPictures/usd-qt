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

"""
A Note on `None`
================

This module aims to provide editors that are compatable with any
`VtValue`s/`SdfValueTypeName`s that may appear in a Usd file. That means that
`None` may be a value that needs to be handled by a widget's SetValue (as
`None` may be returned by an attribute's Get). At the same time, calling Set
with a value of None will raise an Exception, so value editors cannot not
return `None` from GetValue. When values are not explicitly defined (e.g. an
empty numeric value, we prefer to map the undefined field to the type's
`VtZero` value. It may be tempting to try and equate a SetValue with a Block or
a Clear, but that may be ambiguous.

In short, editor widgets MUST handle be able to handle `None` as an argument to
SetValue, and NEVER return `None` from GetValue.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools

from ._Qt import QtCore, QtWidgets, QtGui

from pxr import Gf, Tf, Sdf

if False:
    from typing import *


class _ValueEditMetaclass(type(QtWidgets.QWidget)):
    """Metaclass for `_ValueEdit`

    Qt user properties are the magic that allows for the editors to leverage a
    lot of default Qt behavior with respect to item delegates.

    If 'valueType' is not `None`, then you MUST reimplement GetValue and
    SetValue. Ideally, this would be achieved via inheritance or python
    decorators, but the user property is defined via a metaclass in PySide, so
    we need to approach the problem this way.
    """
    def __new__(meta, name, bases, clsAttributes):
        valueType = clsAttributes.get('valueType', None)
        if valueType is not None:
            if 'GetValue' in clsAttributes:
                getter = clsAttributes['GetValue']
            else:
                for base in bases:
                    if hasattr(base, 'GetValue'):
                        getter = base.GetValue
                        break
                else:
                    raise NotImplementedError(
                        "GetValue must be reimplemented by class or parent.")
            if 'SetValue' in clsAttributes:
                setter = clsAttributes['SetValue']
            else:
                for base in bases:
                    if hasattr(base, 'SetValue'):
                        setter = base.SetValue
                        break
                else:
                    raise NotImplementedError(
                        "SetValue must be reimplemented by class or parent.")
            clsAttributes['value'] = QtCore.Property(
                valueType, getter, setter, user=True)
            # NOTE: We're supposed to be able to declare a notify signal in the
            # Qt property declaration.  I haven't gotten it working so I've been
            # manually defining it in each SetValue method.  We should
            # reevaluate this approach to declaring the value user property as
            # it is a little convoluted.
        return super(_ValueEditMetaclass, meta).__new__(
            meta, name, bases, clsAttributes)


class _ValueEdit(QtWidgets.QWidget):
    """Infers Qt user property called 'value' from class variable 'valueType'.

    Subclasses must set 'valueType' to be not None and implement 'GetValue',
    'SetValue', and 'IsChanged'.
    """
    __metaclass__ = _ValueEditMetaclass

    valueType = None

    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(_ValueEdit, self).__init__(parent=parent)

    def GetValue(self):
        raise NotImplementedError

    def SetValue(self, value):
        raise NotImplementedError

    def IsChanged(self):
        # type: () -> bool
        """Returns whether the widget should be considered changed by delegates.

        There are several actions that can trigger setModelData in the
        ValueDelegate. A custom IsChanged allows us to filter those out by
        limiting the edits that will be considered a change.
        (It would be nice to remove this if possible.)

        Returns
        -------
        bool
        """
        raise NotImplementedError

    def _SetupLayoutSpacing(self, layout):
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)


class _LineEdit(_ValueEdit):
    """Parent class for any ValueEdit that contains one or more QLineEdits"""
    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(_LineEdit, self).__init__(parent=parent)
        self._changed = False

    def _SetupLineEdit(self, lineEdit):
        lineEdit.returnPressed.connect(self._OnReturnPressed)
        lineEdit.textEdited.connect(self._OnTextEdited)
        lineEdit.setFrame(False)

    def _OnReturnPressed(self):
        self._changed = True

    def _OnTextEdited(self, _):
        self._changed = True

    def IsChanged(self):
        """Return true if return has been pressed or text has been edited.

        See _ValueEdit.IsChanged for more information.
        """
        return self._changed


class _ComboEdit(_ValueEdit):
    """Parent class for any ValueEdit that contains a QComboBox"""
    def __init__(self, choices, parent=None):
        # type: (List[str], Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        choices : List[str]
        parent : Optional[QtWidgets.QWidget]
        """
        super(_ComboEdit, self).__init__(parent=parent)
        self._changed = False
        self._comboBox = QtWidgets.QComboBox(self)
        self._comboBox.addItems(choices)
        self._comboBox.activated.connect(self._OnActivated)
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.addWidget(self._comboBox)
        self._SetupLayoutSpacing(self._layout)
        self.setFocusProxy(self._comboBox)
        self.setLayout(self._layout)

    def _OnActivated(self, _):
        self._changed = True
        self.editFinished.emit()

    def IsChanged(self):
        """Return true if an item has been activated.

        See _ValueEdit.IsChanged for more information.
        """
        return self._changed

    editFinished = QtCore.Signal()


class _NumericEdit(_LineEdit):
    """Base class for single line edit that contains a number.

    Values can be limited via an option min and max value .Objects inheriting
    from _NumericEdit should set the 'valueType' with the python numeric type
    as well as a QValidator 'validatorType' class variable.
    """
    valueType = None
    validatorType = None

    def __init__(self, minValue=None, maxValue=None, parent=None):
        # type: (Optional[Union[int, float]], Optional[Union[int, float]], Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        minValue : Optional[Union[int, float]]
        maxValue : Optional[Union[int, float]]
        parent : Optional[QtWidgets.QWidget]
        """
        super(_NumericEdit, self).__init__(parent=parent)

        self._lineEdit = QtWidgets.QLineEdit(self)
        self._validator = self.validatorType(self)
        self._lineEdit.setValidator(self._validator)
        if minValue:
            self._validator.setBottom(minValue)
        if maxValue:
            self._validator.setTop(maxValue)
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.addWidget(self._lineEdit)
        self._SetupLayoutSpacing(self._layout)
        self.setLayout(self._layout)
        self.setFocusProxy(self._lineEdit)

        self._SetupLineEdit(self._lineEdit)

    def GetValue(self):
        text = self._lineEdit.text()
        if text:
            return self.valueType(text)
        return 0.0

    def SetValue(self, value):
        if value is None:
            self._lineEdit.clear()
            return
        value = str(value)
        if self._validator.validate(value, 0)[0] != QtGui.QValidator.Acceptable:
            raise ValueError("%s not accepted by validator." % value)
        self._lineEdit.setText(value)


class _VecEdit(_LineEdit):
    """Base class for a line edit per component of a GfVec*

    No custom implementation of Get and Set value are required.
    You can effectively treat this is a C++ templated class where the template
    parameters are the three class parameters.

    'valueType' is the GfVec type. 'scalarType' (ie. int, float) is the type of
    the individual elements. 'validatorType' is a sublcass of QValidator
    used for 'scalarType' validation.
    """
    valueType = None
    scalarType = None
    validatorType = None

    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(_VecEdit, self).__init__(parent=parent)
        self._layout = QtWidgets.QHBoxLayout()
        self._editors = []

        self._validator = self.validatorType()

        for index in xrange(self.valueType.dimension):
            self._editors.append(QtWidgets.QLineEdit(self))
            self._editors[-1].setValidator(self._validator)
            self._layout.addWidget(self._editors[-1])
            if index != 0:
                self.setTabOrder(self._editors[-2], self._editors[-1])
            self._SetupLineEdit(self._editors[-1])
        self.setTabOrder(self._editors[-1], self._editors[0])

        self._SetupLayoutSpacing(self._layout)
        self.setLayout(self._layout)
        self.setFocusProxy(self._editors[0])

    def GetValue(self):
        text = (self._editors[i].text()
                for i in xrange(self.valueType.dimension))
        return self.valueType(*(self.scalarType(t) if t else 0.0 for t in text))

    def SetValue(self, value):
        if value is None:
            for index in xrange(self.valueType.dimension):
                self._editors[index].clear()
            return
        if len(value) != self.valueType.dimension:
            raise ValueError("Input length %i does not match expected length "
                             "%i", len(value), self.valueType.dimension)
        for index in xrange(self.valueType.dimension):
            if value[index] is None:
                raise ValueError("Value at %i is None", index)
            string = str(value[index])
            if self._validator.validate(string, 0)[0] != QtGui.QValidator.Acceptable:
                raise ValueError(
                    "%s (at index %i) not accepted by validator." %
                    (string, index))
            self._editors[index].setText(string)


class _MatrixEdit(_LineEdit):
    """Base class for a line edit per component of a GfMatrix*

    No custom implementation of Get and Set value are required.
    You can effectively treat this is a C++ templated class where the template
    parameters are the three class parameters.

    'valueType' is the GfVec type. 'scalarType' (ie. int, float) is the type of
    the individual elements. 'validatorType' is a sublcass of QValidator
    used for 'scalarType' validation.
    """
    valueType = None
    scalarType = None
    validatorType = None

    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(_MatrixEdit, self).__init__(parent)
        self._layout = QtWidgets.QGridLayout(self)
        self._editors = []
        self._validator = self.validatorType()

        for row in xrange(self.valueType.dimension[0]):
            for column in xrange(self.valueType.dimension[1]):
                self._editors.append(QtWidgets.QLineEdit(self))
                self._editors[-1].setValidator(self._validator)
                self._layout.addWidget(self._editors[-1], row, column)
                self._SetupLineEdit(self._editors[-1])
                if row != 0 and column != 0:
                    self.setTabOrder(self._editors[-2], self._editors[-1])
        self.setTabOrder(self._editors[-1], self._editors[0])

        self.setFocusProxy(self._editors[0])
        # self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setLayout(self._layout)
        self._SetupLayoutSpacing(self._layout)

    def _GetIndex(self, row, column):
        return row * self.valueType.dimension[1] + column

    def GetValue(self):
        text = (e.text() for e in self._editors)
        return self.valueType(*(self.scalarType(t) if t else 0.0 for t in text))

    def SetValue(self, value):
        numRows = self.valueType.dimension[0]
        numColumns = self.valueType.dimension[1]
        if value is None:
            for e in self._editors:
                e.clear()
            return
        if len(value) != numRows:
            raise ValueError(
                "Input row size %i does not match expected length %i",
                len(value), numRows)
        for row in xrange(numRows):
            if type(value) is str:
                raise TypeError("Row cannot be string")
            if len(value[row]) != numColumns:
                raise ValueError("Input column size %i does not match expected "
                                 "length %i", len(value[row]), numColumns)
            for column in xrange(numColumns):
                if value[row][column] is None:
                    raise ValueError("Value at (%i, %i) is None", row, column)
                string = str(value[row][column])
                if self._validator.validate(string, 0)[0] != QtGui.QValidator.Acceptable:
                    raise ValueError(
                        "%s (at %i, %i) not accepted by validator." %
                        (string, row, column))
                self._editors[self._GetIndex(row, column)].setText(string)


class IntEdit(_NumericEdit):
    valueType = int
    validatorType = QtGui.QIntValidator


class FloatEdit(_NumericEdit):
    valueType = float
    validatorType = QtGui.QDoubleValidator


class Vec3dEdit(_VecEdit):
    valueType = Gf.Vec3d
    scalarType = float
    validatorType = QtGui.QDoubleValidator


class Vec3iEdit(_VecEdit):
    valueType = Gf.Vec3i
    scalarType = int
    validatorType = QtGui.QIntValidator


class Vec2dEdit(_VecEdit):
    valueType = Gf.Vec2d
    scalarType = float
    validatorType = QtGui.QDoubleValidator


class Vec2iEdit(_VecEdit):
    valueType = Gf.Vec2i
    scalarType = int
    validatorType = QtGui.QIntValidator


class Vec4dEdit(_VecEdit):
    valueType = Gf.Vec4d
    scalarType = float
    validatorType = QtGui.QDoubleValidator


class Vec4iEdit(_VecEdit):
    valueType = Gf.Vec4i
    scalarType = int
    validatorType = QtGui.QIntValidator


class Matrix4dEdit(_MatrixEdit):
    valueType = Gf.Matrix4d
    scalarType = float
    validatorType = QtGui.QDoubleValidator


class Matrix3dEdit(_MatrixEdit):
    valueType = Gf.Matrix3d
    scalarType = float
    validatorType = QtGui.QDoubleValidator


class Matrix2dEdit(_MatrixEdit):
    valueType = Gf.Matrix2d
    scalarType = float
    validatorType = QtGui.QDoubleValidator


class TextComboEdit(_ComboEdit):
    valueType = str

    def __init__(self, allowedValues, parent=None):
        # type: (List[str], Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        allowedValues : List[str]
        parent : Optional[QtWidgets.QWidget]
        """
        super(TextComboEdit, self).__init__(allowedValues, parent=parent)
        self._reluctantValues = []

    def GetValue(self):
        return str(self._comboBox.currentText())

    def SetValue(self, value):
        value = value if value else ''
        index = self._comboBox.findText(value)
        if index < 0:
            self._comboBox.addItem(value)
            index = self._comboBox.findText(value)
            self._reluctantValues.append(value)
            assert(index >= 0)
        self._comboBox.setCurrentIndex(index)


class BoolEdit(_ComboEdit):
    valueType = bool

    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(BoolEdit, self).__init__(['false', 'true'], parent)

    def GetValue(self):
        return self._comboBox.currentText() == "true"

    def SetValue(self, value):
        if value:
            self._comboBox.setCurrentIndex(1)
        else:
            self._comboBox.setCurrentIndex(0)


class StringEdit(_LineEdit):
    valueType = str

    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(StringEdit, self).__init__(parent)
        self._lineEdit = QtWidgets.QLineEdit(self)
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.addWidget(self._lineEdit)
        self._SetupLayoutSpacing(self._layout)
        self.setFocusProxy(self._lineEdit)
        self.setLayout(self._layout)
        self._SetupLineEdit(self._lineEdit)

    def GetValue(self):
        return str(self._lineEdit.text())

    def SetValue(self, value):
        if value is None:
            self._lineEdit.clear()
            return
        self._lineEdit.setText(value)


class AssetEdit(_LineEdit):
    valueType = Sdf.AssetPath

    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(AssetEdit, self).__init__(parent)
        self._lineEdit = QtWidgets.QLineEdit(self)
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.addWidget(self._lineEdit)
        self._SetupLayoutSpacing(self._layout)
        self.setFocusProxy(self._lineEdit)
        self.setLayout(self._layout)
        self._SetupLineEdit(self._lineEdit)

    def GetValue(self):
        text = str(self._lineEdit.text())
        return Sdf.AssetPath(text) if text else Sdf.AssetPath()

    def SetValue(self, value):
        if value is None:
            self._lineEdit.clear()
            return
        self._lineEdit.setText(value.path)


class PathValidator(QtGui.QValidator):
    """A PathValidator ensures that the path is a valid SdfPath"""
    def __init__(self, parent=None):
        # type: (Optional[QtCore.QObject]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtCore.QObject]
        """
        super(PathValidator, self).__init__(parent)

    def validate(self, value, pos):
        if value != '' and not Sdf.Path.IsValidPathString(value):
            return (QtGui.QValidator.Intermediate, value, pos)
        return (QtGui.QValidator.Acceptable, value, pos)


class PathEdit(_LineEdit):
    valueType = Sdf.Path

    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(PathEdit, self).__init__(parent)
        self._validator = PathValidator()
        self._lineEdit = QtWidgets.QLineEdit(self)
        self._lineEdit.setValidator(self._validator)
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.addWidget(self._lineEdit)
        self._SetupLayoutSpacing(self._layout)
        self.setFocusProxy(self._lineEdit)
        self.setLayout(self._layout)
        self._SetupLineEdit(self._lineEdit)

    def GetValue(self):
        text = str(self._lineEdit.text())
        return Sdf.Path(text) if text else Sdf.Path()

    def SetValue(self, value):
        if value is None:
            self._lineEdit.clear()
            return
        value = str(value)
        if self._validator.validate(value, 0)[0] != QtGui.QValidator.Acceptable:
            raise ValueError("%s not accepted by validator." % value)
        self._lineEdit.setText(value)


class _ColorButton(QtWidgets.QPushButton):
    """The color button stores its color in DISPLAY space not LINEAR space"""
    class _PainterContext(object):
        def __init__(self, widget):
            self.widget = widget
            self._painter = None

        def __enter__(self):
            self._painter = QtGui.QPainter()
            self._painter.begin(self.widget)
            return self._painter

        def __exit__(self, *args):
            self._painter.end()

    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(_ColorButton, self).__init__(parent)
        self._color = QtGui.QColor(255, 255, 255)

    @property
    def displayColor(self):
        """Returns color in display space"""
        return self._color

    @displayColor.setter
    def displayColor(self, color):
        """Set color in display space"""
        if self._color == color:
            return

        self._color = color
        self.update()

    def paintEvent(self, event):
        super(_ColorButton, self).paintEvent(event)

        # Paint a subset of the button the defined color
        with self._PainterContext(self) as painter:
            painter.setPen(QtGui.QPen(self._color))
            painter.setBrush(QtGui.QBrush(self._color))

            bounds = self.geometry()
            area = QtCore.QRect(5, 5, bounds.width() - 11, bounds.height() - 11)
            painter.drawRect(area)


class _ColorEdit(_ValueEdit):
    """Stores a color in LINEAR space"""
    valueType = None

    def __init__(self, parent=None):
        # type: (Optional[QtWidgets.QWidget]) -> None
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(_ColorEdit, self).__init__(parent)
        self._layout = QtWidgets.QHBoxLayout()
        self._SetupLayoutSpacing(self._layout)
        self._colorButton = _ColorButton()
        self._colorButton.setMaximumWidth(30)
        self._colorButton.clicked.connect(self._OnPushed)
        self._valueWidget = valueTypeMap[Tf.Type.Find(self.valueType)]()

        self._layout.addWidget(self._colorButton)
        self._layout.addWidget(self._valueWidget)
        self.setLayout(self._layout)

        # TODO: There should be a way to more directly identify if one of the
        # numeric widgets have changed.
        for child in self._valueWidget.children():
            if isinstance(child, QtWidgets.QLineEdit):
                child.editingFinished.connect(self._SetButtonColor)

        self._changed = False

    def _SetButtonColor(self):
        assert(self.valueType.dimension in (3, 4))
        value = Gf.ConvertLinearToDisplay(self.value)
        self._colorButton.displayColor = QtGui.QColor(
            *[255 * v for v in value])

    def _OnPushed(self):
        if self.valueType.dimension in (3, 4):
            options = QtWidgets.QColorDialog.ColorDialogOptions()
            displayColor = QtGui.QColor(*[255 * v for v in
                                          Gf.ConvertLinearToDisplay(self.value)])
            if self.valueType.dimension == 4:
                options = QtWidgets.QColorDialog.ShowAlphaChannel
            newColor = QtWidgets.QColorDialog.getColor(
                displayColor, self, unicode(self.valueType), options)
            if newColor.isValid():
                if self.valueType.dimension == 3:
                    value = (newColor.red(), newColor.green(), newColor.blue())
                elif self.valueType.dimension == 4:
                    value = (newColor.red(), newColor.green(),
                             newColor.blue(), newColor.alpha())
                value = self.valueType(*(v/255.0 for v in value))
                value = Gf.ConvertDisplayToLinear(value)
                self.value = self.valueType(*(round(v, 2) for v in value))
                self._changed = True

    def GetValue(self):
        return self._valueWidget.value

    def SetValue(self, value):
        self._valueWidget.value = value
        self._SetButtonColor()

    def IsChanged(self):
        return self._valueWidget.IsChanged() or self._changed


class Color3dEdit(_ColorEdit):
    valueType = Gf.Vec3d


class Color4dEdit(_ColorEdit):
    valueType = Gf.Vec4d


colorTypeMap = {
    Tf.Type.Find(Gf.Vec3f): Color3dEdit,
    Tf.Type.Find(Gf.Vec3d): Color3dEdit,
    Tf.Type.Find(Gf.Vec3h): Color3dEdit,
    Tf.Type.Find(Gf.Vec4f): Color4dEdit,
    Tf.Type.Find(Gf.Vec4d): Color4dEdit,
    Tf.Type.Find(Gf.Vec4h): Color4dEdit,
}

valueTypeMap = {
    Tf.Type.FindByName('string'): StringEdit,
    Tf.Type.FindByName('TfToken'): StringEdit,
    Tf.Type.FindByName('SdfAssetPath'): AssetEdit,
    Tf.Type.FindByName('SdfPath'): PathEdit,
    Tf.Type.FindByName('unsigned char'):
        functools.partial(IntEdit, minValue=0, maxValue=(2 << (8 - 1)) - 1),
    Tf.Type.FindByName('unsigned int'):
        functools.partial(IntEdit, minValue=0, maxValue=(2 << (32 - 1)) - 1),
    Tf.Type.FindByName('unsigned long'):
        functools.partial(IntEdit, minValue=0, maxValue=(2 << (64 - 1)) - 1),
    Tf.Type.FindByName('int'): functools.partial(
        IntEdit, minValue=-(2 << (32 - 1 - 1)), maxValue=(2 << (32 - 1 - 1)) - 1),
    Tf.Type.FindByName('long'): functools.partial(
        IntEdit, minValue=-(2 << (64 - 1 - 1)), maxValue=(2 << (64 - 1 - 1)) - 1),
    Tf.Type.FindByName('half'): FloatEdit,
    Tf.Type.FindByName('float'): FloatEdit,
    Tf.Type.FindByName('double'): FloatEdit,
    Tf.Type.Find(Gf.Vec2i): Vec2iEdit, Tf.Type.Find(Gf.Vec2f): Vec2dEdit,
    Tf.Type.Find(Gf.Vec2d): Vec2dEdit, Tf.Type.Find(Gf.Vec2h): Vec2dEdit,
    Tf.Type.Find(Gf.Vec3i): Vec3iEdit, Tf.Type.Find(Gf.Vec3f): Vec3dEdit,
    Tf.Type.Find(Gf.Vec3f): Vec3dEdit, Tf.Type.Find(Gf.Vec3d): Vec3dEdit,
    Tf.Type.Find(Gf.Vec4i): Vec4iEdit, Tf.Type.Find(Gf.Vec4f): Vec4dEdit,
    Tf.Type.Find(Gf.Vec4h): Vec4dEdit, Tf.Type.Find(Gf.Vec4d): Vec4dEdit,
    Tf.Type.Find(Gf.Matrix2f): Matrix2dEdit,
    Tf.Type.Find(Gf.Matrix2d): Matrix2dEdit,
    Tf.Type.Find(Gf.Matrix3f): Matrix3dEdit,
    Tf.Type.Find(Gf.Matrix3d): Matrix3dEdit,
    Tf.Type.Find(Gf.Matrix4f): Matrix4dEdit,
    Tf.Type.Find(Gf.Matrix4d): Matrix4dEdit,
}

floatTypes = {Tf.Type.FindByName('half'),
              Tf.Type.FindByName('float'), Tf.Type.FindByName('double')}
vecTypes = {Tf.Type.Find(Gf.Vec2i), Tf.Type.Find(Gf.Vec2f),
            Tf.Type.Find(Gf.Vec2d), Tf.Type.Find(Gf.Vec2h),
            Tf.Type.Find(Gf.Vec3i), Tf.Type.Find(Gf.Vec3f),
            Tf.Type.Find(Gf.Vec3d), Tf.Type.Find(Gf.Vec3h),
            Tf.Type.Find(Gf.Vec4i), Tf.Type.Find(Gf.Vec4f),
            Tf.Type.Find(Gf.Vec4d), Tf.Type.Find(Gf.Vec4h)}
matrixTypes = {Tf.Type.Find(Gf.Matrix2f), Tf.Type.Find(Gf.Matrix2d),
               Tf.Type.Find(Gf.Matrix3f), Tf.Type.Find(Gf.Matrix3d),
               Tf.Type.Find(Gf.Matrix4f), Tf.Type.Find(Gf.Matrix4d)}


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    layout = QtWidgets.QVBoxLayout()

    widget = FloatEdit()
    widget.value = .5
    layout.addWidget(widget)

    widget1 = Vec3dEdit()
    widget1.value = (1, 2, 3)
    layout.addWidget(widget1)

    widget2 = StringEdit()
    widget2.value = "one"
    layout.addWidget(widget2)

    widget3 = PathEdit()
    widget3.value = Sdf.Path("/World")
    layout.addWidget(widget3)

    widget4 = Color3dEdit()
    widget4.value = (.5, .5, .5)
    layout.addWidget(widget4)

    mainWidget = QtWidgets.QWidget()
    mainWidget.setLayout(layout)
    mainWidget.show()

    sys.exit(app.exec_())
