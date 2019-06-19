//
// Copyright 2016 Pixar
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

#include <iostream>
#include "pxr/base/tf/stringUtils.h"

#include "debugCodes.h"
#include "hierarchyCache.h"

PXR_NAMESPACE_OPEN_SCOPE

typedef TfWeakPtr<UsdQt_HierarchyCache::Proxy> ProxyPtr;
typedef TfRefPtr<UsdQt_HierarchyCache::Proxy> ProxyRefPtr;

UsdQt_HierarchyCache::UsdQt_HierarchyCache(
    const UsdPrim& root, const Usd_PrimFlagsPredicate& predicate)
    : _predicate(predicate) {
    _RegisterPrim(root);
    _root = _pathToProxy[root.GetPath()];
    _invalidPrim = UsdQt_HierarchyCache::Proxy::New(UsdPrim());
    // TfDebug::Enable(USDQT_DEBUG_HIERARCHYCACHE);
}

void UsdQt_HierarchyCache::_RegisterPrim(const UsdPrim& prim) {
    SdfPath path = prim.GetPath();
    if (_pathToProxy.count(path) < 1) {
        _pathToProxy[path] = UsdQt_HierarchyCache::Proxy::New(prim);
        _pathToProxy[path]->_RefreshChildren(_predicate);
    }
}

size_t UsdQt_HierarchyCache::GetChildCount(ProxyPtr prim) const {
    if (!prim) {
        TF_CODING_ERROR("Attempting to query child count for invalid prim.");
        return 0;
    }
    return prim->_GetChildren().size();
}

ProxyRefPtr UsdQt_HierarchyCache::GetChild(ProxyPtr prim, size_t index) {
    if (!prim) {
        TF_CODING_ERROR("Attempting to query child for invalid prim.");
        return _invalidPrim;
    }
    if (index >= prim->_GetChildren().size()){
        TF_CODING_ERROR("Index '%zu' exceeds number of children '%zu'", index, prim->_GetChildren().size());
        return _invalidPrim;
    }
    SdfPath childPath = prim->_GetChildren()[index];
    const auto& ptIterator = _pathToProxy.find(childPath);
    if (ptIterator != _pathToProxy.end()) return ptIterator->second;

    UsdPrim child = prim->GetPrim().GetChild(TfToken(childPath.GetName()));
    _RegisterPrim(child);
    const auto& ptIterator2 = _pathToProxy.find(childPath);
    if (ptIterator2 == _pathToProxy.end()) {
        TF_CODING_ERROR("Registration must have failed during GetChild");
        return _invalidPrim;
    }
    return ptIterator2->second;
}

UsdQt_HierarchyCache::Proxy::Proxy(const UsdPrim& prim) : _prim(prim) {}

ProxyRefPtr UsdQt_HierarchyCache::Proxy::New(const UsdPrim& prim) {
    return TfCreateRefPtr(new Proxy(prim));
}

void UsdQt_HierarchyCache::Proxy::_RefreshChildren(
    Usd_PrimFlagsPredicate predicate) {
    _children.clear();
    if (_prim) {
        for (const auto& child : _prim.GetFilteredChildren(predicate)) {
            _children.push_back(child.GetPath());
        }
    }
}
const SdfPathVector& UsdQt_HierarchyCache::Proxy::_GetChildren() {
    return _children;
}

UsdPrim UsdQt_HierarchyCache::Proxy::GetPrim() { return _prim; }

ProxyRefPtr UsdQt_HierarchyCache::GetParent(ProxyPtr proxy) const {
    if (!proxy) {
        TF_CODING_ERROR("Attempting to query parent for invalid proxy.");
        return NULL;
    }
    UsdPrim prim = proxy->GetPrim();

    // NOTE.  It's important at this point that we deal with exclusively
    // paths as prims may start to expire during resync notices.
    SdfPath path = prim.GetPath();
    SdfPath parentPath = path.GetParentPath();

    const auto& ptIterator = _pathToProxy.find(parentPath);
    if (ptIterator == _pathToProxy.end()) {
        TF_CODING_ERROR("Cannot find registered parent. %s",
                        prim.GetPath().GetText());
        return _invalidPrim;
    }
    return ptIterator->second;
}

bool UsdQt_HierarchyCache::IsRoot(TfWeakPtr<Proxy> root) const {
    if (!root) {
        return false;
    }
    return _root->GetPrim() == root->GetPrim();
}

size_t UsdQt_HierarchyCache::GetRow(ProxyPtr proxy) const {
    if (IsRoot(proxy)) {
        return 0;
    }

    if (!proxy) {
        TF_CODING_ERROR("Attempting to query row for invalid proxy.");
        return 0;
    }

    // NOTE.  It's important at this point that we deal with exclusively
    // paths as prims may start to expire during resync notices.
    SdfPath parentPath = proxy->GetPrim().GetPath().GetParentPath();

    const auto& parentIt = _pathToProxy.find(parentPath);
    if (parentIt == _pathToProxy.end()) {
        TF_CODING_ERROR("Could not find parent during row query.");
        return 0;
    }

    ProxyPtr parent = parentIt->second;
    UsdPrim prim = proxy->GetPrim();
    const auto& rowIterator =
        std::find(parent->_GetChildren().begin(), parent->_GetChildren().end(),
                  prim.GetPath());

    if (rowIterator == parent->_GetChildren().end()) {
        TF_CODING_ERROR("Cannot find child '%s' in parent '%s'.",
                        prim.GetPath().GetText(),
                        parent->GetPrim().GetPath().GetText());
        return 0;
    }

    return rowIterator - parent->_GetChildren().begin();
}

void UsdQt_HierarchyCache::_DeleteSubtree(const SdfPath& path) {
    if (_pathToProxy.count(path) > 0) {
        TF_DEBUG(USDQT_DEBUG_HIERARCHYCACHE)
            .Msg("Deleting instantiated path: '%s'\n", path.GetText());
        _pathToProxy.erase(path);
    } else {
        TF_DEBUG(USDQT_DEBUG_HIERARCHYCACHE).Msg(
            "Skipping deletion of uninstantiated path: '%s'\n", path.GetText());
    }
}
void UsdQt_HierarchyCache::_InvalidateSubtree(const SdfPath& path) {
    if (_pathToProxy.count(path) > 0) {
        TfWeakPtr<Proxy> proxy = _pathToProxy[path];
        UsdPrim prim = proxy->GetPrim();
        if (prim.IsValid() && _predicate(prim)) {
            TF_DEBUG(USDQT_DEBUG_HIERARCHYCACHE)
                .Msg("Keeping '%s' during invalidation.\n", path.GetText());
            for (const auto& childPath : proxy->_GetChildren()) {
                _InvalidateSubtree(childPath);
            }
            TF_DEBUG(USDQT_DEBUG_HIERARCHYCACHE).Msg(
                "Original size: %zu children.\n", proxy->_GetChildren().size());
            proxy->_RefreshChildren(_predicate);
            TF_DEBUG(USDQT_DEBUG_HIERARCHYCACHE)
                .Msg("New size: %zu children.\n", proxy->_GetChildren().size());
        } else {
            TF_DEBUG(USDQT_DEBUG_HIERARCHYCACHE)
                .Msg("Rejecting '%s' during invalidation.\n", path.GetText());
            _DeleteSubtree(path);
        }
    } else {
        TF_DEBUG(USDQT_DEBUG_HIERARCHYCACHE)
            .Msg("Skipping invalidation of uninstantiated path '%s'\n",
                 path.GetText());
    }
}

void UsdQt_HierarchyCache::ResyncSubtrees(const std::vector<SdfPath>& paths) {
    /// TODO: Is there a way to optimize the paths that need to be traversed
    /// if there are redundancies? (say, /World/foo and /World/foo/bar)

    /// Uniquify the list of parents.
    SdfPathSet uniqueParents;
    for (const auto& path : paths) uniqueParents.insert(path.GetParentPath());

    // Update the list of children per unique parent.
    for (auto parentPath : uniqueParents) {
        const auto& proxyIt = _pathToProxy.find(parentPath);
        if (proxyIt != _pathToProxy.end()) {
            TF_DEBUG(USDQT_DEBUG_HIERARCHYCACHE).Msg(
                "Updating children of parent: '%s'\n", parentPath.GetText());

            ProxyPtr proxy = proxyIt->second;
            SdfPathSet originalChildren(proxy->_GetChildren().begin(),
                                        proxy->_GetChildren().end());
            proxy->_RefreshChildren(_predicate);
            SdfPathSet newChildren(proxy->_GetChildren().begin(),
                                   proxy->_GetChildren().end());

            SdfPathSet allChildren;
            std::set_union(originalChildren.begin(), originalChildren.end(),
                           newChildren.begin(), newChildren.end(),
                           std::inserter(allChildren, allChildren.end()));

            for (const auto& child : allChildren) {
                _InvalidateSubtree(child);
            }
        }
    }
}

void UsdQt_HierarchyCache::DebugFullIndex() {
    for (const auto& it : _pathToProxy) {
        std::cout << " [path]: " << it.first
                  << " [prim valid]: " << it.second->GetPrim().IsValid()
                  << " [child count]: " << it.second->_GetChildren().size()
                  << std::endl;
    }
  std::cout << "Root: " << _root->GetPrim().GetPrimPath() << std::endl;
}

PXR_NAMESPACE_CLOSE_SCOPE
