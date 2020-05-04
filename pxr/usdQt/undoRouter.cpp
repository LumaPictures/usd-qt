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

#include "undoRouter.h"

#include "pxr/base/tf/instantiateSingleton.h"
#include "pxr/base/tf/refPtr.h"

#include <boost/range/adaptor/sliced.hpp>

#include "debugCodes.h"
#include "undoBlock.h"
#include "undoStateDelegate.h"

using BOOST_NS::adaptors::slice;

PXR_NAMESPACE_OPEN_SCOPE

TF_REGISTRY_FUNCTION(TfType) {
    TfType::Define<UsdQt::UndoStackNotice, TfType::Bases<TfNotice> >();
}

TF_INSTANTIATE_SINGLETON(UsdQtUndoRouter);

namespace UsdQt {
UndoStackNotice::UndoStackNotice() {}
}

UsdQtUndoRouter::UsdQtUndoRouter() {
    // TfDebug::Enable(USDQT_DEBUG_UNDOSTACK);
}

bool UsdQtUndoRouter::TrackLayer(const SdfLayerHandle& layer) {
    layer->SetStateDelegate(UsdQt_UndoStateDelegate::New());
    return true;
}

void UsdQtUndoRouter::_AddInverse(std::function<bool()> inverse) {
    UsdQtUndoBlock undoBlock;
    _inversion._Append(inverse);
}

UsdQtUndoRouter& UsdQtUndoRouter::Get() {
    return TfSingleton<UsdQtUndoRouter>::GetInstance();
}

bool UsdQtUndoRouter::TransferEdits(UsdQtUndoInverse* inverse){
    inverse->_Adopt(Get()._inversion);
    Get()._inversion._Clear();
    return true;
}

void UsdQtUndoRouter::_Mute(){
    Get()._muteDepth++;
}

void UsdQtUndoRouter::_Unmute(){
    Get()._muteDepth--;
    if (Get()._muteDepth < 0){
        TF_CODING_ERROR("Mute depth error.");
    }
}

bool UsdQtUndoRouter::IsMuted(){
    return Get()._muteDepth > 0;
}

PXR_NAMESPACE_CLOSE_SCOPE
