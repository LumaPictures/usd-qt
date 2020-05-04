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

#include "attributeProxy.h"
#include "utils.h"

#include <boost/range/adaptor/sliced.hpp>

PXR_NAMESPACE_OPEN_SCOPE

using BOOST_NS::adaptors::slice;
using std::remove_if;

VtTokenArray UsdQt_AttributeProxy::GetAllowedTokens() const {
    if (_attributes.size() < 1) return VtTokenArray();
    if (GetTypeName() != SdfValueTypeNames->Token) return VtTokenArray();

    TfToken allowedTokensStr("allowedTokens");

    VtTokenArray sharedAllowedTokens;
    if (!_attributes[0].GetMetadata(allowedTokensStr, &sharedAllowedTokens)) {
        return VtTokenArray();
    }

    auto sharedAllowedTokensEnd = sharedAllowedTokens.end();
    for (const auto &attribute : slice(_attributes, 1, _attributes.size())) {
        VtTokenArray allowedTokens;
        if (!attribute.GetMetadata(allowedTokensStr, &allowedTokens)) {
            return VtTokenArray();
        }
        sharedAllowedTokensEnd =
            remove_if(sharedAllowedTokens.begin(), sharedAllowedTokensEnd,
                      [&](const TfToken &token) {
                return UsdQt_ItemNotInArray(allowedTokens, token);
            });
    }

    sharedAllowedTokens.resize(sharedAllowedTokensEnd -
                               sharedAllowedTokens.begin());

    // waiting on bug http://bugzilla.pixar.com/show_bug.cgi?id=125316
    // sharedAllowedTokens.erase(sharedAllowedTokensEnd,
    //                           sharedAllowedTokens.end());
    return sharedAllowedTokens;
};

UsdQt_AttributeProxy::UsdQt_AttributeProxy(
    const std::vector<UsdAttribute> &attributes)
    : _attributes(attributes) {}

UsdQt_AttributeProxyRefPtr UsdQt_AttributeProxy::New(
    const std::vector<UsdAttribute> &attributes) {
    return TfCreateRefPtr(new UsdQt_AttributeProxy(attributes));
}

SdfVariability UsdQt_AttributeProxy::GetVariability() const {
    if (_attributes.size() < 1) {
        return SdfVariabilityUniform;
    }
    for (const auto &attribute : _attributes) {
        if (!attribute.GetVariability() == SdfVariabilityVarying) {
            return SdfVariabilityUniform;
        }
    }
    return SdfVariabilityVarying;
}

SdfValueTypeName UsdQt_AttributeProxy::GetTypeName() const {
    if (_attributes.size() < 1) {
        return SdfValueTypeName();
    }
    SdfValueTypeName sharedTypeName = _attributes[0].GetTypeName();
    for (const auto &attribute : slice(_attributes, 1, _attributes.size())) {
        if (attribute.GetTypeName() != sharedTypeName) {
            return SdfValueTypeName();
        }
    }
    return sharedTypeName;
}

bool UsdQt_AttributeProxy::Get(VtValue *result, UsdTimeCode time) const {
    if (_attributes.size() < 1) {
        (*result) = VtValue();
        return true;
    }
    VtValue sharedValue;
    _attributes[0].Get(&sharedValue, time);
    for (const auto &attribute : slice(_attributes, 1, _attributes.size())) {
        VtValue value;
        if (!attribute.Get(&value, time) || value != sharedValue) {
            (*result) = VtValue();
            return false;
        }
    }
    (*result) = sharedValue;
    return true;
}

bool UsdQt_AttributeProxy::Set(const VtValue &result, UsdTimeCode time) {
    bool success = true;
    for (auto &attribute : _attributes) {
        success &= attribute.Set(result, time);
    }
    return success;
}

bool UsdQt_AttributeProxy::Clear() {
    bool success = true;
    for (auto &attribute : _attributes) {
        success &= attribute.Clear();
    }
    return success;
}

bool UsdQt_AttributeProxy::ClearAtTime(UsdTimeCode time) {
    bool success = true;
    for (auto &attribute : _attributes) {
        success &= attribute.ClearAtTime(time);
    }
    return success;
}

void UsdQt_AttributeProxy::Block() {
    for (auto &attribute : _attributes) {
        attribute.Block();
    }
}

std::vector<UsdAttribute> &UsdQt_AttributeProxy::_GetObjects() {
    return _attributes;
}
const std::vector<UsdAttribute> &UsdQt_AttributeProxy::_GetObjects() const {
    return _attributes;
}

PXR_NAMESPACE_CLOSE_SCOPE
