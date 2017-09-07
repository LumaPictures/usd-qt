//
// Copyright 2017 Pixar
//
// Licensed under the Apache License, Version 2.0 (the "Apache License")
// with the following modification; you may not use this file except in
// compliance with the Apache License and the following modification to it:
// Section 6. Trademarks. is deleted and replaced with:
//
// 6. Trademarks. This License does not grant permission to use the trade
//    names, trademarks, service marks, or product names of the Licensor
//    and its affiliates, except as required to comply with Section 4(c) of
//    the License and to reproduce the content of the NOTICE file.
//
// You may obtain a copy of the Apache License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the Apache License with the above modification is
// distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied. See the Apache License for the specific
// language governing permissions and limitations under the Apache License.
//

#ifndef USDQT_DISPLAYGROUPPROXY_H
#define USDQT_DISPLAYGROUPPROXY_H

#include "pxr/pxr.h"
#include "pxr/base/tf/token.h"

#include "proxyBase.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(UsdQt_DisplayGroupProxy);

/// \class UsdQt_DisplayGroupProxy
/// \brief Proxy interface for an display group
class UsdQt_DisplayGroupProxy : public UsdQt_ProxyBase {
private:
    TfToken _name;
    explicit UsdQt_DisplayGroupProxy(const TfToken& displayName);

public:
    static UsdQt_DisplayGroupProxyRefPtr New(const TfToken& displayName);

    /// \brief Return the name of the displayGroup
    TfToken GetName() const;
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif