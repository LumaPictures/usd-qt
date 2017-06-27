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

import unittest
import os.path

from pxr import Tf, Sdf, Usd
from usdQt._bindings import _PrimIdTable


class TestSimplePrimIdTable(unittest.TestCase):

    def setUp(self):
        stagePath = 'testenv/testUsdQtPrimIdTable/simple.usda'
        stagePath = stagePath if os.path.isfile(stagePath) else stagePath.split('/')[-1]

        self.stage = Usd.Stage.Open(stagePath)

    def testBadRegistration(self):
        idTable = _PrimIdTable(self.stage, self.stage.GetPseudoRoot(), 
            Usd.PrimDefaultPredicate)
        with self.assertRaisesRegexp(Tf.ErrorException, 
            "Cannot find '\d+' in PrimIdTable"):
            idTable.RegisterChild(1234, 5678)


    def testSimple(self):
        idTable = _PrimIdTable(self.stage, self.stage.GetPseudoRoot(), 
            Usd.PrimDefaultPredicate)

        # Validate the root
        rootPath = self.stage.GetPseudoRoot().GetPath()
        self.assertEqual(idTable.GetRootPath(), rootPath)
        self.assertTrue(idTable.ContainsPath(rootPath))
        rootId = idTable.GetIdFromPath(rootPath)
        self.assertEqual(idTable.GetChildCount(rootId), 1)
        
        # Ensure that child paths are accessible before they are registered
        worldPath = idTable.GetChildPath(rootId, 0)
        self.assertEqual(worldPath, Sdf.Path('/World'))

        # Validate world and its initial children
        self.assertTrue(idTable.RegisterChild(rootId, 0))
        worldId = idTable.GetIdFromPath(worldPath)
        self.assertEqual(idTable.GetChildCount(worldId), 3)
        for i in xrange(3):
            self.assertTrue(idTable.RegisterChild(worldId, i))
            
        with self.assertRaisesRegexp(Tf.ErrorException,
            "Index '\d+' exceeds number of children of '[a-zA-Z0-9_/]+' in PrimIdTable"):
            self.assertFalse(idTable.RegisterChild(rootId, 1234))

        child1Path = idTable.GetChildPath(worldId, 0)
        child2Path = idTable.GetChildPath(worldId, 1)
        child3Path = idTable.GetChildPath(worldId, 2)
        
        child1Id = idTable.GetIdFromPath(child1Path)
        child2Id = idTable.GetIdFromPath(child2Path)
        child3Id = idTable.GetIdFromPath(child3Path)
        
        self.assertEqual(idTable.GetChildCount(child1Id), 2)
        self.assertEqual(idTable.GetChildCount(child2Id), 1)
        self.assertEqual(idTable.GetChildCount(child3Id), 0)
        
        grandchild1Path = idTable.GetChildPath(child1Id, 0)
        grandchild2Path = idTable.GetChildPath(child1Id, 1)

        self.assertEqual(idTable.GetChildCount(child1Id), 2)
        self.assertEqual(idTable.GetChildCount(child2Id), 1)

        for i in xrange(2):
            self.assertTrue(idTable.RegisterChild(child1Id, i))
        
        # Test resyncing
        # We should still have access to Grandchild1_{1,2} but not Grandchild2_1
        # without reregistering
        idTable.ResyncSubtrees([Sdf.Path('/World/Child2'), Sdf.Path('/World/Child1'), Sdf.Path('/World/Child1/Grandchild1_1')])
        
        idTable.GetIdFromPath(grandchild1Path)
        idTable.GetIdFromPath(grandchild2Path)
        
        otherGrandchild1Path = idTable.GetChildPath(child2Id, 0)
        self.assertEqual(otherGrandchild1Path, Sdf.Path('/World/Child2/GrandChild2_1'))
        
        with self.assertRaisesRegexp(Tf.ErrorException,
            "Cannot find '[a-zA-Z0-9_/]+' in PrimIdTable"):
            idTable.GetIdFromPath(otherGrandchild1Path)

if __name__ == '__main__':
    unittest.main(verbosity=2)
