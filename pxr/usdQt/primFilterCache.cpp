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

#include "primFilterCache.h"

#include "pxr/base/tf/enum.h"
#include "pxr/base/tf/registryManager.h"

#include "pxr/base/work/loops.h"
#include "tbb/parallel_reduce.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_REGISTRY_FUNCTION(TfEnum) {
    TF_ADD_ENUM_NAME(UsdQtPrimFilterCache::Accept);
    TF_ADD_ENUM_NAME(UsdQtPrimFilterCache::Intermediate);
    TF_ADD_ENUM_NAME(UsdQtPrimFilterCache::Reject);
    TF_ADD_ENUM_NAME(UsdQtPrimFilterCache::Untraversed);
};

UsdQtPrimFilterCache::UsdQtPrimFilterCache() {
    // TfDebug::Enable(USDQT_DEBUG_PRIMFILTERCACHE);
}

void UsdQtPrimFilterCache::ApplyPathContainsFilter(
    const UsdPrim& root, const std::string& substring,
    Usd_PrimFlagsPredicate predicate) {
    ApplyFilter(root, UsdQtPrimFilterPathContains(substring), predicate);
}

UsdQtPrimFilterCache::State UsdQtPrimFilterCache::GetState(
    const SdfPath& path) {
    if (_stateMap.count(path.GetString()) > 0) {
        return _stateMap[path.GetString()];
    }
    return UsdQtPrimFilterCache::Untraversed;
}

UsdQtPrimFilterCache::State UsdQtPrimFilterCache::_RunFilter(
    UsdPrim prim, const std::function<State(const UsdPrim&)>& filter,
    Usd_PrimFlagsPredicate predicate) {

    TF_DEBUG(USDQT_DEBUG_PRIMFILTERCACHE)
        .Msg("Running filter on: '%s'\n", prim.GetPath().GetText());
    State state = filter(prim);

    TF_DEBUG(USDQT_DEBUG_PRIMFILTERCACHE).Msg("State after filter: %s '%s'\n",
                                              TfEnum::GetName(state).c_str(),
                                              prim.GetPath().GetText());

    if (state != UsdQtPrimFilterCache::Reject) {
        TF_DEBUG(USDQT_DEBUG_PRIMFILTERCACHE).Msg(
            "Applying filter to children: '%s'\n", prim.GetPath().GetText());
        auto runFilterPerChild = [this, filter, predicate](
            const UsdPrim& child) { _RunFilter(child, filter, predicate); };
        WorkParallelForEach(prim.GetFilteredChildren(predicate).begin(),
                            prim.GetFilteredChildren(predicate).end(),
                            runFilterPerChild);

        if (state == UsdQtPrimFilterCache::Intermediate) {
            TF_DEBUG(USDQT_DEBUG_PRIMFILTERCACHE)
                .Msg("Checking filter for children: '%s'\n",
                     prim.GetPath().GetText());

            for (auto child : prim.GetFilteredChildren(predicate)) {
                if (_stateMap[child.GetPath().GetString()] ==
                    UsdQtPrimFilterCache::Accept) {
                    TF_DEBUG(USDQT_DEBUG_PRIMFILTERCACHE).Msg(
                        "Converting Intermediate to Accept because of child: "
                        "'%s', '%s'\n",
                        child.GetPath().GetText(), prim.GetPath().GetText());
                    state = UsdQtPrimFilterCache::Accept;
                    break;
                }
            }
            if (state != UsdQtPrimFilterCache::Accept) {
                TF_DEBUG(USDQT_DEBUG_PRIMFILTERCACHE)
                    .Msg("Converting Intermediate to Reject: '%s'\n",
                         prim.GetPath().GetText());
                state = UsdQtPrimFilterCache::Reject;
            }
        }
    }

    // auto getStatePerChild = [this](
    //     tbb::blocked_range<const UsdPrimSiblingIterator&> children,
    //     State state) {
    //     if (state == UsdQtPrimFilterCache::Accept) {
    //         return UsdQtPrimFilterCache::Accept;
    //     }
    //     if (state == UsdQtPrimFilterCache::Intermediate) {
    //         for (auto child : children) {
    //             if (_stateMap[child.GetPath().GetString()] ==
    //                 UsdQtPrimFilterCache::Accept)
    //                 return UsdQtPrimFilterCache::Accept;
    //         }
    //     }
    //     return UsdQtPrimFilterCache::Intermediate;
    // };
    // auto joinState = [this](State state1, State state2) {
    //     if (state1 == UsdQtPrimFilterCache::Accept or state2 ==
    //         UsdQtPrimFilterCache::Accept)
    //         return UsdQtPrimFilterCache::Accept;
    //     return UsdQtPrimFilterCache::Intermediate;
    // };
    // tbb::parallel_reduce(prim.GetFilteredChildren(predicate).begin(),
    //                      prim.GetFilteredChildren(predicate).end(),
    //                      UsdQtPrimFilterCache::Intermediate,
    // getStatePerChild,
    //                      joinState);

    _stateMap[prim.GetPath().GetString()] = state;
    return state;
}

void UsdQtPrimFilterCache::ApplyFilter(
    const UsdPrim& root, const std::function<State(const UsdPrim&)>& filter,
    Usd_PrimFlagsPredicate predicate) {
    _stateMap.clear();
    _RunFilter(root, filter, predicate);
}

UsdQtPrimFilterCache::State UsdQtPrimFilterPathContains::operator()(
    const UsdPrim& prim) {
    SdfPath path = prim.GetPath();
    if (TfStringContains(TfStringToLower(path.GetName()),
                         TfStringToLower(_substring)))
        return UsdQtPrimFilterCache::Accept;

    if (!prim.GetChildren().empty())
        return UsdQtPrimFilterCache::Intermediate;
    return UsdQtPrimFilterCache::Reject;
}

PXR_NAMESPACE_CLOSE_SCOPE
