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

#include "undoBlock.h"

#include "undoRouter.h"
#include "debugCodes.h"

PXR_NAMESPACE_OPEN_SCOPE

void UsdQtUndoBlock::_Initialize(){
    UsdQtUndoRouter& router = UsdQtUndoRouter::Get();
    TF_VERIFY(router._depth >= 0);
    TF_DEBUG(USDQT_DEBUG_UNDOSTACK).Msg(
        "--Opening undo block inverse at depth '%i'.\n", router._depth);
    if (router._depth == 0) {
        if (router._inversion._GetSize() != 0) {
            TF_CODING_ERROR(
                "Opening fragmented undo block. This may be because of an undo "
                "command running inside of an edit block.");
        }
    }
    router._depth++;    
}

UsdQtUndoBlock::UsdQtUndoBlock() {
    _Initialize();
}

UsdQtUndoBlock::~UsdQtUndoBlock() {
    UsdQtUndoRouter& router = UsdQtUndoRouter::Get();
    router._depth--;
    TF_VERIFY(router._depth >= 0);
    if (router._depth == 0) {
        if (router._inversion._GetSize() < 1) {
            TF_DEBUG(USDQT_DEBUG_UNDOSTACK)
                .Msg("Skipping sending notice for empty undo block.\n");
        } else {
            UsdQt::UndoStackNotice().Send();
            TF_DEBUG(USDQT_DEBUG_UNDOSTACK).Msg("Undo Notice Sent.\n");
            if (router._inversion._GetSize() > 0){
                TF_CODING_ERROR("All edits have not been adopted. Undo stack may be incomplete.");
                router._inversion._Clear();
            }
        }
    }
    TF_DEBUG(USDQT_DEBUG_UNDOSTACK).Msg(
        "--Closed undo block inverse at depth '%i'.\n", router._depth);
}

PXR_NAMESPACE_CLOSE_SCOPE