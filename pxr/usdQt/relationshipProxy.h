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

#ifndef USDQT_RELATIONSHIPPROXY_H
#define USDQT_RELATIONSHIPPROXY_H

#include <vector>
#include <string>

#include "pxr/pxr.h"
#include "pxr/base/tf/token.h"
#include "pxr/usd/usd/relationship.h"

#include "metadataProxy.h"
#include "objectProxy.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(UsdQt_RelationshipProxy);

/// \class UsdQt_RelationshipProxy
/// \brief Proxy interface for a relationship
class UsdQt_RelationshipProxy
    : public UsdQt_PropertyProxyBase<UsdRelationship, SdfSpecTypeRelationship> {
private:
    std::vector<UsdRelationship> _relationships;
    explicit UsdQt_RelationshipProxy(const std::vector<UsdRelationship>& rels);

protected:
    virtual const std::vector<UsdRelationship>& _GetObjects() const override;
    virtual std::vector<UsdRelationship>& _GetObjects() override;

public:
    static UsdQt_RelationshipProxyRefPtr New(
        const std::vector<UsdRelationship>& rels);

    /// \brief Return the list of all relationships for this proxy.
    const std::vector<UsdRelationship>& GetRelationships();

    /// \brief Get the intersection of targets for the contained relationships
    ///
    /// Return true if all GetTargets requests are succesful on the
    /// UsdRelationship contents.
    bool GetTargets(SdfPathVector* result) const;

    /// \brief Get the intersection of forwarded targets for the contained
    /// relationships
    ///
    /// Return true if all GetForwardedTargets requests are succesful on the
    /// UsdRelationship contents.
    bool GetForwardedTargets(SdfPathVector* result) const;

    /// \brief Clear targets for all relationshps on this proxy.
    ///
    /// Returns true if all UsdRelationship ClearTargets requests were
    /// successful.
    bool ClearTargets(bool removeSpec);

    /// \brief Authors a block on all relationships for this proxy.
    bool BlockTargets();
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif
