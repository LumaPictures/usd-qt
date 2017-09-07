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

#ifndef USDQT_UNDOBLOCK_H
#define USDQT_UNDOBLOCK_H

#include "pxr/pxr.h"
#include "pxr/usd/sdf/layer.h"
#include "pxr/base/tf/weakPtr.h"
#include "pxr/base/tf/refPtr.h"
#include "pxr/base/tf/declarePtrs.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(UsdQtUndoRouter);

/// \class UsdQtUndoBlock
///
/// Similar to an SdfChangeBlock, this will collect multiple edits into a single
/// undo operation.  
///
/// Because edit tracking is done at the Sdf level, it's important to
/// aggressively use UndoBlocks even around single Usd calls.  One Usd call
/// may map to multiple Sdf calls, each spawning their own unique inverse.
///
/// Future refactoring may try to address and smooth over this quirk.
///
/// Sample Python Usage:
///
/// with UsdQt.UndoBlock():
///    attribute1.Set(5)
///    attribute2.Set(6)
///
class UsdQtUndoBlock {
private:
    void _Initialize();

public:
    explicit UsdQtUndoBlock();
    ~UsdQtUndoBlock();
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif