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
//

#include <boost/range/adaptor/sliced.hpp>

#include "pxr/usd/usd/attribute.h"
#include "pxr/usd/usd/object.h"
#include "pxr/usd/usd/prim.h"
#include "pxr/usd/usd/relationship.h"

#include "objectProxy.h"

using boost::adaptors::slice;
using std::remove_if;

PXR_NAMESPACE_OPEN_SCOPE;

template <typename T, SdfSpecType SpecType>
UsdQt_MetadataProxyRefPtr
UsdQt_ObjectProxyBase<T, SpecType>::CreateMetadataProxy(const TfToken& field) {
    std::vector<UsdObject> parentObjects;
    for (const T& objectIt : _GetObjects()) {
        UsdObject object = objectIt.template As<UsdObject>();
        parentObjects.push_back(object);
    }
    return UsdQt_MetadataProxy::New(parentObjects, field);
}

template <typename T, SdfSpecType SpecType>
bool UsdQt_ObjectProxyBase<T, SpecType>::ContainsPathOrDescendent(
    const SdfPathVector& potentialPaths) const {
    for (auto path : potentialPaths) {
        for (auto object : _GetObjects()) {
            // return true if the paths are equal or of if the shared
            //             // common parent is the path we are testing against.
            if (!path.IsEmpty() &&
                object.GetPath().GetCommonPrefix(path) == path) {
                return true;
            }
        }
    }
    return false;
}

template <typename T, SdfSpecType SpecType>
bool UsdQt_ObjectProxyBase<T, SpecType>::ContainsPath(
    const SdfPathVector& potentialPaths) const {
    for (auto path : potentialPaths) {
        for (auto object : _GetObjects()) {
            if (!path.IsEmpty() && object.GetPath() == path) return true;
        }
    }
    return false;
}

template <typename T, SdfSpecType SpecType>
TfTokenVector UsdQt_ObjectProxyBase<T, SpecType>::GetMetadataFields() const {
    if (_GetObjects().size() < 1) {
        return TfTokenVector();
    }

    TfTokenVector fields = SdfSchema::GetInstance().GetMetadataFields(SpecType);
    auto newFieldsEnd =
        std::remove_if(fields.begin(), fields.end(), [&](const TfToken& field) {
            return SdfSchema::GetInstance().GetMetadataFieldDisplayGroup(
                       SdfSpecTypeAttribute, field) == TfToken("deprecated");
        });
    fields.erase(newFieldsEnd, fields.end());
    std::sort(fields.begin(), fields.end());
    return fields;
}

template <typename T, SdfSpecType SpecType>
TfToken UsdQt_ObjectProxyBase<T, SpecType>::GetName() const {
    if (_GetObjects().size() < 1) {
        return TfToken();
    }
    TfToken sharedName = _GetObjects()[0].GetName();
    for (const auto& object : slice(_GetObjects(), 1, _GetObjects().size())) {
        if (object.GetName() != sharedName) {
            return TfToken();
        }
    }
    return sharedName;
}

template <typename T, SdfSpecType SpecType>
std::string UsdQt_ObjectProxyBase<T, SpecType>::GetDocumentation() const {
    if (_GetObjects().size() < 1) return std::string();
    return _GetObjects()[0].GetDocumentation();
}

template <typename T, SdfSpecType SpecType>
bool UsdQt_ObjectProxyBase<T, SpecType>::IsValid() const {
    return std::all_of(
        this->_GetObjects().begin(), this->_GetObjects().end(),
        [](const UsdObject& object) { return object.IsValid(); });
}

template <typename T, SdfSpecType SpecType>
size_t UsdQt_ObjectProxyBase<T, SpecType>::GetSize() const {
    return _GetObjects().size();
}

template <typename T, SdfSpecType SpecType>
bool UsdQt_PropertyProxyBase<T, SpecType>::IsAuthored() const {
    return std::any_of(
        this->_GetObjects().begin(), this->_GetObjects().end(),
        [](const UsdProperty& property) { return property.IsAuthored(); });
}

template <typename T, SdfSpecType SpecType>
bool UsdQt_PropertyProxyBase<T, SpecType>::IsAuthoredAt(
    const UsdEditTarget& editTarget) const {
    return std::any_of(this->_GetObjects().begin(), this->_GetObjects().end(),
                       [&editTarget](const T& property) {
                           return property.IsAuthoredAt(editTarget);
                       });
}

template <typename T, SdfSpecType SpecType>
bool UsdQt_PropertyProxyBase<T, SpecType>::IsDefined() const {
    return std::any_of(this->_GetObjects().begin(), this->_GetObjects().end(),
                       [](const T& property) { return property.IsDefined(); });
}

template class UsdQt_ObjectProxyBase<UsdPrim, SdfSpecTypePrim>;
template class UsdQt_ObjectProxyBase<UsdAttribute, SdfSpecTypeAttribute>;
template class UsdQt_ObjectProxyBase<UsdRelationship, SdfSpecTypeRelationship>;

template class UsdQt_PropertyProxyBase<UsdAttribute, SdfSpecTypeAttribute>;
template class UsdQt_PropertyProxyBase<UsdRelationship, SdfSpecTypeRelationship>;


PXR_NAMESPACE_CLOSE_SCOPE
