#
# Copyright 2017 Luma Pictures
#
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification you may not use this file except in
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
#     http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License with the above modification is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the Apache License for the specific
# language governing permissions and limitations under the Apache License.
#

from pxr import Usd

import pytest
import usdlib.variants
from usdlib.variants import PrimVariant

BASIC_PRIM_WITH_VARIANTS = {
    '/path/to/test/prim': {
        'elem=anim(default)': {
            'color=blue': {
                'version=A01': {},
                'version=A02(default)': {},
                'version=A03': {}
            }
        },
        'elem=rigg': {
            'size=big(default)': {
                'animal=dinosaur': {}
            },
            'size=small': {
                'animal=dinosaur': {}
            }
        }
    }
}


def createVariants(prim, variants):
    '''Create a variant set and add any variants. Can be used recursively.

    Keys take the form of:
        'variantSetName=variantValue' or
        'variantSetName=variantValue(default)' if they are the default
    '''
    for variantKey, rest in variants.iteritems():
        setName, variantName = variantKey.split('=')

        default = variantName.endswith('(default)')
        if default:
            variantName = variantName[:-len('(default)')]

        variantSet = prim.GetVariantSets().AddVariantSet(setName)

        old = variantSet.GetVariantSelection()
        variantSet.AddVariant(variantName)
        variantSet.SetVariantSelection(variantName)
        with variantSet.GetVariantEditContext():
            createVariants(prim, rest)

        if old and not default:
            variantSet.SetVariantSelection(old)


def createPrims(stage, variants):
    '''Create a testing asset prim and populate its variants.'''
    for path, pathVariants in variants.iteritems():
        prim = stage.DefinePrim(path)
        model = Usd.ModelAPI(prim)
        model.SetAssetName('test_asset')  # needs a name or it will be skipped
        createVariants(prim, pathVariants)
    stage.GetRootLayer().Save()


@pytest.fixture(scope='function')
def usdstage(tmpdir):
    tempfile = str(tmpdir.join('tmpstage.usd'))
    stage = Usd.Stage.CreateNew(tempfile)
    yield stage


def test_primVariants(usdstage):
    createPrims(usdstage, BASIC_PRIM_WITH_VARIANTS)
    prim = usdstage.GetPrimAtPath(BASIC_PRIM_WITH_VARIANTS.keys()[0])
    primVariants = usdlib.variants.getPrimVariants(prim)
    assert primVariants == [
        PrimVariant(setName='elem', variantName='anim'),
        PrimVariant(setName='color', variantName='blue'),
        PrimVariant(setName='version', variantName='A02')
    ]
    assert usdlib.variants.getPrimVariantsWithKey(prim) == [
        ('elem', PrimVariant(setName='elem', variantName='anim')),
        ('{elem=anim}color', PrimVariant(setName='color', variantName='blue')),
        ('{elem=anim}{color=blue}version', PrimVariant(setName='version', variantName='A02'))
    ]
    assert usdlib.variants.applySelection(primVariants, {'color': 'red'}) == [
        PrimVariant(setName='elem', variantName='anim'),
        PrimVariant(setName='color', variantName='red'),
        PrimVariant(setName='version', variantName='A02')
    ]


BASIC_PRIM_WITH_PARALLEL_VARIANTS = {
    '/path/to/test/prim': {
        'elem=anim(default)': {
            'color=blue(default)': {
                'version=A01': {},
                'version=A02(default)': {},
                'version=A03': {}
            },
            'color=red': {
                'version=A01': {},
                'version=A02(default)': {},
                'version=A03': {}
            }
        },
        'elem=rigg': {
            'size=big(default)': {
                'animal=dinosaur': {}
            },
            'size=small': {
                'animal=dinosaur': {}
            }
        },
        'shaderVariant=battleReady': {
            'shader_version=A01': {},
            'shader_version=A02(default)': {},
            'shader_version=A03': {}
        },
        'shaderVariant=battleTested(default)': {
            'shader_version=A01': {},
            'shader_version=A02(default)': {},
            'shader_version=A03': {}
        }
    }
}


def test_primVariants2(usdstage):
    createPrims(usdstage, BASIC_PRIM_WITH_PARALLEL_VARIANTS)
    prim = usdstage.GetPrimAtPath(BASIC_PRIM_WITH_PARALLEL_VARIANTS.keys()[0])
    primVariants = usdlib.variants.getPrimVariants(prim)
    assert primVariants == [
        PrimVariant(setName='elem', variantName='anim'),
        PrimVariant(setName='color', variantName='blue'),
        PrimVariant(setName='version', variantName='A02'),
        PrimVariant(setName='shaderVariant', variantName='battleTested'),
        PrimVariant(setName='shader_version', variantName='A02'),
    ]
    assert usdlib.variants.getPrimVariantsWithKey(prim) == [
        ('elem', PrimVariant(setName='elem', variantName='anim')),
        ('{elem=anim}color', PrimVariant(setName='color', variantName='blue')),
        ('{elem=anim}{color=blue}version', PrimVariant(setName='version', variantName='A02')),
        ('shaderVariant', PrimVariant(setName='shaderVariant', variantName='battleTested')),
        ('{shaderVariant=battleTested}shader_version', PrimVariant(setName='shader_version', variantName='A02')),
    ]
    assert usdlib.variants.applySelection(primVariants, {'color': 'red'}) == [
        PrimVariant(setName='elem', variantName='anim'),
        PrimVariant(setName='color', variantName='red'),
        PrimVariant(setName='version', variantName='A02'),
        PrimVariant(setName='shaderVariant', variantName='battleTested'),
        PrimVariant(setName='shader_version', variantName='A02')
    ]
    # ensure cleared selection will still get picked up
    prim.GetVariantSets().GetVariantSet('shaderVariant').ClearVariantSelection()
    prim.GetVariantSets().GetVariantSet('elem').ClearVariantSelection()
    # prim.GetVariantSets().GetVariantSet('color').SetVariantSelection()
    assert prim.GetVariantSets().GetVariantSelection('elem') == ''
    assert prim.GetVariantSets().GetVariantSelection('shaderVariant') == ''
    primVariants = usdlib.variants.getPrimVariants(prim)
    assert primVariants == [
        PrimVariant(setName='elem', variantName=''),
        # wont get this one as its nested under
        # PrimVariant(setName='color', variantName=''),
        # PrimVariant(setName='version', variantName='A02'),
        PrimVariant(setName='shaderVariant', variantName=''),
        # PrimVariant(setName='shader_version', variantName='A02')
    ]