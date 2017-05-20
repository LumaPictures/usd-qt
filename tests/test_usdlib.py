
# usd, and potentially mess up other tests




from pxr import Usd

import pytest
import usdlib.stage
import usdlib.variants as variants

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
    primVariants = variants.getPrimVariants(prim)
    assert primVariants == [
        variants.PrimVariant(setName='elem', variantName='anim'),
        variants.PrimVariant(setName='color', variantName='blue'),
        variants.PrimVariant(setName='version', variantName='A02')
    ]
    assert list(variants.iterVariantSetKeys(primVariants)) == [
        'elem', '{elem=anim}color', '{elem=anim}{color=blue}version']
    assert variants.variantsByKey(primVariants) == [
        ('elem', 'anim'),
        ('{elem=anim}color', 'blue'),
        ('{elem=anim}{color=blue}version', 'A02')
    ]
    assert variants.applySelection(primVariants, {'color': 'red'}) == [
        variants.PrimVariant(setName='elem', variantName='anim'),
        variants.PrimVariant(setName='color', variantName='red'),
        variants.PrimVariant(setName='version', variantName='A02')
    ]


def test_variablePrimItem(usdstage):
    '''Test the parsing of a stage into prim items, and the gathering of
    variant set info that is used to populate variant widgets.'''
    # dict describing the usd stage that will be built for this test

    createPrims(usdstage, BASIC_PRIM_WITH_VARIANTS)

    # mock user overrides saved in the scene
    _overrides = {
        '/path/to/test/prim': {
            'elem': 'rigg',
            'size': 'small',
            'animal': 'dinosaur'
        }
    }
    # mock state of the stage last time asset manager was used
    _lastDefaults = {
        '/path/to/test/prim': {
            'elem': 'rigg',
            '{elem=rigg}size': 'big',
            # leave this out as if it was recently added:
            # '{elem=rigg}{size=big}animal': 'dinosaur'
        }
    }

    # sets up stage with session layer
    stage = usdlib.stage.getStage(usdstage.GetRootLayer().identifier,
                                  variantOverrides=_overrides)
    # get a list of prim items for each prim with variant sets
    primItems = list(variants.iterVariablePrims(stage,
                                                lastRunData=_lastDefaults))
    assert len(primItems) == 1, 'test stage should only have the one prim'
    prim = primItems[0]

    muliHelper = variants.MultipleVariablePrimHelper(primItems)
    muliHelper.pinCurrentVariants()
    selections = variants.getVariantSelectionData(primItems)
    # these will be the same because every selection has an override, and it
    # will make sure our overrides were applied.
    assert selections == _overrides

    info = list(prim.getVariantSetInfo())
    assert info == [
        {'initialValue': 'rigg',  # override
         'defaultVariant': 'anim',  # != oldDefault, so will change below
         'variantNames': ['anim', 'rigg'],
         'setName': 'elem',
         'isPinnedValue': True,
         'oldDefault': 'rigg',
         'cacheKey': 'elem',
         'oldSelection': 'rigg'},
        {'initialValue': 'small',  # override
         'defaultVariant': 'big',  # does == oldDefault, so wont change below
         'variantNames': ['big', 'small'],
         'setName': 'size',
         'isPinnedValue': True,
         'oldDefault': 'big',
         'cacheKey': '{elem=rigg}size',
         'oldSelection': 'small'},
        {'initialValue': 'dinosaur',
         'defaultVariant': 'dinosaur',
         'variantNames': ['dinosaur'],
         'setName': 'animal',
         'isPinnedValue': True,
         'oldDefault': None,  # no record of variant from last run
         'cacheKey': '{elem=rigg}{size=small}animal',
         'oldSelection': 'dinosaur'}
    ]

    muliHelper.setNewDefaultVariants()
    newInfo = list(prim.getVariantSetInfo())
    assert newInfo == [
        {'initialValue': 'anim',  # this has changed to the new default
         'defaultVariant': 'anim',
         'variantNames': ['anim', 'rigg'],
         'setName': 'elem',
         'isPinnedValue': True,
         'oldDefault': 'rigg',
         'cacheKey': 'elem',
         'oldSelection': 'rigg'},  # still have the orig scene value here
        {'initialValue': 'blue',  # these sub-variants have also changed
         'defaultVariant': 'blue',
         'variantNames': ['blue'],
         'setName': 'color',
         'isPinnedValue': False,  # we havent seen these variants before.
         'oldDefault': None,
         'cacheKey': '{elem=anim}color',
         'oldSelection': None},
        {'initialValue': 'A02',
         'defaultVariant': 'A02',
         'variantNames': ['A01', 'A02', 'A03'],
         'setName': 'version',
         'isPinnedValue': False,
         'oldDefault': None,
         'cacheKey': '{elem=anim}{color=blue}version',
         'oldSelection': None}
    ]

    muliHelper.setInitialVariants()
    noChangeInfo = list(prim.getVariantSetInfo())
    assert info == noChangeInfo, 'should round-trip back to the same values.'


def test_multipleVariablePrimItem(usdstage):
    '''
    Test the mechanism that merges multiple prims variant information
    into only the variant sets that they have in common.
    '''
    # dict describing the usd stage that will be built for this test
    _variants = {
        '/world/hathi_jr': {
            'animal=elephant(default)': {
                'size=big': {
                    'color=rainbow': {},
                    'color=grey(default)': {},
                },
                'size=small(default)': {
                    'color=rainbow': {},
                    'color=grey(default)': {}
                }
            },
            'animal=tiger': {
                'size=big(default)': {
                    'color=orange': {}
                },
                'size=small': {
                    'color=orange': {}
                }
            }
        },
        '/world/hathi': {
            'animal=elephant(default)': {
                'size=big(default)': {
                    'color=rainbow': {},
                    'color=grey(default)': {},
                },
                'size=small': {
                    'color=rainbow': {},
                    'color=grey(default)': {}
                }
            },
            'animal=tiger': {
                'size=big(default)': {
                    'color=orange': {}
                },
                'size=small': {
                    'color=orange': {}
                }
            }
        },
        '/world/shere_kahn': {
            'animal=tiger(default)': {
                'size=big(default)': {
                    'color=orange': {}
                },
                'size=small': {
                    'color=orange': {}
                }
            }
        },
        '/world/baloo': {
            'animal=bear(default)': {
                'activities=bareNecessities(default)': {
                    'size=big(default)': {},
                },
            }
        }

    }
    createPrims(usdstage, _variants)

    # mock user overrides saved in the scene
    _overrides = {
        '/world/hathi_jr': {
            'animal': 'elephant',
            'size': 'small',
            'color': 'rainbow'
        }
    }
    # mock state of the stage last time asset manager was used, when the
    # elephants were defaulting to tigers
    _lastDefaults = {
        '/world/hathi': {
            'animal': 'tiger',
        },
        '/world/hathi_jr': {
            'animal': 'tiger',
        }
    }

    # sets up stage with session layer
    stage = usdlib.stage.getStage(usdstage.GetRootLayer().identifier,
                                  variantOverrides=_overrides)
    # get a list of prim items for each prim with variant sets
    primItems = list(variants.iterVariablePrims(stage,
                                                lastRunData=_lastDefaults))
    pathToItem = dict([(p.path, p) for p in primItems])

    multiHelper = variants.MultipleVariablePrimHelper(primItems)

    assert len(primItems) == 4, 'test stage should have 4 prims'
    multiHelper.pinCurrentVariants()

    info = list(multiHelper.getVariantSetInfo())
    # all four prims have only 1 variant in common that also has
    # intersecting choices: "size"
    assert info == [
        {'cacheKey': None,
         'defaultVariant': None,  # small for hathi jr, big for others
         'initialValue': variants.MULTIPLE_VALUES,
         'isPinnedValue': True,
         'oldDefault': None,
         'oldSelection': None,
         'setName': 'size',
         # "small" wont be in this list because its not an option for all
         # prims. Baloo can only be a big bear.
         'variantNames': [variants.MULTIPLE_VALUES, 'big']}
    ]

    bigAnimalPrims = [item for item in primItems
                      if item.path != '/world/hathi_jr']
    multiHelper = variants.MultipleVariablePrimHelper(bigAnimalPrims)
    bigInfo = list(multiHelper.getVariantSetInfo())
    # still includes baloo who has little in common with the others, but now
    # all the prims have size set to big and default to big
    expectedBigInfo = info[:]
    expectedBigInfo[0]['defaultVariant'] = 'big'
    expectedBigInfo[0]['initialValue'] = 'big'
    assert bigInfo == expectedBigInfo

    elephantPrims = [item for item in primItems
                     if item.path not in ('/world/shere_kahn',
                                          '/world/baloo')]
    multiHelper = variants.MultipleVariablePrimHelper(elephantPrims)
    info = list(multiHelper.getVariantSetInfo())
    # hathi and hathi jr are both elephants and have more in common
    assert info == [
        {'cacheKey': 'animal',
         'defaultVariant': 'elephant',
         'initialValue': 'elephant',
         'isPinnedValue': True,
         'oldDefault': 'tiger',
         'oldSelection': None,
         'setName': 'animal',
         'variantNames': ['elephant', 'tiger']},
        {'cacheKey': '{animal=elephant}size',
         'defaultVariant': None,  # different defaults
         'initialValue': variants.MULTIPLE_VALUES,  # different initial value
         'isPinnedValue': True,
         'oldDefault': None,
         'oldSelection': None,
         'setName': 'size',
         # however the same options are available
         'variantNames': [variants.MULTIPLE_VALUES, 'big', 'small']},
        {'cacheKey': None,
         'defaultVariant': 'grey',
         'initialValue': '< multiple values >',
         'isPinnedValue': True,
         'oldDefault': None,
         'oldSelection': None,
         'setName': 'color',
         'variantNames': ['< multiple values >', 'grey', 'rainbow']}
    ]

    # alter hathi_jr prim to big size
    pathToItem['/world/hathi_jr'].setVariantSelection('size', 'big')
    info = list(multiHelper.getVariantSetInfo())
    # now hathi jr. is all grown up and should be same as his pops except for
    # color
    assert info == [
        {'cacheKey': 'animal',
         'defaultVariant': 'elephant',
         'initialValue': 'elephant',
         'isPinnedValue': True,
         'oldDefault': 'tiger',
         'oldSelection': None,
         'setName': 'animal',
         'variantNames': ['elephant', 'tiger']},
        {'cacheKey': '{animal=elephant}size',
         'defaultVariant': None, # this ones still different
         'initialValue': 'big',  # but now this one is the same.
         'isPinnedValue': True,
         'oldDefault': None,
         'oldSelection': None,
         'setName': 'size',
         'variantNames': [variants.MULTIPLE_VALUES, 'big', 'small']},
        {'cacheKey': '{animal=elephant}{size=big}color',
         'defaultVariant': 'grey',
         'initialValue': variants.MULTIPLE_VALUES,
         'isPinnedValue': True,
         'oldDefault': None,
         'oldSelection': None,
         'setName': 'color',
         'variantNames': [variants.MULTIPLE_VALUES, 'grey', 'rainbow']}
    ]
