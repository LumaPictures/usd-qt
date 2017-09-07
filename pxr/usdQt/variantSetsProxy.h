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

#ifndef USDQT_VARIANTSETSPROXY_H
#define USDQT_VARIANTSETSPROXY_H

#include <vector>
#include <string>

#include "pxr/pxr.h"
#include "pxr/base/tf/token.h"
#include "pxr/usd/usd/variantSets.h"

#include "proxyBase.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(UsdQt_VariantSetsProxy);
TF_DECLARE_WEAK_AND_REF_PTRS(UsdQt_VariantSetProxy);

/// \class UsdQt_VariantSetsProxy
/// \brief Proxy interface for an ordered list of 'UsdVariantSets'
///
/// A VariantSets proxy can be used to as a single interface to query and edit
/// data on multiple UsdVariantSets across disparate prims.
///
/// This should not be confused with a UsdQt_VariantSetProxy which is an
/// interface on top of one specific VariantSet, not all VariantSets for a
/// list of prims.
class UsdQt_VariantSetsProxy : public UsdQt_ProxyBase {
private:
    std::vector<UsdPrim> _prims;
    explicit UsdQt_VariantSetsProxy(
        const std::vector<UsdPrim>& prims);

public:
    static UsdQt_VariantSetsProxyRefPtr New(
        const std::vector<UsdPrim>& prims);

    /// \brief Return the number of VariantSets this proxy refers to.
    size_t GetSize() const { return _prims.size(); }

    /// \brief Return the number of VariantSets this proxy refers to.
    std::vector<std::string> GetNames() const;

    /// \brief Get the intersection of variant set names for all members of this
    /// proxy.
    ///
    /// Returns true all UsdVarianSets queries were successful.
    bool GetNames(std::vector<std::string>* names) const;

    /// \brief Append a new variant set for all members of this proxy
    void AppendVariantSet(const std::string& name);

    /// \brief Create a new proxy for the 'name' variant set for all VariantSets
    ///
    /// If all prims don't have a variant set 'name', no proxy is created and
    /// NULL is returend.
    UsdQt_VariantSetProxyRefPtr CreateVariantSetProxy(const std::string& name);
};


/// \class UsdQt_VariantSetProxy
/// \brief Proxy interface for an ordered list of 'UsdVariantSet' objects
///
/// A VariantSet proxy can be used to as a single interface to query and edit
/// data on multiple UsdVariantSet objects across disparate prims.
///
/// This should not be confused with a UsdQt_VariantSetsProxy which is an
/// interface on top of all of the VariantSets of a list of prims, not one
/// specific VariantSet.
class UsdQt_VariantSetProxy : public UsdQt_ProxyBase {
private:
    std::vector<UsdVariantSet> _variantSets;
    explicit UsdQt_VariantSetProxy(
        const std::vector<UsdVariantSet>& variantSet);

public:
    static UsdQt_VariantSetProxyRefPtr New(
        const std::vector<UsdVariantSet>& variantSets);

    /// \brief Return the number of VariantSet objects this proxy refers to.
    size_t GetSize() const { return _variantSets.size(); }

    /// \brief Get the name that all VariantSet objects for this proxy share
    ///
    /// If the name for all VariantSet objects is not equal, an empty string is
    /// returned.
    std::string GetName() const;

    /// \brief Get the intersection of all variant names for all sets for this
    /// proxy
    std::vector<std::string> GetVariantNames() const;

    /// \brief Get a shared variant selection string for all sets for this proxy
    ///
    /// If all variant selections are not the same, the empty string is
    /// returned.
    std::string GetVariantSelection() const;

    /// \brief Set the variant selection string for all sets for this proxy
    ///
    /// Returns true if all Variant selections were successful.
    bool SetVariantSelection(const std::string& variant);

    /// \brief Clear the variant selection string for all sets for this proxy
    ///
    /// Returns true if all clears were successful.
    bool ClearVariantSelection();

    /// \brief Append a new variant to all set objects for this proxy
    bool AppendVariant (const std::string &variantName);
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif