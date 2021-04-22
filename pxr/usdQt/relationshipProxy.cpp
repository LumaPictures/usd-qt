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

#include "relationshipProxy.h"
#include "utils.h"

PXR_NAMESPACE_OPEN_SCOPE

using BOOST_NS::adaptors::slice;

UsdQt_RelationshipProxy::UsdQt_RelationshipProxy(
    const std::vector<UsdRelationship>& rels)
    : _relationships(rels) {}

UsdQt_RelationshipProxyRefPtr UsdQt_RelationshipProxy::New(
    const std::vector<UsdRelationship>& rels) {
    return TfCreateRefPtr(new UsdQt_RelationshipProxy(rels));
}

bool UsdQt_RelationshipProxy::GetTargets(SdfPathVector* result) const {
    if (!result) return false;
    if (_relationships.size() < 1) {
        result->clear();
        return true;
    }
    SdfPathVector sharedTargets;
    if (!_relationships[0].GetTargets(&sharedTargets)) {
        result->clear();
        return false;
    }

    auto sharedTargetsEnd = sharedTargets.end();
    for (const auto& relationship :
         slice(_relationships, 1, _relationships.size())) {
        SdfPathVector targets;
        if (!relationship.GetTargets(&targets)) {
            result->clear();
            return false;
        }
        sharedTargetsEnd = remove_if(sharedTargets.begin(), sharedTargetsEnd,
                                     [&](const SdfPath& target) {
            return UsdQt_ItemNotInVector(targets, target);
        });
    }

    sharedTargets.erase(sharedTargetsEnd, sharedTargets.end());
    result->assign(sharedTargets.begin(), sharedTargets.end());
    return true;
}

bool UsdQt_RelationshipProxy::GetForwardedTargets(SdfPathVector* result) const {
    if (!result) return false;
    if (_relationships.size() < 1) {
        result->clear();
        return true;
    }
    SdfPathVector sharedTargets;
    if (!_relationships[0].GetForwardedTargets(&sharedTargets)) {
        result->clear();
        return false;
    }

    auto sharedTargetsEnd = sharedTargets.end();
    for (const auto& relationship :
         slice(_relationships, 1, _relationships.size())) {
        SdfPathVector targets;
        if (!relationship.GetForwardedTargets(&targets)) {
            (*result) = SdfPathVector();
            return false;
        }
        sharedTargetsEnd = remove_if(sharedTargets.begin(), sharedTargetsEnd,
                                     [&](const SdfPath& target) {
            return UsdQt_ItemNotInVector(targets, target);
        });
    }

    sharedTargets.erase(sharedTargetsEnd, sharedTargets.end());
    result->assign(sharedTargets.begin(), sharedTargets.end());
    return true;
}

bool UsdQt_RelationshipProxy::ClearTargets(bool removeSpec) {
    bool success = true;
    for (const auto& relationship : _relationships) {
        success &= relationship.ClearTargets(removeSpec);
    }
    return success;
}

std::vector<UsdRelationship>& UsdQt_RelationshipProxy::_GetObjects() {
    return _relationships;
}
const std::vector<UsdRelationship>& UsdQt_RelationshipProxy::_GetObjects()
    const {
    return _relationships;
}

PXR_NAMESPACE_CLOSE_SCOPE
