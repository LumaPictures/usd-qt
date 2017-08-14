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

#ifndef USDQT_HIERARCHYCACHE_H
#define USDQT_HIERARCHYCACHE_H

#include <limits>
#include <unordered_map>
#include <vector>

#include "pxr/base/tf/refPtr.h"
#include "pxr/base/tf/weakPtr.h"
#include "pxr/usd/sdf/path.h"
#include "pxr/usd/sdf/pathTable.h"
#include "pxr/usd/usd/prim.h"
#include "pxr/usd/usd/primFlags.h"
#include "pxr/usd/usd/stage.h"

/// \class UsdQt_HierarchyCache
///
/// The HierarchyCache is an internal class to UsdQt and provides a mapping
/// from SdfPaths to ref counted pointers that can be used with
/// QModelIndexs.  We provide this class so that the hierarchy can be quickly
/// indexed and traversed in C++ without mandating that clients link against
/// the Qt library.  This class should also be compatable with a variety of
/// flavors of Qt bindings and versions.

class UsdQt_HierarchyCache {
public:
    class Proxy : public TfRefBase, public TfWeakBase {
    private:
        UsdPrim _prim;
        SdfPathVector _children;
        explicit Proxy(const UsdPrim& prim);
        static TfRefPtr<Proxy> New(const UsdPrim& prim);

        void _RefreshChildren(Usd_PrimFlagsPredicate predicate);
        const SdfPathVector& _GetChildren();

    public:
        UsdPrim GetPrim();
        friend class UsdQt_HierarchyCache;
    };

private:
    Usd_PrimFlagsPredicate _predicate;
    TfRefPtr<Proxy> _root;
    TfRefPtr<Proxy> _invalidPrim;

    SdfPathTable<TfRefPtr<Proxy>> _pathToProxy;

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
    /// root allow you to optimize traversal if, for example, you know that you
    /// will only need to ever browse a specific scope (say Materials or Looks)
    /// or know that you never want to browse abstract or absent prims.
    explicit UsdQt_HierarchyCache(const UsdPrim& root,
                                  const Usd_PrimFlagsPredicate& predicate =
                                      UsdPrimDefaultPredicate);

    bool IsRoot(TfWeakPtr<Proxy> root) const;
    TfRefPtr<Proxy> GetRoot() const { return _root; }

    /// \brief
    bool ContainsPath(const SdfPath& path) {
        return _pathToProxy.find(path) != _pathToProxy.end();
    }

    /// \brief Return the predicate used to filter
    ///
    /// The predicate cannot be changed after instantiation of the index.
    Usd_PrimFlagsPredicate GetPredicate() const { return _predicate; }

    /// \brief Return the id of the parent of the prim mapped to 'childId'
    TfRefPtr<Proxy> GetParent(TfWeakPtr<Proxy> child) const;

    /// \brief Return the index of the prim in the list of its parent's children
    size_t GetRow(TfWeakPtr<Proxy> child) const;

    /// \brief Return the number of children the prim for the proxy
    size_t GetChildCount(TfWeakPtr<Proxy> prim) const;

    /// \brief Return the proxy of the 'index'th child of the prim for the proxy
    /// This may create the child under the hood.
    TfRefPtr<Proxy> GetChild(TfWeakPtr<Proxy>, size_t index);

    TfRefPtr<Proxy> GetProxy(const SdfPath& path) { return _pathToProxy[path]; }

    /// \brief Refresh all the ids for the input paths and their descendants
    ///
    /// Resyncing is terminology from the UsdObjectChanged notice.  Resyncing
    /// may imply a variety of things, addition, removal, variant change, etc.
    /// which is why we have to potentially touch every descendent of the
    /// input paths
    void ResyncSubtrees(const std::vector<SdfPath>& paths);

    // void PrintSubtreeIndex(const SdfPath& path);
    void DebugFullIndex();
};

#endif
