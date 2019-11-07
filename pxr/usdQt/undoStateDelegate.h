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
#ifndef USDQT_UNDOSTATEDELEGATE_H
#define USDQT_UNDOSTATEDELEGATE_H

#include <functional>

#include "pxr/pxr.h"
#include "pxr/base/tf/declarePtrs.h"

#include "pxr/usd/sdf/layerStateDelegate.h"
#include "pxr/usd/sdf/path.h"

#include "pxr/usd/usd/attribute.h"
#include "pxr/usd/usd/prim.h"
#include "pxr/usd/usd/property.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(UsdQt_UndoStateDelegate);
TF_DECLARE_WEAK_AND_REF_PTRS(UsdQtUndoRouter);  // forward declaration

/// \class UsdQt_UndoStateDelegate
///
/// The layer state delegate is a class that forwards the inverse of a given
/// edit to a UsdQtUndoRouter.  To instantiate this class, create a 
/// UsdQtUndoRouterPtr, and call yourRouter->TrackLayer(yourLayer).
class UsdQt_UndoStateDelegate : public SdfLayerStateDelegateBase {
private:
    SdfLayerHandle _layer;
    bool _dirty;

    static UsdQt_UndoStateDelegateRefPtr New();

    UsdQt_UndoStateDelegate();

    void _RouteInverse(std::function<bool()> inverse);

    virtual bool _IsDirty() override;
    virtual void _MarkCurrentStateAsClean() override;
    virtual void _MarkCurrentStateAsDirty() override;

    bool _InvertSetField(const SdfPath& path, const TfToken& fieldName,
                         const VtValue& inverse);

    bool _InvertSetFieldDictValueByKey(const SdfPath& path,
                                       const TfToken& fieldName,
                                       const TfToken& keyPath,
                                       const VtValue& inverse);
    bool _InvertSetTimeSample(const SdfPath& path, double time,
                              const VtValue& inverse);
    bool _InvertCreateSpec(const SdfPath& path, bool inert);
    bool _InvertDeleteSpec(const SdfPath& path, bool inert,
                           SdfSpecType deletedSpecType,
                           const SdfDataRefPtr& deletedData);
    bool _InvertPushTokenChild(const SdfPath& parentPath,
                               const TfToken& fieldName, const TfToken& value);
    bool _InvertPopTokenChild(const SdfPath& parentPath,
                              const TfToken& fieldName, const TfToken& value);
    bool _InvertPushPathChild(const SdfPath& parentPath,
                              const TfToken& fieldName, const SdfPath& value);
    bool _InvertPopPathChild(const SdfPath& parentPath,
                             const TfToken& fieldName, const SdfPath& value);

    bool _InvertMoveSpec(const SdfPath& oldPath, const SdfPath& newPath);

    void _OnSetLayer(const SdfLayerHandle& layer) override;

    void _OnSetField(const SdfPath& path, const TfToken& fieldName,
                     const VtValue& value) override;
    virtual void _OnSetField(const SdfPath& path,
                             const TfToken& fieldName,
                             const SdfAbstractDataConstValue& value) override;
    void _OnSetFieldImpl(const SdfPath& path,
                         const TfToken& fieldName);

    virtual void _OnSetFieldDictValueByKey(const SdfPath& path,
                                           const TfToken& fieldName,
                                           const TfToken& keyPath,
                                           const VtValue& value) override;
    virtual void _OnSetFieldDictValueByKey(
        const SdfPath& path, const TfToken& fieldName,
        const TfToken& keyPath,
        const SdfAbstractDataConstValue& value) override;
    void _OnSetFieldDictValueByKeyImpl(const SdfPath& path,
                                       const TfToken& fieldName,
                                       const TfToken& keyPath);

    virtual void _OnSetTimeSample(const SdfPath& path, double time,
                                  const VtValue& value) override;

    virtual void _OnSetTimeSample(
        const SdfPath& path, double time,
        const SdfAbstractDataConstValue& value) override;
    void _OnSetTimeSampleImpl(const SdfPath& path, double time);

    virtual void _OnCreateSpec(const SdfPath& path, SdfSpecType specType,
                               bool inert) override;

    virtual void _OnDeleteSpec(const SdfPath& path, bool inert) override;

    virtual void _OnMoveSpec(const SdfPath& oldPath,
                             const SdfPath& newPath) override;
    virtual void _OnPushChild(const SdfPath& parentPath,
                              const TfToken& fieldName,
                              const TfToken& value) override;
    virtual void _OnPushChild(const SdfPath& parentPath,
                              const TfToken& fieldName,
                              const SdfPath& value) override;

    virtual void _OnPopChild(const SdfPath& parentPath,
                             const TfToken& fieldName,
                             const TfToken& oldValue) override;

    virtual void _OnPopChild(const SdfPath& parentPath,
                             const TfToken& fieldName,
                             const SdfPath& oldValue) override;
    friend class UsdQtUndoRouter;
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif
