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

#ifndef USDQT_PRIMSPROXY_H
#define USDQT_PRIMSPROXY_H

#include "pxr/pxr.h"
#include "pxr/usd/usd/prim.h"

#include "attributeProxy.h"
#include "metadataProxy.h"
#include "objectProxy.h"
#include "relationshipProxy.h"
#include "variantSetsProxy.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(UsdQt_PrimProxy);

/// \class UsdQt_PrimProxy
/// \brief Proxy interface for an ordered list of prims
///
/// A prim proxy can be used to as a single interface to query and edit
/// data on multiple prims.
///
/// When a vector of properties is returned, the order is determined
/// by the first prim in the list.
///
/// NOTE: Nothing about this interface enforces that the prims must be
/// on the same stage.  While we aren't taking advantage of this yet,
/// this could be used to enable multi-stage/shot editing workflows and
/// tools.
class UsdQt_PrimProxy : public UsdQt_ObjectProxyBase<UsdPrim, SdfSpecTypePrim> {
private:
    std::vector<UsdPrim> _prims;
    explicit UsdQt_PrimProxy(const std::vector<UsdPrim>& prims);

protected:
    virtual const std::vector<UsdPrim>& _GetObjects() const override;
    virtual std::vector<UsdPrim>& _GetObjects() override;

public:
    static UsdQt_PrimProxyRefPtr New(const std::vector<UsdPrim>& prims);

    /// \brief Return the name of all prims (not their paths)
    std::vector<std::string> GetNames();

    /// \brief Return the prims this proxy refers to
    const std::vector<UsdPrim>& GetPrims();

    /// \brief Get the names of attributes that ALL prims for this proxy share
    std::vector<TfToken> GetAttributeNames();

    /// \brief Create a proxy if ALL prims for this proxy have a 'name'
    /// attribute
    UsdQt_AttributeProxyRefPtr CreateAttributeProxy(const TfToken& name);

    /// \brief Get the names of relationships that ALL prims for this proxy
    /// share
    std::vector<TfToken> GetRelationshipNames();

    /// \brief Create a proxy if ALL prims for this proxy have a 'name'
    /// relationship
    UsdQt_RelationshipProxyRefPtr CreateRelationshipProxy(const TfToken& name);

    /// \brief Check if one or more of the prims for this proxy have variant
    /// sets.
    bool HasVariantSets();

    /// \brief Create a proxy if one or more prims for this proxy have variant
    /// sets.
    UsdQt_VariantSetsProxyRefPtr CreateVariantSetsProxy();

    /// \brief Strip any expired prims
    void ClearExpired();
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif
