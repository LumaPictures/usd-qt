from pxr import Usd

import pytest
import usdlib.variants

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

        variantSet = prim.GetVariantSets().AppendVariantSet(setName)

        old = variantSet.GetVariantSelection()
        variantSet.AppendVariant(variantName)
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


@pytest.fixture
def usdstage(tmpdir):
    tempfile = str(tmpdir.join('tmpstage.usd'))
    stage = Usd.Stage.CreateNew(tempfile)
    return stage


def test_primVariants(usdstage):
    createPrims(usdstage, BASIC_PRIM_WITH_VARIANTS)
    prim = usdstage.GetPrimAtPath(BASIC_PRIM_WITH_VARIANTS.keys()[0])
    primVariants = usdlib.variants.getPrimVariants(prim)
    assert primVariants == [
        usdlib.variants.PrimVariant(setName='elem', variantName='anim'),
        usdlib.variants.PrimVariant(setName='color', variantName='blue'),
        usdlib.variants.PrimVariant(setName='version', variantName='A02')
    ]
    assert list(usdlib.variants.iterVariantSetKeys(primVariants)) == [
        'elem', '{elem=anim}color', '{elem=anim}{color=blue}version']
    assert usdlib.variants.variantsByKey(primVariants) == [
        ('elem', 'anim'),
        ('{elem=anim}color', 'blue'),
        ('{elem=anim}{color=blue}version', 'A02')
    ]
    assert usdlib.variants.applySelection(primVariants, {'color': 'red'}) == [
        usdlib.variants.PrimVariant(setName='elem', variantName='anim'),
        usdlib.variants.PrimVariant(setName='color', variantName='red'),
        usdlib.variants.PrimVariant(setName='version', variantName='A02')
    ]
