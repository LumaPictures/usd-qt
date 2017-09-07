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

#include "variantSetsProxy.h"

#include <boost/range/adaptor/sliced.hpp>

#include "utils.h"

PXR_NAMESPACE_OPEN_SCOPE

using boost::adaptors::slice;

UsdQt_VariantSetsProxy::UsdQt_VariantSetsProxy(
    const std::vector<UsdPrim>& prims)
    : _prims(prims) {}

UsdQt_VariantSetsProxyRefPtr UsdQt_VariantSetsProxy::New(
    const std::vector<UsdPrim>& prims) {
    return TfCreateRefPtr(new UsdQt_VariantSetsProxy(prims));
}

std::vector<std::string> UsdQt_VariantSetsProxy::GetNames() const {
    std::vector<std::string> names;
    if (!GetNames(&names)) {
        return std::vector<std::string>();
    }
    return names;
}

bool UsdQt_VariantSetsProxy::GetNames(std::vector<std::string>* names) const {
    if (!names) return false;
    if (_prims.size() < 1) {
        return true;
    }
    if (!_prims[0]) {
        names->clear();
	return false;
    }
    std::vector<std::string> sharedNames =
        _prims[0].GetVariantSets().GetNames();
    auto sharedNamesEnd = sharedNames.end();

    for (const auto& prim : slice(_prims, 1, _prims.size())) {
        if (!prim) {
            names->clear();
            return false;
        }
        sharedNamesEnd = remove_if(
            sharedNames.begin(), sharedNamesEnd, [&](const std::string& name) {
                return !prim.GetVariantSets().HasVariantSet(name);
            });
    }
    sharedNames.erase(sharedNamesEnd, sharedNames.end());
    names->assign(sharedNames.begin(), sharedNames.end());
    return true;
}

void UsdQt_VariantSetsProxy::AppendVariantSet(const std::string& name) {
    for (auto& prim : _prims) {
        prim.GetVariantSets().AppendVariantSet(name);
    }
}

UsdQt_VariantSetProxyRefPtr UsdQt_VariantSetsProxy::CreateVariantSetProxy(
    const std::string& name) {
    std::vector<UsdVariantSet> sharedSets;

    for (const auto& prim : _prims) {
        if (!prim.GetVariantSets().HasVariantSet(name)) return NULL;
        sharedSets.push_back(prim.GetVariantSets().GetVariantSet(name));
    }
    return UsdQt_VariantSetProxy::New(sharedSets);
}

UsdQt_VariantSetProxy::UsdQt_VariantSetProxy(
    const std::vector<UsdVariantSet>& variantSets)
    : _variantSets(variantSets) {}

UsdQt_VariantSetProxyRefPtr UsdQt_VariantSetProxy::New(
    const std::vector<UsdVariantSet>& variantSets) {
    return TfCreateRefPtr(new UsdQt_VariantSetProxy(variantSets));
}

std::string UsdQt_VariantSetProxy::GetVariantSelection() const {
    if (_variantSets.size() < 1) {
        return std::string();
    }
    std::string sharedName = _variantSets[0].GetVariantSelection();

    for (const auto& variantSet : slice(_variantSets, 1, _variantSets.size())) {
        if (variantSet.GetVariantSelection() != sharedName) {
            return std::string();
        }
    }

    return sharedName;
}

bool UsdQt_VariantSetProxy::ClearVariantSelection() {
    bool success = true;
    for (auto& variantSet : _variantSets) {
        success &= variantSet.ClearVariantSelection();
    }
    return success;
}

std::vector<std::string> UsdQt_VariantSetProxy::GetVariantNames() const {
    if (_variantSets.size() < 1) {
        return std::vector<std::string>();
    }
    std::vector<std::string> sharedNames = _variantSets[0].GetVariantNames();
    auto sharedNamesEnd = sharedNames.end();
    for (const auto& variantSet : slice(_variantSets, 1, _variantSets.size())) {
        std::vector<std::string> names = variantSet.GetVariantNames();
        sharedNamesEnd = remove_if(
            sharedNames.begin(), sharedNamesEnd, [&](const std::string& name) {
                return UsdQt_ItemNotInVector(names, name);
            });
    }
    sharedNames.erase(sharedNamesEnd, sharedNames.end());
    return sharedNames;
}

std::string UsdQt_VariantSetProxy::GetName() const {
    if (_variantSets.size() < 1) {
        return std::string();
    }
    std::string sharedName = _variantSets[0].GetName();

    for (const auto& variantSet : slice(_variantSets, 1, _variantSets.size())) {
        if (variantSet.GetName() != sharedName) {
            return std::string();
        }
    }
    return sharedName;
}

bool UsdQt_VariantSetProxy::SetVariantSelection(const std::string& variant) {
    bool success = true;
    for (auto& variantSet : _variantSets) {
        success &= variantSet.SetVariantSelection(variant);
    }
    return success;
}

bool UsdQt_VariantSetProxy::AppendVariant(const std::string& variant) {
    bool success = true;
    for (auto& variantSet : _variantSets) {
        success &= variantSet.AppendVariant(variant);
    }
    return success;
}

PXR_NAMESPACE_CLOSE_SCOPE
