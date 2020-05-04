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

#ifndef USDQT_UNDOADAPTERBASE_H
#define USDQT_UNDOADAPTERBASE_H

#include <boost/noncopyable.hpp>

#include "pxr/pxr.h"
#include "pxr/base/tf/declarePtrs.h"
#include "pxr/base/tf/refPtr.h"
#include "pxr/base/tf/singleton.h"
#include "pxr/base/tf/weakPtr.h"
#include "pxr/usd/sdf/layer.h"
#include "pxr/usd/usd/stage.h"

#include "undoInverse.h"

PXR_NAMESPACE_OPEN_SCOPE

/// \class UsdQtUndoRouter
///
/// Class used to track edits to one or more SdfLayers.  This is the primary
/// class in UsdQt's undo adapter.  The UndoRouter attaches itself to track
/// edits
/// to a layer by spawning a UsdQt_UndoLayerStateDelegate.  It may batch
/// multiple edits by attaching a UsdQtUndoBlock to it.  Once the last block has
/// been closed, a UsdQt::UndoStackNotice is emitted.  The application's native
/// undo queue system now knows it's safe to adopt the edits tracked by the
/// router into a local UsdQtUndoInverse object.  When undo is called, this
/// object can invert all the edits it represents and transforms itself into
/// a redo.
///
/// The UndoRouter is the linchpin and it's important to maintain its lifetime
/// as long as there is an UndoBlock, UndoInverse, or UndoLayerStateDelegate
/// that is expecting to forward or receive information from it.
///
/// Here is a quick breakdown of the chain of triggers.
/// Usd Edit => Sdf Edit => Delegate => Router => Notice => Native Undo Listener
///
/// Usage:
/// # setup
/// UsdQt.UndoRouter.TrackLayer(stage.GetRootLayer())
/// # usage
/// prim = stage.GetPrimAtPath('/World')
/// with UsdQt.UndoBlock():
///    prim.GetAttribute('hello').Set(True)
///
class UsdQtUndoRouter : BOOST_NS::noncopyable {
private:
    int _depth = 0;
    UsdQtUndoInverse _inversion;

    void _AddInverse(std::function<bool()> inverse);

    UsdQtUndoRouter();

    int _muteDepth = 0;

    static UsdQtUndoRouter& Get();

    static void _Mute();
    static void _Unmute();
public:

    static bool TrackLayer(const SdfLayerHandle& layer);
    static bool TransferEdits(UsdQtUndoInverse* inverse);
    static bool IsMuted();

    friend class UsdQtUndoBlock;
    friend class UsdQtUndoInverse;
    friend class UsdQt_UndoStateDelegate;
    friend class TfSingleton<UsdQtUndoRouter>;
};

namespace UsdQt {

/// \class UndoStackNotice
///
/// When an undoable change has been made, and all open UndoBlocks have been
/// freed, this notice is emitted.  The listener of this notice should adopt the
/// edits tracked by the router and place the edits into the application's
/// native undo queue.
class UndoStackNotice : public TfNotice {
public:
    explicit UndoStackNotice();
};
}

PXR_NAMESPACE_CLOSE_SCOPE

#endif
