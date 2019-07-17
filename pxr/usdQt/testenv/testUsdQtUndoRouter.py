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

import unittest2 as unittest

from pxr import Tf, Usd
from pxr.UsdQt._bindings import (UndoBlock, UndoInverse, UndoRouter,
                                 UndoStackNotice)


class TestUndoRouter(unittest.TestCase):

    def setUp(self):
        self.stage = Usd.Stage.CreateInMemory()
        UndoRouter.TrackLayer(self.stage.GetRootLayer())
        self.localUndoStack = []
        self.listener = Tf.Notice.RegisterGlobally(UndoStackNotice, self.Notice)

    def Notice(self, notice, sender):
        inverse = UndoInverse()
        UndoRouter.TransferEdits(inverse)
        self.localUndoStack.append(inverse)

    def testExpiredStage(self):
        with UndoBlock():
            self.stage.DefinePrim('/World')

        self.stage = None
        with self.assertRaises(Tf.ErrorException):
            self.localUndoStack[-1].Invert()

    def testMidEditBlockInversion(self):
        self.stage.DefinePrim('/World')
        with UndoBlock():
            with self.assertRaisesRegexp(Tf.ErrorException, 'Inversion during \
open edit block may result in corrupted undo stack.'):
                self.localUndoStack[-1].Invert()

    def testNoEditBlock(self):
        prim = self.stage.DefinePrim('/World')
        self.assertTrue(bool(prim))
        self.assertEqual(len(self.localUndoStack), 3)
        # undo
        self.localUndoStack[-1].Invert()
        self.localUndoStack[-2].Invert()
        self.localUndoStack[-3].Invert()
        self.assertFalse(bool(prim))
        # redo
        self.localUndoStack[-3].Invert()
        self.localUndoStack[-2].Invert()
        self.localUndoStack[-1].Invert()
        prim = self.stage.GetPrimAtPath('/World')
        self.assertTrue(bool(prim))

    def testRevokedListener(self):
        self.listener.Revoke()
        with UndoBlock():
            self.stage.DefinePrim('/World')
        with UndoBlock():
            self.stage.DefinePrim('/World/Child')
        self.assertEqual(self.localUndoStack, [])

    def testNestedUndoBlock(self):
        with UndoBlock():
            prim = self.stage.DefinePrim('/World')

        self.assertTrue(bool(prim))
        with UndoBlock():
            prim.SetActive(False)
            with UndoBlock():
                prim.SetActive(True)
                with UndoBlock():
                    prim.SetActive(False)

        self.assertFalse(prim.IsActive())
        self.assertEqual(len(self.localUndoStack), 2)

        with UndoBlock():
            prim.SetActive(False)
            with UndoBlock():
                prim.SetActive(True)

        self.assertTrue(prim.IsActive())
        self.assertEqual(len(self.localUndoStack), 3)

        self.localUndoStack[-1].Invert()  # undo
        self.assertFalse(prim.IsActive())
        self.localUndoStack[-1].Invert()  # redo
        self.assertTrue(prim.IsActive())
        self.localUndoStack[-1].Invert()  # undo
        self.assertFalse(prim.IsActive())
        self.localUndoStack[-2].Invert()  # undo
        self.assertTrue(prim.IsActive())
        self.localUndoStack[-3].Invert()  # undo
        self.assertFalse(bool(prim))
        self.localUndoStack[-3].Invert()  # redo
        prim = self.stage.GetPrimAtPath('/World')
        self.assertTrue(bool(prim))
        self.assertTrue(prim.IsActive())

        self.assertEqual(len(self.localUndoStack), 3)

    def testEmptyUndoBlock(self):
        with UndoBlock():
            pass
        self.assertEqual(self.localUndoStack, [])

        with UndoBlock():
            with UndoBlock():
                with UndoBlock():
                    pass
        self.assertEqual(self.localUndoStack, [])


if __name__ == '__main__':
    unittest.main()
