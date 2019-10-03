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
import os
import os.path

import pxr.UsdQt.opinionModel as opinionModel
from pxr import Usd
from pxr.UsdQt._Qt import QtCore


class TestOpinionModel(unittest.TestCase):

    def setUp(self):
        stageFilePath = "simple.usda"
        stageFilePath = stageFilePath if os.path.isfile(stageFilePath) else \
            os.path.join(os.path.splitext(__file__)[0], stageFilePath)
        self.stage = Usd.Stage.Open(stageFilePath)

    def testProperties(self):
        prims = [self.stage.GetPrimAtPath(path) for path in
                 ['/MyPrim1/Child1', '/MyPrim1/Child2', '/MyPrim1/Child3', '/MyPrim1/Child4']]

        model = opinionModel.OpinionStandardModel(prims)
        primIndex = model.index(0, 0, QtCore.QModelIndex())
        proxy = model.GetProxyForIndex(primIndex)
        self.assertEqual(proxy.GetNames(),
                         ['Child1', 'Child2', 'Child3', 'Child4'])
        self.assertEqual(model.data(primIndex),
                         'Child1, Child2, Child3, Child4')

        metadataGroupIndex = model.index(0, 0, primIndex)
        attributeGroupIndex = model.index(1, 0, primIndex)
        relationshipGroupIndex = model.index(2, 0, primIndex)

        self.assertGreater(model.rowCount(metadataGroupIndex), 0)
        self.assertEqual(model.rowCount(attributeGroupIndex), 2)
        self.assertEqual(model.rowCount(relationshipGroupIndex), 1)

        self.assertEqual(model.index(0, 0, attributeGroupIndex).data(), "x")
        self.assertEqual(model.index(0, 1, attributeGroupIndex).data(), "")
        self.assertEqual(model.index(0, 2, attributeGroupIndex).data(
            QtCore.Qt.DisplayRole), "")
        self.assertEqual(model.index(0, 2, attributeGroupIndex).data(
            QtCore.Qt.EditRole), None)

        self.assertEqual(model.index(1, 0, attributeGroupIndex).data(), "y")
        self.assertEqual(model.index(1, 1, attributeGroupIndex).data(), "int")
        self.assertEqual(model.index(1, 2, attributeGroupIndex).data(
            QtCore.Qt.DisplayRole), "2")
        self.assertEqual(model.index(
            1, 2, attributeGroupIndex).data(QtCore.Qt.EditRole), 2)

        self.assertEqual(model.index(
            0, 0, relationshipGroupIndex).data(), "rel1")

    def testMetadata(self):
        prims = [self.stage.GetPrimAtPath(path) for path in
                 ['/MyPrim1', '/MyPrim2']]

    def testInvalidSetData(self):
        """Ensure that indices are property cleaned when a bad setData occurs.
        This can end up triggering a very hard to track down deferred crash
        where persistent indices are created and not cleaned up."""
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
