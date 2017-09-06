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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools

from ._Qt import QtCore, QtWidgets, QtGui

from pxr import Gf, Tf, Sdf

from . import compatability


class _ValueEditMetaclass(type(QtWidgets.QWidget)):
    """Metaclass used for all subclasses of _ValueEdit
    Qt user properties are the magic that allows for the editors to
    leverage a lot of default Qt behavior with respect to item delegates.
    If 'valueType' is not None, then you MUST declare an implementation of
    GetValue and SetValue.

    Ideally, this would be achieved via inheritance or python decorators,
    but the user property is defined via metaclass in PySide so we need to
    approach the problem this way.
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
                        "GetValue must be defined in class or parent.")
            if 'SetValue' in clsAttributes:
                setter = clsAttributes['SetValue']
            else:
                for base in bases:
                    if hasattr(base, 'GetValue'):
                        setter = base.SetValue
                        break
                else:
                    raise NotImplementedError(
                        "GetValue must be defined in class or parent.")
            clsAttributes['value'] = QtCore.Property(
                valueType, getter, setter, user=True)
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
        super(_ValueEdit, self).__init__(parent=parent)

    def GetValue(self):
        raise NotImplementedError()

    def SetValue(self, value):
        raise NotImplementedError()

    def IsChanged(self):
        """Returns whether the widget should be considered changed by delegates.

        There are several actions that can trigger setModelData in the 
        ValueDelegate.  A custom IsChanged allows us to filter those out by
        limiting the edits that will be considered a change.  
        (It would be nice to remove this if possible.)
        """
        raise NotImplementedError()

    def _SetupLayoutSpacing(self, layout):
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)


class _LineEdit(_ValueEdit):
    """Parent class for any ValueEdit that contains one or more QLineEdits"""

    def __init__(self, parent=None):
        super(_LineEdit, self).__init__(parent=parent)
        self.__changed = False

    def _SetupLineEdit(self, lineEdit):
        lineEdit.returnPressed.connect(self.__OnReturnPressed)
        lineEdit.textEdited.connect(self.__OnTextEdited)
        lineEdit.setFrame(False)

    def __OnReturnPressed(self):
        self.__changed = True

    def __OnTextEdited(self, _):
        self.__changed = True

    def IsChanged(self):
        """Return true if return has been pressed or text has been edited.

        See _ValueEdit.IsChanged for more information.
        """
        return self.__changed


class _ComboEdit(_ValueEdit):
    """Parent class for any ValueEdit that contains a QComboBox"""

    def __init__(self, choices, parent=None):
        super(_ComboEdit, self).__init__(parent=parent)
        self.__changed = False
        self._comboBox = QtWidgets.QComboBox(self)
        self._comboBox.addItems(choices)
        self._comboBox.activated.connect(self.__OnActivated)
        self.__layout = QtWidgets.QHBoxLayout()
        self.__layout.addWidget(self._comboBox)
        self._SetupLayoutSpacing(self.__layout)
        self.setFocusProxy(self._comboBox)
        self.setLayout(self.__layout)

    def __OnActivated(self, _):
        self.__changed = True
        self.editFinished.emit()

    def IsChanged(self):
        """Return true if an item has been activated.

        See _ValueEdit.IsChanged for more information.
        """
        return self.__changed

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
        super(_NumericEdit, self).__init__(parent=parent)

        self.__lineEdit = QtWidgets.QLineEdit(self)
        self.__validator = self.validatorType(self)
        self.__lineEdit.setValidator(self.__validator)
        if minValue:
            self.__validator.setBottom(minValue)
        if maxValue:
            self.__validator.setTop(maxValue)
        self.__layout = QtWidgets.QHBoxLayout()
        self.__layout.addWidget(self.__lineEdit)
        self._SetupLayoutSpacing(self.__layout)
        self.setLayout(self.__layout)
        self.setFocusProxy(self.__lineEdit)

        self._SetupLineEdit(self.__lineEdit)

        # get the preferred string type of the current Qt context
        self._stringType = type(self.__lineEdit.text())

    def GetValue(self):
        return self.valueType(self.__lineEdit.text())

    def SetValue(self, value):
        stringValue = compatability.ResolveString(str(value), self._stringType)
        if self.__validator.validate(stringValue, 0)[0] != QtGui.QValidator.Acceptable:
            raise ValueError("%s not accepted by validator." % stringValue)
        self.__lineEdit.setText(stringValue)


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

    def __init__(self,  parent=None):
        super(_VecEdit, self).__init__(parent=parent)
        self.__layout = QtWidgets.QHBoxLayout()
        self.__editors = []

        self.__validator = self.validatorType()

        for index in xrange(self.valueType.dimension):
            self.__editors.append(QtWidgets.QLineEdit(self))
            self.__editors[-1].setValidator(self.__validator)
            self.__layout.addWidget(self.__editors[-1])
            if index != 0:
                self.setTabOrder(self.__editors[-2], self.__editors[-1])
            self._SetupLineEdit(self.__editors[-1])
        self.setTabOrder(self.__editors[-1], self.__editors[0])

        self._SetupLayoutSpacing(self.__layout)
        self.setLayout(self.__layout)
        self.setFocusProxy(self.__editors[0])
        # get the preferred string type of the current Qt context
        self._stringType = type(self.__editors[0].text())

    def GetValue(self):
        vec = self.valueType()
        for index in xrange(self.valueType.dimension):
            scalar = self.scalarType(self.__editors[index].text())
            vec[index] = scalar
        return vec

    def SetValue(self, value):
        if len(value) != self.valueType.dimension:
            raise ValueError("Input length %i does not match expected length %i", len(
                value), self.valueType.dimension)
        for index in xrange(self.valueType.dimension):
            if value[index] is None:
                raise ValueError("Value at %i is None", index)
            string = compatability.ResolveString(
                str(value[index]), self._stringType)
            if self.__validator.validate(string, 0)[0] != QtGui.QValidator.Acceptable:
                raise ValueError(
                    "%s (at index %i) not accepted by validator." % (string, index))
            self.__editors[index].setText(string)


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

    def __init__(self,  parent=None):
        super(_MatrixEdit, self).__init__(parent)
        self.__layout = QtWidgets.QGridLayout(self)
        self.__editors = []

        self.__validator = self.validatorType()

        for row in xrange(self.valueType.dimension[0]):
            for column in xrange(self.valueType.dimension[1]):
                self.__editors.append(QtWidgets.QLineEdit(self))
                self.__editors[-1].setValidator(self.__validator)
                self.__layout.addWidget(self.__editors[-1], row, column)
                self._SetupLineEdit(self.__editors[-1])
                if row != 0 and column != 0:
                    self.setTabOrder(self.__editors[-2], self.__editors[-1])
        self.setTabOrder(self.__editors[-1], self.__editors[0])

        self.setFocusProxy(self.__editors[0])
        # self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setLayout(self.__layout)
        self._SetupLayoutSpacing(self.__layout)
        # get the preferred string type of the current Qt context
        self._stringType = type(self.__editors[0].text())

    def __GetIndex(self, row, column):
        return row * self.valueType.dimension[1] + column

    def GetValue(self):
        matrix = self.valueType()
        numRows = self.valueType.dimension[0]
        numColumns = self.valueType.dimension[1]
        for row in xrange(numRows):
            for column in xrange(numColumns):
                scalar = self.scalarType(
                    self.__editors[self.__GetIndex(row, column)].text())
                matrix[row, column] = scalar
        return matrix

    def SetValue(self, value):
        numRows = self.valueType.dimension[0]
        numColumns = self.valueType.dimension[1]
        if len(value) != numRows:
            raise ValueError(
                "Input row size %i does not match expected length %i", len(value), numRows)
        for row in xrange(numRows):
            if type(value) is str:
                raise TypeError("Row cannot be string")
            if len(value[row]) != numColumns:
                raise ValueError("Input column size %i does not match expected length %i", len(
                    value[row]), numColumns)
            for column in xrange(numColumns):
                if value[row][column] is None:
                    raise ValueError("Value at (%i, %i) is None", row, column)
                string = compatability.ResolveString(
                    str(value[row][column]), self._stringType)
                if self.__validator.validate(string, 0)[0] != QtGui.QValidator.Acceptable:
                    raise ValueError(
                        "%s (at %i, %i) not accepted by validator." % (string, row, column))
                self.__editors[self.__GetIndex(row, column)].setText(string)


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
        super(StringEdit, self).__init__(parent)
        self.__lineEdit = QtWidgets.QLineEdit(self)
        self.__layout = QtWidgets.QHBoxLayout()
        self.__layout.addWidget(self.__lineEdit)
        self._SetupLayoutSpacing(self.__layout)
        self.setFocusProxy(self.__lineEdit)
        self.setLayout(self.__layout)
        self._SetupLineEdit(self.__lineEdit)

    def GetValue(self):
        return str(self.__lineEdit.text())

    def SetValue(self, value):
        value = value if value else ''
        self.__lineEdit.setText(value)


class AssetEdit(_LineEdit):
    valueType = Sdf.AssetPath

    def __init__(self, parent=None):
        super(AssetEdit, self).__init__(parent)
        self.__lineEdit = QtWidgets.QLineEdit(self)
        self.__layout = QtWidgets.QHBoxLayout()
        self.__layout.addWidget(self.__lineEdit)
        self._SetupLayoutSpacing(self.__layout)
        self.setFocusProxy(self.__lineEdit)
        self.setLayout(self.__layout)
        self._SetupLineEdit(self.__lineEdit)

    def GetValue(self):
        return Sdf.AssetPath(str(self.__lineEdit.text()))

    def SetValue(self, value):
        self.__lineEdit.setText(value.path)


class PathEdit(_LineEdit):
    valueType = Sdf.Path

    def __init__(self, parent=None):
        super(PathEdit, self).__init__(parent)
        self.__lineEdit = QtWidgets.QLineEdit(self)
        self.__layout = QtWidgets.QHBoxLayout()
        self.__layout.addWidget(self.__lineEdit)
        self._SetupLayoutSpacing(self.__layout)
        self.setFocusProxy(self.__lineEdit)
        self.setLayout(self.__layout)
        self._SetupLineEdit(self.__lineEdit)

    def GetValue(self):
        return Sdf.Path(str(self.__lineEdit.text()))

    def SetValue(self, value):
        value = str(value) if value else ''
        self.__lineEdit.setText(value)

valueTypeMap = {
    Tf.Type.FindByName('string'): StringEdit,
    Tf.Type.FindByName('TfToken'): StringEdit,
    Tf.Type.Find(Sdf.AssetPath): AssetEdit,
    Tf.Type.Find(Sdf.Path): PathEdit,
    Tf.Type.FindByName('unsigned char'):
        functools.partial(IntEdit, minValue=0, maxValue=(2 << (8-1))-1),
    Tf.Type.FindByName('unsigned int'):
        functools.partial(IntEdit, minValue=0, maxValue=(2 << (32-1))-1),
    Tf.Type.FindByName('unsigned long'):
        functools.partial(IntEdit, minValue=0, maxValue=(2 << (64-1))-1),
    Tf.Type.FindByName('int'): functools.partial(
        IntEdit, minValue=-(2 << (32-1-1)), maxValue=(2 << (32-1-1))-1),
    Tf.Type.FindByName('long'): functools.partial(
        IntEdit, minValue=-(2 << (64-1-1)), maxValue=(2 << (64-1-1))-1),
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

    widget = Vec3dEdit()
    widget.show()

    widget = StringEdit()
    widget.show()

    sys.exit(app.exec_())
