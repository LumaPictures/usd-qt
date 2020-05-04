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

#include "metadataProxy.h"

#include <boost/range/adaptor/sliced.hpp>


PXR_NAMESPACE_OPEN_SCOPE

using BOOST_NS::adaptors::slice;

UsdQt_MetadataProxy::UsdQt_MetadataProxy(const std::vector<UsdObject>& objects,
                                         TfToken field)
    : _objects(objects), _field(field) {}

UsdQt_MetadataProxyRefPtr UsdQt_MetadataProxy::New(
    const std::vector<UsdObject>& objects, TfToken field) {
    return TfCreateRefPtr(new UsdQt_MetadataProxy(objects, field));
}

TfType UsdQt_MetadataProxy::GetType() const {
    return SdfSchema::GetInstance().GetFallback(_field).GetType();
}

TfToken UsdQt_MetadataProxy::GetName() const { return _field; }

bool UsdQt_MetadataProxy::GetValue(VtValue* result) const {
    if (_objects.size() < 1) {
        (*result) = VtValue();
        return true;
    }
    VtValue sharedValue;
    _objects[0].GetMetadata(_field, &sharedValue);
    for (const auto& object : slice(_objects, 1, _objects.size())) {
        VtValue value;
        if (!object.GetMetadata(_field, &value) || value != sharedValue) {
            (*result) = VtValue();
            return false;
        }
    }
    (*result) = sharedValue;
    return true;
}

bool UsdQt_MetadataProxy::SetValue(const VtValue& value) {
    bool success = true;
    for (auto& object : _objects) {
        success &= object.SetMetadata(_field, value);
    }
    return success;
}

bool UsdQt_MetadataProxy::ClearValue() {
    bool success = true;
    for (auto& object : _objects) {
        success &= object.ClearMetadata(_field);
    }
    return success;
};

std::vector<std::string> UsdQt_MetadataProxy::GetDictKeys() const {
    if (GetType() != TfType::FindByName("VtDictionary")) {
        TF_CODING_ERROR("Metadata isn't a VtDictionary.");
        return std::vector<std::string>();
    }
    if (_objects.size() == 0) return std::vector<std::string>();
    VtDictionary dict;
    if (!_objects[0].GetMetadata(_field, &dict))
        return std::vector<std::string>();

    std::vector<std::string> sharedKeys;
    for (const auto& key : dict) {
        sharedKeys.push_back(key.first);
    }

    auto sharedKeysEnd = sharedKeys.end();

    for (const auto& object : slice(_objects, 1, _objects.size())) {
        sharedKeysEnd = remove_if(sharedKeys.begin(), sharedKeysEnd,
                                  [&](const std::string& key) {
            return !object.HasMetadataDictKey(_field, TfToken(key));
        });
    }
    sharedKeys.erase(sharedKeysEnd, sharedKeys.end());
    return sharedKeys;
}

UsdQt_MetadataDictKeyProxyRefPtr
UsdQt_MetadataProxy::CreateMetadataDictKeyProxy(const TfToken& dictKey) {
    if (GetType() != TfType::FindByName("VtDictionary")) {
        return NULL;
    }
    std::vector<UsdObject> parentObjects;
    for (const auto& object : _objects) {
        if (!object.HasMetadataDictKey(_field, dictKey)) return NULL;
        parentObjects.push_back(object.As<UsdObject>());
    }
    return UsdQt_MetadataDictKeyProxy::New(parentObjects, _field, dictKey);
}

UsdQt_MetadataDictKeyProxy::UsdQt_MetadataDictKeyProxy(
    const std::vector<UsdObject>& objects, TfToken field, TfToken dictKey)
    : _objects(objects), _field(field), _dictKey(dictKey) {}

UsdQt_MetadataDictKeyProxyRefPtr UsdQt_MetadataDictKeyProxy::New(
    const std::vector<UsdObject>& objects, TfToken field, TfToken dictKey) {
    return TfCreateRefPtr(
        new UsdQt_MetadataDictKeyProxy(objects, field, dictKey));
}

TfToken UsdQt_MetadataDictKeyProxy::GetEntryName() const { return _dictKey; }

TfToken UsdQt_MetadataDictKeyProxy::GetDictName() const { return _field; }

bool UsdQt_MetadataDictKeyProxy::GetValue(VtValue* result) const {
    if (_objects.size() < 1) {
        (*result) = VtValue();
        return true;
    }
    VtValue sharedValue;
    _objects[0].GetMetadataByDictKey(_field, _dictKey, &sharedValue);
    for (const auto& object : slice(_objects, 1, _objects.size())) {
        VtValue value;
        if (!object.GetMetadataByDictKey(_field, _dictKey, &value) ||
            value != sharedValue) {
            (*result) = VtValue();
            return false;
        }
    }
    (*result) = sharedValue;
    return true;
}

bool UsdQt_MetadataDictKeyProxy::SetValue(const VtValue& value) {
    bool success = true;
    for (auto& object : _objects) {
        success &= object.SetMetadataByDictKey(_field, _dictKey, value);
    }
    return success;
}

bool UsdQt_MetadataDictKeyProxy::ClearValue() {
    bool success = true;
    for (auto& object : _objects) {
        success &= object.ClearMetadataByDictKey(_field, _dictKey);
    }
    return success;
}

/// \brief Get the type of the metdata field for this proxy.
TfType UsdQt_MetadataDictKeyProxy::GetType() const {
    VtValue temp;
    if (GetValue(&temp)) return temp.GetType();
    return TfType();
}

PXR_NAMESPACE_CLOSE_SCOPE
