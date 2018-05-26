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

#ifndef USDQT_ATTRIBUTEPROXY_H
#define USDQT_ATTRIBUTEPROXY_H

#include <string>
#include <vector>

#include "pxr/pxr.h"
#include "pxr/base/tf/token.h"
#include "pxr/usd/usd/attribute.h"

#include "metadataProxy.h"
#include "objectProxy.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(UsdQt_AttributeProxy);

/// \class UsdQt_AttributeProxy
/// \brief Proxy interface for an ordered list of attributes
///
/// An attribute proxy can be used to as a single interface to query and edit
/// data on multiple attributes across disparate prims.
///
/// As much as possible, we try to make the API method names, parameters,
/// and return types match UsdAttribute for duck typing in python.  Code
/// that one wrote to operate on an Attribute should whenever possible also
/// work on an attribute proxy.
class UsdQt_AttributeProxy
    : public UsdQt_PropertyProxyBase<UsdAttribute, SdfSpecTypeAttribute> {
private:
    std::vector<UsdAttribute> _attributes;
    explicit UsdQt_AttributeProxy(const std::vector<UsdAttribute>& attributes);

protected:
    virtual const std::vector<UsdAttribute>& _GetObjects() const override;
    virtual std::vector<UsdAttribute>& _GetObjects() override;

public:
    static UsdQt_AttributeProxyRefPtr New(
        const std::vector<UsdAttribute>& attributes);

    /// \brief Get the variability that all attributes for this proxy share
    ///
    /// If variability for all attributes is not equal, then
    /// SdfVariabilityUniform is returned as a fallback.
    SdfVariability GetVariability() const;

    /// \brief Get the value type name that all attributes for this proxy share
    ///
    /// If the typeName for all attributes is not equal, an empty
    /// SdfValueTypeName is returned.
    SdfValueTypeName GetTypeName() const;

    /// \brief Return the list of all attributes for this proxy.
    const std::vector<UsdAttribute>& GetAttributes() { return _attributes; }

    /// \brief Get the shared value that all attributes for this proxy share
    ///
    /// If the value for all attributes is not equal, an empty VtValue is
    /// stored in 'result'.
    ///
    /// Returns true all UsdAttribute Get requests  were successful.
    bool Get(VtValue* result, UsdTimeCode timeCode) const;

    /// \brief Set a value on all attributes for this proxy.
    ///
    /// Returns true if all UsdAttribute Set requests were successful.
    bool Set(const VtValue& value, UsdTimeCode timeCode);

    /// \brief Clear time samples and defaults on all attributes for this proxy.
    ///
    /// Returns true if all UsdAttribute Clear requests were successful.
    bool Clear();

    /// \brief Clear value at time code  on all attributes for this proxy.
    ///
    /// Returns true if all UsdAttribute ClearAtTime requests were successful.
    bool ClearAtTime(UsdTimeCode time);

    /// \brief Authors a block on all attriutes for this proxy.
    ///
    /// NOTE: BlockValue doesn't return a bool only because UsdAttribute Block
    /// doesn't return a bool.  If this changes, this should be updated in kind.
    void Block();

    /// \brief Get the intersection of allowedTokens for all attributes of this
    /// proxy.
    ///
    /// This is only valid for attributes with valueType 'token'
    VtTokenArray GetAllowedTokens() const;
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif
