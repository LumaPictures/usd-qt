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

#ifndef USDQT_PRIMFILTERCACHE_H
#define USDQT_PRIMFILTERCACHE_H

#include <functional>
#include <iostream>
#include <unordered_map>

#include "pxr/pxr.h"
#include "pxr/usd/usd/primFlags.h"
#include "pxr/usd/usd/prim.h"
#include "pxr/usd/usd/stage.h"
#include "pxr/usd/sdf/path.h"

#include "tbb/concurrent_unordered_map.h"

#include "debugCodes.h"

PXR_NAMESPACE_OPEN_SCOPE

/// \class UsdQtPrimFilterCache
///
/// By default, Qt rejects parents before traversing the children.  The prim
/// filter cache is used to fully traverse the stage in parallel and
/// cache Accept and Reject states for the prim hierarchy based on a filter.
///
/// This filtering allows for a "Intermediate" State which will accept the
/// current location if and only if one ofthe children have been accepted.
///
/// For example, take this hierarchy...
///  /World
///     /sets
///     /crowds
///     /fx
/// If I were try and match prims whose path contains "crowds", Qt by default
/// would not know whether or not to accept or reject '/World'.  The filter
/// cache allows a user to specify "Intermediate" as the state for '/World' to
/// defer Acceptance or Rejection until after its children have been processed.
class UsdQtPrimFilterCache {

public:
    enum State {
        Accept,        // Accept the current location
        Intermediate,  // Accept the current location if and only if one of the
                       // children have been accepted
        Reject,        // Reject the current location
        Untraversed    // Default value
    };

private:
    tbb::concurrent_unordered_map<std::string, State> _stateMap;

public:
    UsdQtPrimFilterCache();

    /// \brief Apply a string match against the name of root and its descendents
    ///
    /// The prim will match the substring if the prim's name contains the
    /// substring.
    void ApplyPathContainsFilter(const UsdPrim& root,
                                 const std::string& substring,
                                 Usd_PrimFlagsPredicate predicate =
                                     UsdPrimDefaultPredicate);

    /// \brief Apply a custom filter to root and its descendents
    void ApplyFilter(const UsdPrim& root,
                     const std::function<State(const UsdPrim&)>& filter,
                     Usd_PrimFlagsPredicate predicate =
                         UsdPrimDefaultPredicate);

    /// \brief Retrieve the stored Acceptance/Rejection state for a path
    ///
    /// If a path has not been found, returns Untraversed.  This implies a
    /// coding error that's allowed the cache to become out of sync.
    ///
    /// This should never return Intermediate to a client unless it's accessing
    /// the cache in a thread-unsafe matter.
    State GetState(const SdfPath& path);

    void PrintDebugString() const {
        for (auto item : _stateMap) {
            std::cout << item.first << " " << item.second << std::endl;
        }
    }

private:
    State _RunFilter(UsdPrim prim,
                     const std::function<State(const UsdPrim&)>& filter,
                     Usd_PrimFlagsPredicate predicate);
};

/// \class UsdQtPrimFilterPathContains
/// Function object which checks to see if the prim's name contains the
/// substring.
///
class UsdQtPrimFilterPathContains {
private:
    std::string _substring;

public:
    explicit UsdQtPrimFilterPathContains(const std::string& substring)
        : _substring(substring) {}

    UsdQtPrimFilterCache::State operator()(const UsdPrim& prim);
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif