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

#ifndef USDQT_PRIMIDTABLE_H
#define USDQT_PRIMIDTABLE_H

#include <unordered_map>
#include <vector>
#include <limits>

#include "pxr/usd/sdf/path.h"
#include "pxr/usd/sdf/pathTable.h"
#include "pxr/usd/usd/prim.h"
#include "pxr/usd/usd/primFlags.h"
#include "pxr/usd/usd/stage.h"

typedef uint32_t UsdQt_InternalId;

/// \class UsdQt_PrimTreeIdTable
///
/// The PrimTreeIdTable is an internal class to UsdQt and provides a mapping
/// from SdfPaths to unique integer ids that can be used as the internalId of a
/// QModelIndex.  We provide this class so that the hierarchy can be quickly
/// indexed and traversed in C++ without mandating that clients link against
/// the Qt library.  This class should also be compatable with a variety of
/// flavors of Qt bindings and versions.
class UsdQt_PrimIdTable {
private:
    struct _ItemInfo {
        // The path represented by the item id.
        SdfPath path;
        std::vector<SdfPath> children;
    };

    UsdStagePtr _stage;
    Usd_PrimFlagsPredicate _predicate;
    SdfPath _root;

    UsdQt_InternalId _nextAvailableId;
    UsdQt_InternalId _maxId;

    // XXX: Remove mutable.  operator[] is only implemented for references, not
    // const references.
    SdfPathTable<UsdQt_InternalId> _pathToId;
    std::map<UsdQt_InternalId, _ItemInfo> _idToItem;

    void _RegisterPrim(const UsdPrim& prim);
    void _InvalidateSubtree(const SdfPath& path);
    void _DeleteSubtree(const SdfPath& prim);

public:
    /// Given a pointer to a stage, a root prim, and a predicate, construct
    /// the table.
    ///
    /// The predicate and root prim should be as accepting as possible, and
    /// a QSortFilterProxyModel used to dynamically filter the view.
    /// The root should almost always be the stage's pseudo root.
    /// The predicate should almost always be a tautology.  The predicate and
    /// root allow you to optmize traversal if, for example, you know that you
    /// will only need to ever browse a specific scope (say Materials or Looks)
    /// or know that you never want to browse abstract or absent prims.
    explicit UsdQt_PrimIdTable(
        const UsdStagePtr& stage, const UsdPrim& root,
        const Usd_PrimFlagsPredicate& predicate = UsdPrimDefaultPredicate,
        UsdQt_InternalId maxId = std::numeric_limits<UsdQt_InternalId>::max());

    /// \brief Return the predicate used to filter
    ///
    /// The predicate cannot be changed after instantiation of the index.
    Usd_PrimFlagsPredicate GetPredicate() const { return _predicate; }

    /// \brief Lookup the QModelIndex internal id for the path
    UsdQt_InternalId GetIdFromPath(const SdfPath& path) const;

    /// \brief Lookup the path for the QModelIndex internal id
    SdfPath GetPathFromId(UsdQt_InternalId id) const;

    /// \brief Checks to see if the path is stored in the table
    bool ContainsPath(const SdfPath& path) const;

    /// \brief Checks to see if the id is stored in the table
    ///
    /// This is often used to check to see if the id is stale.
    /// That is to say, Qt is holding onto the id, but this table had been told
    /// to remove it.
    bool ContainsId(UsdQt_InternalId id) const {
        return _idToItem.count(id) == 0;
    }

    /// \brief Check if the id maps to the root of the
    bool IsRoot(UsdQt_InternalId id) const;

    /// \brief Return the path of the root of the table
    SdfPath GetRootPath() const { return _root; }

    /// \brief Return the id of the parent of the prim mapped to 'childId'
    UsdQt_InternalId GetParentId(UsdQt_InternalId childId) const;

    /// \brief Return the index of the prim in the list of its parent's children
    size_t GetRow(UsdQt_InternalId id) const;

    /// \brief Registers the 'index'th child of a prim mapped to 'id'
    ///
    /// When a prim is registered, we look ahead and read the paths of all
    /// that prim's children, but don't register the children internally.
    /// This function will register children on demand whenever the
    /// QAbstractItemModel requests it.
    ///
    /// It's a valid operation to register the same child multiple times, but
    /// a new id will not be assigned.
    bool RegisterChild(UsdQt_InternalId id, size_t index);

    /// \brief Return the number of children for the prim mapped to 'id'
    size_t GetChildCount(UsdQt_InternalId id) const;

    /// \brief Return the path of the 'index'th child of the prim mapped to 'id'
    SdfPath GetChildPath(UsdQt_InternalId id, size_t index) const;

    /// \brief Return the last id assigned.
    UsdQt_InternalId GetLastId() const { return _nextAvailableId - 1; }

    /// \brief Refresh all the ids for the input paths and their descendants
    ///
    /// Resyncing is terminology from the UsdObjectChanged notice.  Resyncing
    /// may imply a variety of things, addition, removal, variant change, etc.
    /// which is why we have to potentially touch every descendent of the
    /// input paths
    void ResyncSubtrees(const std::vector<SdfPath>& paths);

    void PrintSubtreeIndex(const SdfPath& path);
    void PrintFullIndex();
};

#endif
