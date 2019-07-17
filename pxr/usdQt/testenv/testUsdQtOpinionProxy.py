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

from pxr import Tf, Sdf, Usd, Vt
from pxr.UsdQt._bindings import (_AttributeProxy, _MetadataProxy, _PrimProxy,
                                 _VariantSetsProxy, _VariantSetProxy)


class BaseClasses:

    class ProxyTest(unittest.TestCase):

        def setUp(self):
            stagePath = 'simple.usda'
            stagePath = stagePath if os.path.isfile(stagePath) else \
                os.path.join(os.path.splitext(__file__)[0], stagePath)
            self.stage = Usd.Stage.Open(stagePath)


class TestVariantSetAndSetsProxy(BaseClasses.ProxyTest):

    def testSimple(self):
        prim1 = self.stage.GetPrimAtPath('/World/VariantPrim1')
        prim2 = self.stage.GetPrimAtPath('/World/VariantPrim2')

        variantSetsProxy = _VariantSetsProxy([prim1, prim2])
        self.assertEqual(variantSetsProxy.GetNames(), ['variant2', 'variant3'])

        variantSetProxy1 = _VariantSetProxy([
            prim1.GetVariantSets().GetVariantSet('variant2'),
            prim2.GetVariantSets().GetVariantSet('variant2')
        ]
        )

        variantSetProxy2 = _VariantSetProxy([
            prim1.GetVariantSets().GetVariantSet('variant3'),
            prim2.GetVariantSets().GetVariantSet('variant3')
        ]
        )

        self.assertEqual(variantSetProxy1.GetVariantSelection(), "")
        self.assertEqual(variantSetProxy2.GetVariantSelection(), "five")

        self.assertTrue(variantSetProxy1.SetVariantSelection("three"))
        self.assertEqual(variantSetProxy1.GetVariantSelection(), "three")
        self.assertTrue(variantSetProxy1.ClearVariantSelection())
        self.assertEqual(variantSetProxy1.GetVariantSelection(), "")


class TestMetadataProxy(BaseClasses.ProxyTest):

    def testSimple(self):
        prim1 = self.stage.GetPrimAtPath('/World/MetadataPrim1')
        prim2 = self.stage.GetPrimAtPath('/World/MetadataPrim2')
        prim3 = self.stage.GetPrimAtPath('/World/MetadataPrim3')

        metadataProxy = _MetadataProxy(
            [prim1, prim2], 'documentation')

        self.assertEqual(metadataProxy.GetType(), Tf.Type.FindByName('string'))
        self.assertEqual(metadataProxy.GetValue(), 'sharedDoc')

        metadataProxy2 = _MetadataProxy(
            [prim1, prim2, prim3], 'documentation')

        self.assertEqual(metadataProxy2.GetType(), Tf.Type.FindByName('string'))
        self.assertEqual(metadataProxy2.GetValue(), None)

        self.assertTrue(metadataProxy2.SetValue('new documentation'))
        self.assertEqual(metadataProxy2.GetValue(), "new documentation")
        self.assertTrue(metadataProxy2.ClearValue())
        self.assertEqual(metadataProxy2.GetValue(), None)


class TestAttributeProxy(BaseClasses.ProxyTest):

    def testSimple(self):
        prim1 = self.stage.GetPrimAtPath('/World/AttrPrim1')
        prim2 = self.stage.GetPrimAtPath('/World/AttrPrim2')
        prim3 = self.stage.GetPrimAtPath('/World/AttrPrim3')
        prim4 = self.stage.GetPrimAtPath('/World/AttrPrim4')

        attrProxy1 = _AttributeProxy(
            [prim1.GetAttribute('x'), prim2.GetAttribute('x')])

        self.assertEqual(attrProxy1.GetName(), 'x')
        self.assertEqual(attrProxy1.GetTypeName(), Sdf.ValueTypeNames.Int)
        self.assertEqual(attrProxy1.GetVariability(), Sdf.VariabilityVarying)
        self.assertEqual(attrProxy1.Get(Usd.TimeCode.Default()), 5)

        attrProxy2 = _AttributeProxy(
            [prim1.GetAttribute('x'), prim2.GetAttribute('x'),
             prim3.GetAttribute('x')])

        # test a combination of common series of operations like
        # Get, Set, Clear, and Block
        self.assertEqual(attrProxy2.GetTypeName(), Sdf.ValueTypeNames.Int)
        self.assertEqual(attrProxy2.GetVariability(), Sdf.VariabilityVarying)
        self.assertEqual(attrProxy2.Get(Usd.TimeCode.Default()), None)
        self.assertTrue(attrProxy2.Set(22, Usd.TimeCode.Default()))
        self.assertEqual(attrProxy2.Get(Usd.TimeCode.Default()), 22)
        attrProxy2.Block()
        self.assertEqual(attrProxy2.Get(Usd.TimeCode.Default()), None)
        self.assertTrue(attrProxy2.Clear())
        self.assertEqual(attrProxy2.Get(Usd.TimeCode.Default()), None)

        attrProxy3 = _AttributeProxy(
            [prim1.GetAttribute('x'), prim2.GetAttribute('x'),
             prim3.GetAttribute('x'), prim4.GetAttribute('x')])

        self.assertEqual(attrProxy3.GetTypeName(), Sdf.ValueTypeName())
        self.assertEqual(attrProxy3.GetVariability(), Sdf.VariabilityVarying)
        self.assertEqual(attrProxy3.Get(Usd.TimeCode.Default()), None)
        with self.assertRaises(Tf.ErrorException):
            self.assertTrue(attrProxy3.Set(22, Usd.TimeCode.Default()))
        self.assertTrue(attrProxy3.Clear())
        self.assertEqual(attrProxy3.Get(Usd.TimeCode.Default()), None)

    def testAuthoredAndDefined(self):
        """Validates IsDefined() and IsAuthored() methods"""
        prim1 = self.stage.GetPrimAtPath('/World/Prim1')
        prim2 = self.stage.GetPrimAtPath('/World/AttrPrim1')

        attrProxyX = _AttributeProxy(
            [prim1.GetAttribute('x'), prim2.GetAttribute('x')])

        self.assertTrue(attrProxyX.IsDefined())
        self.assertTrue(attrProxyX.IsAuthored())


    def testToken(self):
        """Validates GetAllowedTokens() for token attributes"""
        prim = self.stage.GetPrimAtPath('/World/TokenPrim')

        attrProxy = _AttributeProxy(
            [prim.GetAttribute('a'), prim.GetAttribute('b'),
             prim.GetAttribute('c')])
        self.assertEqual(attrProxy.GetAllowedTokens(),
                         Vt.TokenArray(['one', 'two']))

    def testContains(self):
        prim1 = self.stage.GetPrimAtPath('/World/AttrPrim1')
        prim2 = self.stage.GetPrimAtPath('/World/AttrPrim2')

        attrProxy = _AttributeProxy(
            [prim1.GetAttribute('x'), prim2.GetAttribute('x')])

        self.assertTrue(attrProxy.ContainsPath(['/World/AttrPrim1.x']))
        self.assertTrue(attrProxy.ContainsPath(['/World/AttrPrim2.x']))
        self.assertTrue(attrProxy.ContainsPath(
            ['/World/AttrPrim2.x', '/World/blah']))
        self.assertFalse(attrProxy.ContainsPath(['/World']))
        self.assertFalse(attrProxy.ContainsPath(['/World/AttrPrim1']))
        self.assertFalse(attrProxy.ContainsPath(['/World/AttrPrim']))
        self.assertFalse(attrProxy.ContainsPath([Sdf.Path()]))

        self.assertTrue(attrProxy.ContainsPathOrDescendent(
            ['/World/AttrPrim1.x']))
        self.assertTrue(
            attrProxy.ContainsPathOrDescendent(['/World/AttrPrim2']))
        self.assertTrue(attrProxy.ContainsPathOrDescendent(
            ['/World/AttrPrim2', '/World/blah']))
        self.assertTrue(attrProxy.ContainsPathOrDescendent(['/World']))
        self.assertFalse(
            attrProxy.ContainsPathOrDescendent(['/World/AttrPrim']))
        self.assertFalse(attrProxy.ContainsPathOrDescendent(['/AnotherWorld']))
        self.assertFalse(attrProxy.ContainsPathOrDescendent([Sdf.Path()]))
        self.assertFalse(attrProxy.ContainsPathOrDescendent(
            ['/World/AttrPrim1.y']))


class TestPrimProxy(BaseClasses.ProxyTest):

    def testSimple(self):
        prim1 = self.stage.GetPrimAtPath('/World/Prim1')
        prim2 = self.stage.GetPrimAtPath('/World/Prim2')
        prim3 = self.stage.GetPrimAtPath('/World/Prim3')

        primProxy = _PrimProxy([prim1, prim2, prim3])
        self.assertEqual(primProxy.GetNames(), [
                         'Prim1', 'Prim2', 'Prim3'])

        self.assertEqual(primProxy.GetAttributeNames(), ['x', 'y'])
        self.assertEqual(primProxy.GetRelationshipNames(), ['rel1', 'rel2'])

    def testContains(self):
        prim1 = self.stage.GetPrimAtPath('/World/Prim1')
        prim2 = self.stage.GetPrimAtPath('/World/Prim2')

        primProxy = _PrimProxy([prim1, prim2])

        self.assertTrue(primProxy.ContainsPath(['/World/Prim1']))
        self.assertTrue(primProxy.ContainsPath(['/World/Prim2']))
        self.assertTrue(primProxy.ContainsPath(['/World/Prim2', '/World/blah']))
        self.assertFalse(primProxy.ContainsPath(['/World']))
        self.assertFalse(primProxy.ContainsPath(['/World/Prim']))
        self.assertFalse(primProxy.ContainsPath([Sdf.Path()]))

        self.assertTrue(primProxy.ContainsPathOrDescendent(['/World/Prim1']))
        self.assertTrue(primProxy.ContainsPathOrDescendent(['/World/Prim2']))
        self.assertTrue(primProxy.ContainsPathOrDescendent(
            ['/World/Prim2', '/World/blah']))
        self.assertTrue(primProxy.ContainsPathOrDescendent(['/World']))
        self.assertFalse(primProxy.ContainsPathOrDescendent(['/World/Prim']))
        self.assertFalse(primProxy.ContainsPathOrDescendent(['/AnotherWorld']))
        self.assertFalse(primProxy.ContainsPathOrDescendent([Sdf.Path()]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
