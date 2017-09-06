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

#ifndef USDQT_METADATAPROXY_H
#define USDQT_METADATAPROXY_H

#include <vector>
#include <string>

#include "pxr/pxr.h"
#include "pxr/base/tf/token.h"
#include "pxr/base/vt/value.h"
#include "pxr/usd/usd/object.h"
#include "pxr/usd/usd/stage.h"

#include "proxyBase.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(UsdQt_MetadataProxy);
TF_DECLARE_WEAK_AND_REF_PTRS(UsdQt_MetadataDictKeyProxy);

/// \class UsdQt_MetadataProxy
/// \brief Proxy interface for metadata on a list of UsdObjects
///
/// A metadata proxy can be used to as a single interface to query and edit
/// metadata on multiple UsdObjects
class UsdQt_MetadataProxy : public UsdQt_ProxyBase {
private:
    std::vector<UsdObject> _objects;
    TfToken _field;
    explicit UsdQt_MetadataProxy(const std::vector<UsdObject>& objects,
                                 TfToken field);

public:
    static UsdQt_MetadataProxyRefPtr New(const std::vector<UsdObject>& objects,
                                         TfToken field);
                                         
    const std::vector<UsdObject>& GetObjects(){return _objects;}

    /// \brief Get the name of the metdata field for this proxy.
    TfToken GetName() const;

    /// \brief Get the type of the metdata field for this proxy.
    TfType GetType() const;

    /// \brief Get the shared value of metdata for all objects in this proxy.
    ///
    /// If all values are not the same, result will be an empty VtValue.
    /// This method returns true if all metadata Get requests were successful.
    bool GetValue(VtValue* result) const;

    /// \brief Set the value of metdata for all objects in this proxy.
    ///
    /// This method returns true if all metadata Set requests were successful.
    bool SetValue(const VtValue& value);

    /// \brief Clear the value of metdata for all objects in this proxy.
    ///
    /// This method returns true if all metadata Clearrequests were successful.
    bool ClearValue();

    /// \brief Get the intersection of all dictionary keys for this metadata.
    ///
    /// Just as we provide a specailized interface for VariantSet metadata
    /// It may make sense to provide a specialized interface for VtDictionary
    /// Metadata to avoid polluting the MetadataProxy API.
    std::vector<std::string> GetDictKeys() const;

    /// \brief Create a proxy for this entry in a metadata dictionary
    UsdQt_MetadataDictKeyProxyRefPtr CreateMetadataDictKeyProxy(
        const TfToken& dictKey);

    /// \brief Return the number of UsdObjects this proxy refers to.
    size_t GetSize() const { return _objects.size(); }
};

/// \class UsdQt_MetadataDictKeyProxy
/// \brief Proxy interface for an entry in a metadata dictionary
///
/// A metadata dict key proxy can be used to as a single interface to query and
/// edit a single entry of a metadata dictionary on multiple UsdObjects
class UsdQt_MetadataDictKeyProxy : public UsdQt_ProxyBase {
private:
    std::vector<UsdObject> _objects;
    TfToken _field;
    TfToken _dictKey;
    explicit UsdQt_MetadataDictKeyProxy(const std::vector<UsdObject>& objects,
                                        TfToken field, TfToken dictKey);

public:
    static UsdQt_MetadataDictKeyProxyRefPtr New(
        const std::vector<UsdObject>& objects, TfToken field, TfToken dictKey);

    /// \brief Get the name of the metadata field that refers to this dictionary
    TfToken GetDictName() const;

    /// \brief Get the name of the key of the entry in this dictionary
    TfToken GetEntryName() const;

    /// \brief Get the shared value of this entry in the dictionary
    ///
    /// Return true if all GetMetadataByDictKey requests are succesful.
    /// If the values of the entry are not eqaul, 'result' is set to an empty
    /// VtValue
    bool GetValue(VtValue* result) const;

    /// \brief Set the value of this entry in the dictionary for all objects
    ///
    /// Return true if all SetMetadataByDictKey requests are succesful.
    bool SetValue(const VtValue& value);

    /// \brief Clear the value of this entry in the dictionary for all objects
    ///
    /// Return true if all ClearMetadataByDictKey requests are succesful.
    bool ClearValue();

    /// \brief Get the type of the metdata field for this proxy.
    TfType GetType() const;    

    /// \brief Return the number of UsdObjects this proxy refers to.
    size_t GetSize() const { return _objects.size(); }
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif
