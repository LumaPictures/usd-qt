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
////
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

#include "primIdTable.h"
#include "debug.h"

UsdQt_PrimIdTable::UsdQt_PrimIdTable(const UsdStagePtr& stage,
                                     const UsdPrim& root,
                                     const Usd_PrimFlagsPredicate& predicate,
                                     UsdQt_InternalId maxId)
    : _stage(stage),
      _predicate(predicate),
      _root(root.GetPath()),
      _nextAvailableId(1),
      _maxId(maxId) {
    //    TfDebug::Enable(USDQT_DEBUG_PRIMIDTABLE);

    TF_VERIFY(_maxId > _nextAvailableId);
    _RegisterPrim(root);
}

void UsdQt_PrimIdTable::_RegisterPrim(const UsdPrim& prim) {
    SdfPath path = prim.GetPath();
    TF_VERIFY(_nextAvailableId < _maxId);
    if (_pathToId.count(path) < 1) {
        _pathToId[path] = _nextAvailableId;
        UsdQt_PrimIdTable::_ItemInfo info;
        info.path = path;
        for (auto child : prim.GetFilteredChildren(_predicate))
            info.children.push_back(child.GetPath());

        _idToItem[_nextAvailableId] = info;
        _nextAvailableId++;
    }
}

bool UsdQt_PrimIdTable::IsRoot(UsdQt_InternalId id) const {
    auto itemIterator = _idToItem.find(id);
    return itemIterator != _idToItem.end() &&
           itemIterator->second.path == _root;
}

bool UsdQt_PrimIdTable::ContainsPath(const SdfPath& path) const {
    return _pathToId.count(path) > 0;
}

UsdQt_InternalId UsdQt_PrimIdTable::GetIdFromPath(const SdfPath& path) const {
    auto idIterator = _pathToId.find(path);
    if (idIterator == _pathToId.end()) {
        TF_CODING_ERROR("Cannot find '%s' in PrimIdTable", path.GetText());
        return 0;
    }
    return idIterator->second;
}

SdfPath UsdQt_PrimIdTable::GetPathFromId(UsdQt_InternalId id) const {
    auto itemIterator = _idToItem.find(id);
    if (itemIterator == _idToItem.end()) {
        TF_CODING_ERROR("Cannot find '%u' in PrimIdTable", id);
        return SdfPath();
    }
    return itemIterator->second.path;
}

size_t UsdQt_PrimIdTable::GetChildCount(UsdQt_InternalId id) const {
    auto itemIterator = _idToItem.find(id);
    if (itemIterator == _idToItem.end()) {
        TF_CODING_ERROR("Cannot find '%u' in PrimIdTable", id);
        return 0;
    }
    return itemIterator->second.children.size();
}

SdfPath UsdQt_PrimIdTable::GetChildPath(UsdQt_InternalId id,
                                        size_t index) const {
    auto itemIterator = _idToItem.find(id);
    if (itemIterator == _idToItem.end()) {
        TF_CODING_ERROR("Cannot find '%u' in PrimIdTable", id);
        return SdfPath();
    }

    if (index >= itemIterator->second.children.size()) {
        TF_CODING_ERROR(
            "Index '%zu' exceeds number of children of '%s' in PrimIdTable",
            index, itemIterator->second.path.GetText());
        return SdfPath();
    }
    return itemIterator->second.children[index];
}

UsdQt_InternalId UsdQt_PrimIdTable::GetParentId(UsdQt_InternalId id) const {
    auto itemIterator = _idToItem.find(id);
    if (itemIterator == _idToItem.end()) {
        TF_CODING_ERROR("Cannot find '%u' in PrimIdTable", id);
        return 0;
    }
    const SdfPath& path = itemIterator->second.path;
    if (path == _root) {
        return 0;
    }
    SdfPath parent = path.GetParentPath();
    auto parentIdIterator = _pathToId.find(parent);
    if (parentIdIterator == _pathToId.end()) {
        TF_CODING_ERROR("Cannot find parent '%s' of '%s' in PrimIdTable",
                        parent.GetText(), path.GetText());
        return 0;
    }

    return parentIdIterator->second;
}

size_t UsdQt_PrimIdTable::GetRow(UsdQt_InternalId id) const {
    auto itemIterator = _idToItem.find(id);
    if (itemIterator == _idToItem.end()) {
        TF_CODING_ERROR("Cannot find '%u' in PrimIdTable", id);
        return 0;
    }

    UsdQt_InternalId parentId = GetParentId(id);
    SdfPath path = GetPathFromId(id);
    if (path == _root) {
        return 0;
    }

    auto parentItemIterator = _idToItem.find(parentId);
    if (parentItemIterator == _idToItem.end()) {
        TF_CODING_ERROR("Cannot find parent '%u' of '%u' in PrimIdTable",
                        parentId, id);
        return 0;
    }

    // Run a search to find the index.
    auto rowIterator =
        std::find(parentItemIterator->second.children.begin(),
                  parentItemIterator->second.children.end(), path);

    return rowIterator - parentItemIterator->second.children.begin();
}

bool UsdQt_PrimIdTable::RegisterChild(UsdQt_InternalId id, size_t index) {
    auto itemIterator = _idToItem.find(id);
    if (itemIterator == _idToItem.end()) {
        TF_CODING_ERROR("Cannot find '%u' in PrimIdTable", id);
        return false;
    }
    if (index >= itemIterator->second.children.size()) {
        TF_CODING_ERROR(
            "Index '%zu' exceeds number of children of '%s' in PrimIdTable",
            index, itemIterator->second.path.GetText());
        return false;
    }

    const SdfPath& path = itemIterator->second.children[index];

    if (_pathToId.count(path)) {
        // already registered.
        return true;
    }
    UsdPrim prim = _stage->GetPrimAtPath(path);
    if (not prim) {
        TF_CODING_ERROR("Expected child (%zu) of id (%u) has expired.", index,
                        id);
        return false;
    }
    if (_nextAvailableId >= _maxId) {
        TF_WARN("out of indices.");
        return false;
    }

    _RegisterPrim(prim);
    return true;
}

void UsdQt_PrimIdTable::_DeleteSubtree(const SdfPath& path) {
    if (_pathToId.count(path) > 0) {
        TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE)
            .Msg("Deleting instantiated path: '%s'\n", path.GetText());
        UsdQt_InternalId id = _pathToId[path];
        _pathToId.erase(path);
        for (auto childPath : _idToItem[id].children) {
            _DeleteSubtree(childPath);
        }
        _idToItem.erase(id);
    } else {
        TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE).Msg(
            "Skipping deletion of uninstantiated path: '%s'\n", path.GetText());
    }
}

void UsdQt_PrimIdTable::_InvalidateSubtree(const SdfPath& path) {
    if (_pathToId.count(path) > 0) {
        UsdQt_InternalId id = _pathToId[path];
        UsdPrim prim = _stage->GetPrimAtPath(path);
        if (prim.IsValid() and _predicate(prim)) {
            TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE)
                .Msg("Keeping '%s' during invalidation.\n", path.GetText());
            for (auto childPath : _idToItem[id].children) {
                _InvalidateSubtree(childPath);
            }
            TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE)
                .Msg("Original size: %zu children.\n",
                     _idToItem[id].children.size());
            _idToItem[id].children.clear();
            for (auto child : prim.GetFilteredChildren(_predicate)) {
                _idToItem[id].children.push_back(child.GetPath());
            }
            TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE).Msg(
                "New size: %zu children.\n", _idToItem[id].children.size());
        } else {
            TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE)
                .Msg("Rejecting '%s' during invalidation.\n", path.GetText());
            _DeleteSubtree(path);
        }
    } else {
        TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE)
            .Msg("Skipping invalidation of uninstantiated path '%s'\n",
                 path.GetText());
    }
}

void UsdQt_PrimIdTable::ResyncSubtrees(const std::vector<SdfPath>& paths) {
    /// TODO: Is there a way to optimize the paths that need to be traversed
    /// if there are redundancies? (say, /World/foo and /World/foo/bar)
    std::vector<SdfPath> sortedPaths(paths);
    std::sort(sortedPaths.begin(), sortedPaths.end());

    /// Uniquify the list of parents.
    std::set<SdfPath> uniqueParents;
    for (auto path : sortedPaths) uniqueParents.insert(path.GetParentPath());

    std::set<SdfPath> outOfSyncPaths;

    // Update the list of children per unique parent.
    for (auto parentPath : uniqueParents) {
        TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE)
            .Msg("Updating children of parent: '%s'\n", parentPath.GetText());

        UsdQt_InternalId parentId = GetIdFromPath(parentPath);
        std::vector<SdfPath> sortedOriginalChildren =
            _idToItem[parentId].children;
        std::sort(sortedOriginalChildren.begin(), sortedOriginalChildren.end());

        std::vector<SdfPath> newChildren;

        // Look through the new children to find any paths aren't in the
        // original
        // children and not in sorted paths.  These have gotten out of sync.
        UsdPrim parentPrim = _stage->GetPrimAtPath(parentPath);
        for (auto child : parentPrim.GetFilteredChildren(_predicate)) {
            bool inOriginalChildren = std::binary_search(
                sortedOriginalChildren.begin(), sortedOriginalChildren.end(),
                child.GetPath());
            bool inResyncPaths = std::binary_search(
                sortedPaths.begin(), sortedPaths.end(), child.GetPath());

            if (inOriginalChildren or inResyncPaths) {
                TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE)
                    .Msg("Keeping child: '%s'\n", child.GetPath().GetText());
                newChildren.push_back(child.GetPath());
            } else {
                TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE).Msg(
                    "Out of sync new child: '%s'\n", child.GetPath().GetText());
                outOfSyncPaths.insert(child.GetPath());
            }
        }

        std::vector<SdfPath> sortedNewChildren(newChildren);
        std::sort(sortedNewChildren.begin(), sortedNewChildren.end());
        // Look through the original children to find any paths are missing
        // and not in sorted paths.  These have gotten out of sync, likely
        // because ResyncSubtrees has been called with an incomplete list.
        // This isn't strictly necessary other than for error checking.
        for (auto childPath : sortedOriginalChildren) {
            bool inNewChildren = std::binary_search(
                sortedNewChildren.begin(), sortedNewChildren.end(), childPath);
            bool inResyncPaths = std::binary_search(
                sortedPaths.begin(), sortedPaths.end(), childPath);
            if (not inNewChildren and not inResyncPaths) {
                TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE).Msg(
                    "Out of sync original child: '%s'\n", childPath.GetText());
                outOfSyncPaths.insert(childPath);
            }
        }
        // Assign the new children vector to the parent.
        _idToItem[parentId].children = newChildren;
        TF_DEBUG(USDQT_DEBUG_PRIMIDTABLE)
            .Msg("Total children count: '%zu'\n",
                 _idToItem[parentId].children.size());
    }

    if (outOfSyncPaths.size() > 0) {
        TF_CODING_ERROR("Indices may have been lost during index resync.");
    }
    for (auto path : sortedPaths) _InvalidateSubtree(path);
}

void UsdQt_PrimIdTable::PrintFullIndex() {
    std::cout << "Root: " << _root << std::endl;
    for (auto it : _idToItem) {
        std::string pathMapInfo;
        if (_pathToId.count(it.second.path)) {
            if (_pathToId[it.second.path] == it.first) {
                pathMapInfo = "correct";
            } else {
                pathMapInfo = TfStringPrintf("out of sync path map entry: %u",
                                             _pathToId[it.second.path]);
            }
        } else {
            pathMapInfo = "Missing Path Map Entry.";
        }
        std::cout << "[id]: " << it.first << " [path]: " << it.second.path
                  << " [path map]: " << pathMapInfo
                  << " [child count]: " << it.second.children.size()
                  << std::endl;
    }
    for (auto it : _pathToId) {
        if (_idToItem.count(it.second) < 1) {
            std::cout << "Dangling path: " << it.first << std::endl;
        }
    }
}

void UsdQt_PrimIdTable::PrintSubtreeIndex(const SdfPath& path) {
    if (_pathToId.count(path) < 1) {
        std::cout << "(uninstantiated) " << path.GetString() << std::endl;
    } else {
        UsdQt_InternalId id = GetIdFromPath(path);
        std::cout << path << " id: " << id << " row: " << GetRow(id)
                  << std::endl;
        for (auto child : _idToItem[id].children) PrintSubtreeIndex(child);
    }
}
