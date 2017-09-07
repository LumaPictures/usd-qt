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

# Use this for site customization of Qt binding versions.  This code targets
# PySide2, but may be compatible with a variety of other shims/APIs.  Override
# this file to specify any site specific preferences.

from __future__ import absolute_import

def _get_proxied_module():
    import os
    import importlib
    mod = os.environ.get('PXR_QT_PYTHON_BINDING', 'PySide2')
    return importlib.import_module(mod)

globals().update(_get_proxied_module().__dict__)

del _get_proxied_module
