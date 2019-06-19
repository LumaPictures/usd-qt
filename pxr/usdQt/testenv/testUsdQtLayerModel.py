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

import unittest2 as unittest
import os.path

import pxr.UsdQt.layerModel as layerModel
from pxr import Sdf, Usd
from pxr.UsdQt._Qt import QtCore

stageFilePath = "simpleLayerStack.usda"
stageFilePath = stageFilePath if os.path.isfile(stageFilePath) else \
    os.path.join(os.path.splitext(__file__)[0], stageFilePath)


class TestSimpleLayerModelBase(unittest.TestCase):

    def setUp(self):

        self.stage = Usd.Stage.Open(stageFilePath)
        assert(self.stage)

        self.model = layerModel.LayerBaseModel(self.stage)

    def test_basicUsage(self):
        layerStack = self.stage.GetLayerStack(includeSessionLayers=True)
        self.assertEqual(self.model.rowCount(), len(layerStack))

        self.assertEqual(self.model.data(self.model.createIndex(0, 0)),
                         'session')
        for i, layer in enumerate(layerStack[1:]):
            self.assertEqual(
                os.path.splitext(os.path.split(layer.identifier)[1])[0],
                self.model.data(self.model.createIndex(i + 1, 0)))

    def test_invalidModel(self):
        invalidModel = layerModel.LayerBaseModel()
        self.assertEqual(invalidModel.rowCount(), 0)
        with self.assertRaises(Exception):
            invalidModel.data(invalidModel.createIndex(0, 0))

        with self.assertRaises(Exception):
            invalidModel.GetLayerFromIndex(self.createIndex(0, 0))


class TestSimpleLayerStandardModel(unittest.TestCase):
    """
    TODO: Also test uneditable and unsaveable flag masks as well.
    """

    def setUp(self):

        self.stage = Usd.Stage.Open(stageFilePath)
        assert(self.stage)

        self.model = layerModel.LayerStandardModel(self.stage)

    def test_fileFormatFlagMask(self):
        layerStack = self.stage.GetLayerStack(includeSessionLayers=True)
        self.assertEqual(self.model.rowCount(), len(layerStack))

        self.model.SetFileFormatFlagMask(Sdf.FileFormat.FindById('usdc'),
                                         ~QtCore.Qt.ItemIsEnabled)

        for i, layer in enumerate(layerStack):
            flags = self.model.flags(self.model.createIndex(i, 0))
            if layer.GetFileFormat() == Sdf.FileFormat.FindById('usdc'):
                assert(flags & ~QtCore.Qt.ItemIsEnabled)
            else:
                assert(flags & QtCore.Qt.ItemIsEnabled)


if __name__ == '__main__':
    unittest.main(verbosity=2)
