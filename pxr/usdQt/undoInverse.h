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

#ifndef USDQT_UNDOINVERSE_H
#define USDQT_UNDOINVERSE_H

#include <functional>
#include <vector>

#include "pxr/pxr.h"
#include "pxr/usd/sdf/layer.h"
#include "pxr/base/tf/weakPtr.h"
#include "pxr/base/tf/refPtr.h"
#include "pxr/base/tf/declarePtrs.h"

PXR_NAMESPACE_OPEN_SCOPE

class UsdQtUndoRouter;

/// \class UsdQtUndoInverse
/// 
/// An UsdUndoInverse is a list of invertible edits to one or more SdfLayers 
/// which MAY span multiple stages.
/// 
/// It may contain more than one edit.  When an edit is inverted, say by an undo 
/// operation, it automatically converts itself into a redo operation by
/// tracking edits in the UndoRouter which spawned it.
///
/// This is the object you should store in your application's native undo stack.
/// The implementation of undo and redo should be the same, simply calling
/// inverse.Invert().
///

class UsdQtUndoInverse {
private:
    std::string _name;
    std::vector<std::function<bool()>> _inversion;
    void _Invert();

    void _Append(std::function<bool()>);
    void _Clear();
    size_t _GetSize() { return _inversion.size(); }
    void _Adopt(const UsdQtUndoInverse& inversion);
    explicit UsdQtUndoInverse(UsdQtUndoRouter& router);
    
public:
    UsdQtUndoInverse(){}
    /// \brief Apply the inverse functions.
    ///
    /// When Invert() has been called, this object now stores the Inverse of
    /// the Inverse.  Calling Invert() twice in a row should result in the same
    /// state.
    ///
    /// WARNING: This is not reentrant.  When Invert is called, no other threads
    /// may engage in edits that affect the router.  If this warning is ignored, 
    /// inverses may get incorrectly routed.
    void Invert();
    friend class UsdQtUndoRouter;
    friend class UsdQtUndoBlock;
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif