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

from pxr import Sdf, Usd
from pxr.UsdQt._bindings import PrimFilterCache

from collections import OrderedDict


class TestSimplePrimFilterCache(unittest.TestCase):

    def setUp(self):
        stagePath = 'simpleFilter.usda'
        stagePath = stagePath if os.path.isfile(stagePath) else \
            os.path.join(os.path.splitext(__file__)[0], stagePath)

        self.stage = Usd.Stage.Open(stagePath)
        self.cache = PrimFilterCache()

    def testSimple(self):
        self.cache.ApplyPathContainsFilter(self.stage.GetPrimAtPath("/World"),
                                           "Accept", Usd.PrimDefaultPredicate)

        pathToState = OrderedDict([
            ("/World", PrimFilterCache.Accept),
            ("/World/Reject", PrimFilterCache.Reject),
            ("/World/Accept", PrimFilterCache.Accept),
            ("/World/AcceptParent", PrimFilterCache.Accept),
            ("/World/AcceptParent/RejectChild", PrimFilterCache.Reject),
            ("/World/AcceptParent/AcceptChild", PrimFilterCache.Accept),
            ("/World/IntermediateParent/RejectChild", PrimFilterCache.Reject),
            ("/World/IntermediateParent/AcceptChild", PrimFilterCache.Accept),
            ("/World/IntermediateParent/IntermediateChild",
             PrimFilterCache.Accept),
            ("/World/IntermediateParent/IntermediateChild/AcceptGrandchild",
             PrimFilterCache.Accept),
            ("/World/IntermediateParent/IntermediateChild/RejectGrandchild",
             PrimFilterCache.Reject)
        ]
        )

        for path in pathToState:
            self.assertEqual(self.cache.GetState(
                Sdf.Path(path)), pathToState[path])


if __name__ == '__main__':
    unittest.main(verbosity=2)
