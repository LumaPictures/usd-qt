#
# Copyright 2018 Luma Pictures
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

from __future__ import absolute_import

from pxr import Sdf

from ._Qt import QtWidgets

if False:
    from typing import *
    from pxr import Usd


class FallbackException(Exception):
    """Raised if a customized function fails and wants to fallback to the
    default implementation."""
    pass


class UsdQtHooks(object):
    """Simple aggregator for overrideable hooks within a UsdQt app.

    This allows for easy site-specific overrides to common operations like
    browsing for a reference path, etc.
    """
    _registered = {}

    @classmethod
    def Register(cls, name, func):
        # type: (str, Callable) -> None
        """
        Parameters
        ----------
        name : str
        func : Callable
        """
        cls._registered.setdefault(name, []).insert(0, func)

    @classmethod
    def Call(cls, name, *args, **kwargs):
        # type: (str, *Any, **Dict[str, Any]) -> Any
        """
        Parameters
        ----------
        name : str
        args : *Any
        kwargs : **Dict[str, Any]

        Returns
        -------
        Any
        """
        for func in cls._registered[name]:
            try:
                return func(*args, **kwargs)
            except FallbackException:
                continue


def GetReferencePath(parent, stage=None):
    # type: (QtWidgets.QWidget, Optional[Usd.Stage]) -> str
    """Prompts the user for a reference path.

    Parameters
    ----------
    parent : QtWidgets.QWidget
    stage : Optional[Usd.Stage]

    Returns
    -------
    str
    """
    name, _ = QtWidgets.QInputDialog.getText(parent, 'Add Reference',
                                             'Enter Usd Layer Identifier:')
    return name


def GetId(layer):
    # type: (Sdf.Layer) -> str
    """Returns the unique key used to store the original contents of a layer.
    This is currently used for change tracking in the outliner app.

    Parameters
    ----------
    layer : Sdf.Layer

    Returns
    -------
    str
    """
    if isinstance(layer, Sdf.Layer):
        return layer.identifier
    return str(layer)


UsdQtHooks.Register('GetReferencePath', GetReferencePath)
UsdQtHooks.Register('GetId', GetId)
