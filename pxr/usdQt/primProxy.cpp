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

#include "primProxy.h"

#include <boost/range/adaptor/sliced.hpp>

using BOOST_NS::adaptors::slice;

PXR_NAMESPACE_OPEN_SCOPE

UsdQt_PrimProxy::UsdQt_PrimProxy(const std::vector<UsdPrim>& prims)
    : _prims(prims) {}

UsdQt_PrimProxyRefPtr UsdQt_PrimProxy::New(const std::vector<UsdPrim>& prims) {
    return TfCreateRefPtr(new UsdQt_PrimProxy(prims));
}

std::vector<std::string> UsdQt_PrimProxy::GetNames() {
    std::vector<std::string> names;
    for (const auto& prim : _prims) {
        names.push_back(prim.GetName());
    }
    return names;
}

const std::vector<UsdPrim>& UsdQt_PrimProxy::GetPrims() { return _prims; }

TfTokenVector UsdQt_PrimProxy::GetAttributeNames() {
    if (_prims.size() < 1) return TfTokenVector();

    std::vector<UsdAttribute> firstAttributes = _prims[0].GetAttributes();
    std::vector<TfToken> sharedNames;
    for (const auto& attribute : firstAttributes) {
        sharedNames.push_back(attribute.GetName());
    }

    auto sharedNamesEnd = sharedNames.end();
    for (const auto& prim : slice(_prims, 1, _prims.size())) {
        sharedNamesEnd = remove_if(
            sharedNames.begin(), sharedNamesEnd,
            [&](const TfToken& name) { return !prim.HasAttribute(name); });
    }
    sharedNames.erase(sharedNamesEnd, sharedNames.end());
    return sharedNames;
}

TfTokenVector UsdQt_PrimProxy::GetRelationshipNames() {
    if (_prims.size() < 1) return TfTokenVector();

    std::vector<UsdRelationship> firstRelationships =
        _prims[0].GetRelationships();
    TfTokenVector sharedNames;
    for (const auto& relationship : firstRelationships) {
        sharedNames.push_back(relationship.GetName());
    }

    auto sharedNamesEnd = sharedNames.end();
    for (const auto& prim : slice(_prims, 1, _prims.size())) {
        sharedNamesEnd = remove_if(
            sharedNames.begin(), sharedNamesEnd,
            [&](const TfToken& name) { return !prim.HasRelationship(name); });
    }
    sharedNames.erase(sharedNamesEnd, sharedNames.end());
    return sharedNames;
}

UsdQt_RelationshipProxyRefPtr UsdQt_PrimProxy::CreateRelationshipProxy(
    const TfToken& name) {
    std::vector<UsdRelationship> sharedRelationships;

    for (const auto& prim : _prims) {
        if (!prim.HasRelationship(name))
            return UsdQt_RelationshipProxy::New(std::vector<UsdRelationship>());
        sharedRelationships.push_back(prim.GetRelationship(name));
    }
    return UsdQt_RelationshipProxy::New(sharedRelationships);
}

UsdQt_VariantSetsProxyRefPtr UsdQt_PrimProxy::CreateVariantSetsProxy() {
    return UsdQt_VariantSetsProxy::New(_prims);
}

UsdQt_AttributeProxyRefPtr UsdQt_PrimProxy::CreateAttributeProxy(
    const TfToken& name) {
    std::vector<UsdAttribute> sharedAttributes;

    for (const auto& prim : _prims) {
        if (!prim.HasAttribute(name)) return NULL;
        sharedAttributes.push_back(prim.GetAttribute(name));
    }
    return UsdQt_AttributeProxy::New(sharedAttributes);
}

void UsdQt_PrimProxy::ClearExpired() {
    auto primsEnd = remove_if(_prims.begin(), _prims.end(),
                              [&](const UsdPrim& prim) { return !prim; });
    _prims.erase(primsEnd, _prims.end());
}

std::vector<UsdPrim>& UsdQt_PrimProxy::_GetObjects() { return _prims; }
const std::vector<UsdPrim>& UsdQt_PrimProxy::_GetObjects() const {
    return _prims;
}
PXR_NAMESPACE_CLOSE_SCOPE
