from typing import Dict, Iterator, List, NamedTuple, Optional, Tuple, Union


def getAssetName(prim):
    '''
    Return the prim's asset name as stored in assetInfo metadata

    Parameters
    ----------
    prim : Usd.Prim

    Returns
    -------
    Optional[str]
    '''
    assetInfo = prim.GetAssetInfo()
    if assetInfo and 'name' in assetInfo:
        return assetInfo['name']
