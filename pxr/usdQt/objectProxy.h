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

#ifndef USDQT_OBJECTPROXY_H
#define USDQT_OBJECTPROXY_H

#include "pxr/pxr.h"
#include "pxr/usd/sdf/path.h"

#include "metadataProxy.h"
#include "proxyBase.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(UsdQt_ObjectProxy);

/// \brief Common super class of any proxy representing a list of UsdObjects
///
/// User customized types in general shouldn't subclass this, becaus the only
/// valid UsdObject types are Prim, Attribute, and Relationship.
class UsdQt_ObjectProxy : public UsdQt_ProxyBase {
public:
    /// \brief Check if any object explicilty refers to any path in the vector
    ///
    /// For example, let's say a proxy refers to
    ///   [Usd.Prim(/World/prim1), Usd.Prim(/World/prim2),
    ///    Usd.Prim(/World/prim3)]
    ///
    /// The SdfPathVector [/World/prim3, /World/SomeOthePrim] would return true
    /// because just one of the paths "/World/prim3" matches.
    ///
    /// The SdfPathVector [/World, /AnotherWorld] return false because no path
    /// matches exactly.
    ///
    /// The primary role of this function is to detect objects that may need
    /// to be updated because of ChangeInfo UsdNotices.
    virtual bool ContainsPath(const SdfPathVector&) const = 0;

    /// \brief Check if any object is a descendent or is any path in the vector
    ///
    /// For example, let's say a proxy refers to
    ///   [Usd.Prim(/World/prim1), Usd.Prim(/World/prim2),
    ///    Usd.Prim(/World/prim3)]
    ///
    /// The SdfPathVector [/World/prim3, /World/SomeOthePrim] would return true
    /// because the paths "/World/prim3" matches.
    ///
    /// The SdfPathVector [/World, /AnotherWorld] would also return true because
    /// the path "/World" is an ancestor of prim
    ///
    /// The SdfPathVector [/World/]
    ///
    /// The primary role of this function is to detect objects that may need
    /// to be updated because of Resync UsdNotices.
    virtual bool ContainsPathOrDescendent(const SdfPathVector&) const = 0;
};

template <typename T, SdfSpecType SpecType>
class UsdQt_ObjectProxyBase : public UsdQt_ObjectProxy {
private:
    virtual std::vector<T>& _GetObjects() = 0;
    virtual const std::vector<T>& _GetObjects() const = 0;

public:
    /// \brief Create a new proxy for the 'field' metadata for all attributes
    ///
    /// If all attributes don't have metadata 'field', no proxy is created and
    /// NULL is returend.
    UsdQt_MetadataProxyRefPtr CreateMetadataProxy(const TfToken& field);
    virtual bool ContainsPathOrDescendent(const SdfPathVector&) const override;
    virtual bool ContainsPath(const SdfPathVector&) const override;

    /// \brief Return metadata fields that ALL attributes share.
    TfTokenVector GetMetadataFields() const;

    /// \brief Get the name that all attributes for this proxy share
    ///
    /// If the name for all attributes is not equal, an empty TfToken is
    /// returned.
    TfToken GetName() const;

    /// \brief Get the documentation from the FIRST attribute for this proxy.
    /// Unlike most methods, we don't diff attempt to mediate disparate
    /// opinions for the documentation metadata, as large strings could be
    /// expensive to diff and unlikely to differ.
    std::string GetDocumentation() const;

    /// \brief Return true if ALL attributes for this proxy are valid.
    bool IsValid() const;

    /// \brief Return the number of attributes this proxy refers to.
    size_t GetSize() const;
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif
