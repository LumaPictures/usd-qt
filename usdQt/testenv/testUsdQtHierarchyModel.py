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
import os, os.path

from pxr import Usd, UsdQt
from pxr.UsdQt._Qt import QtCore

class TestSimpleHierarchyDefault(unittest.TestCase):
    predicate = Usd.PrimDefaultPredicate

    def setUp(self):
        stageFilePath = "testenv/testUsdQtHierarchyModel/simpleHierarchy.usda"
        stageFilePath = stageFilePath if os.path.isfile(stageFilePath) else stageFilePath.split('/')[-1]
        self.stage = Usd.Stage.Open(stageFilePath)
        self.model = UsdQt.HierarchyStandardModel(
            self.stage)

        self.world = self.stage.GetPrimAtPath('/World')

        self.pseudoRootIndex = self.model.index(0, 0, QtCore.QModelIndex())
        self.worldIndex = self.model.index(0, 0, self.pseudoRootIndex)

        self.primToDeactivate = self.stage.GetPrimAtPath(
            '/World/PrimToDeactivate')
        self.primToActivate = self.stage.GetPrimAtPath('/World/PrimToActivate')
        self.primWithVariants = self.stage.GetPrimAtPath(
            '/World/PrimWithVariants')

    def test_RootStructure(self):

        self.assertEqual(self.model.rowCount(QtCore.QModelIndex()), 1)
        self.assertEqual(self.model._GetPrimForIndex(
            self.pseudoRootIndex), self.stage.GetPseudoRoot())

        self.assertEqual(self.model.rowCount(self.pseudoRootIndex), 1)
        self.assertEqual(self.model._GetPrimForIndex(
            self.worldIndex), self.world)

    def test_UnmodifiedStage(self):
        #self.model.Debug()
        self.VerifyHierarchyMatchesStage(self.world, self.worldIndex)
    
    def test_UnmodifiedFilterModel(self):
        filterModel = UsdQt.HierarchyStandardFilterModel()
        filterModel.setSourceModel(self.model)
        pseudoRootIndex = filterModel.index(0, 0, QtCore.QModelIndex())
        filterIndex = filterModel.index(0, 0, pseudoRootIndex)
        sourceIndex = filterModel.mapToSource(filterIndex)
      
        self.assertEqual(self.world, self.model._GetPrimForIndex(sourceIndex))

    def test_DeactivateOnly(self):
        self.primToDeactivate.SetActive(False)
        self.VerifyHierarchyMatchesStage(self.world, self.worldIndex)

    def test_DeactivateAndReactivate(self):
        self.primToDeactivate.SetActive(False)
        self.VerifyHierarchyMatchesStage(self.world, self.worldIndex)
        self.primToDeactivate.SetActive(True)
        self.VerifyHierarchyMatchesStage(self.world, self.worldIndex)

    def test_ActivateOnly(self):
        self.primToActivate.SetActive(True)
        self.VerifyHierarchyMatchesStage(self.world, self.worldIndex)

    def test_ActivateAndDeactivate(self):
        self.primToActivate.SetActive(True)
        self.VerifyHierarchyMatchesStage(self.world, self.worldIndex)
        self.primToActivate.SetActive(False)
        self.VerifyHierarchyMatchesStage(self.world, self.worldIndex)

    def test_VariantSwitch(self):
        variantSet = self.primWithVariants.GetVariantSet('testVariant')
        variantSet.SetVariantSelection("Variant1")
        self.VerifyHierarchyMatchesStage(self.world, self.worldIndex)
        variantSet.SetVariantSelection("Variant2")
        self.VerifyHierarchyMatchesStage(self.world, self.worldIndex)
        variantSet.ClearVariantSelection()
        self.VerifyHierarchyMatchesStage(self.world, self.worldIndex)

    def test_BadVariantSwitch(self):
        variantSet = self.primWithVariants.GetVariantSet('testVariant')
        variantSet.SetVariantSelection("NonExistantVariant")
        self.VerifyHierarchyMatchesStage(self.world, self.worldIndex)

    def VerifyHierarchyMatchesStage(self, prim, index, verbose=False):
        if verbose:
            print("Verifying %s" % str(prim), index.internalId())
        self.assertEqual(prim, self.model._GetPrimForIndex(index))

        children = prim.GetFilteredChildren(self.model.GetPredicate())
        numRows = self.model.rowCount(index)

        if verbose:
            print("Num Rows: ", numRows)
            print("Children: ", children)
        self.assertEqual(numRows, len(children))

        for row, child in enumerate(children):
            self.VerifyHierarchyMatchesStage(
                child, self.model.index(row, 0, index), verbose=verbose)


class TestSimpleHierarchyAllLoaded(TestSimpleHierarchyDefault):
    predicate = Usd.PrimIsLoaded

if __name__ == '__main__':
    unittest.main(verbosity=2)
