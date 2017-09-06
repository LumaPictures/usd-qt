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
#include "undoInverse.h"

#include "undoBlock.h"
#include "undoRouter.h"

PXR_NAMESPACE_OPEN_SCOPE

void UsdQtUndoInverse::_Append(std::function<bool()> inverse) {
    _inversion.push_back(inverse);
}

void UsdQtUndoInverse::_Invert() {
    SdfChangeBlock changeBlock;
    for (int i = 0; i < _inversion.size(); i++) {
        _inversion[_inversion.size() - i - 1]();
    }
}

void UsdQtUndoInverse::Invert() {
    UsdQtUndoRouter& router = UsdQtUndoRouter::Get();
    if (router._depth != 0) {
        TF_CODING_ERROR(
            "Inversion during open edit block may result in corrupted undo "
            "stack.");
    }

    // open up an edit change block to capture the inverse of the inversion
    UsdQtUndoBlock editBlock;
    _Invert();
    _Clear();
    // adopt the edits and clear the listeners inversion tracker.
    // when the change block is popped, no notices will be sent
    // TODO: Do we want a more explicit version of this that
    // explicitly marks that we are inverting an undo/redo as
    // opposed to a new edit?
    _Adopt(router._inversion);
    router._inversion._Clear();
}

void UsdQtUndoInverse::_Clear() { _inversion.clear(); }

void UsdQtUndoInverse::_Adopt(const UsdQtUndoInverse& inversion) {
    for (int i = 0; i < inversion._inversion.size(); i++) {
        _inversion.push_back(inversion._inversion[i]);
    }
}

UsdQtUndoInverse::UsdQtUndoInverse(UsdQtUndoRouter& router) {
    _Adopt(router._inversion);
    router._inversion._Clear();
}

PXR_NAMESPACE_CLOSE_SCOPE
