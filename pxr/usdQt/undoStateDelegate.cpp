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

#include <functional>

#include "undoStateDelegate.h"

#include "debugCodes.h"
#include "undoRouter.h"

PXR_NAMESPACE_OPEN_SCOPE

UsdQt_UndoStateDelegate::UsdQt_UndoStateDelegate()
    : _dirty(false) {
    //TfDebug::Enable(USDQT_DEBUG_UNDOSTATEDELEGATE);
}

UsdQt_UndoStateDelegateRefPtr UsdQt_UndoStateDelegate::New() {
    return TfCreateRefPtr(new UsdQt_UndoStateDelegate());
}

bool UsdQt_UndoStateDelegate::_IsDirty() { return _dirty; }

void UsdQt_UndoStateDelegate::_MarkCurrentStateAsClean() {
    _dirty = false;
}

void UsdQt_UndoStateDelegate::_MarkCurrentStateAsDirty() { _dirty = true; }

void UsdQt_UndoStateDelegate::_OnSetLayer(const SdfLayerHandle& layer) {
    if (layer)
        _layer = layer;
    else {
        _layer = NULL;
        // is this an error?
    }
}

void UsdQt_UndoStateDelegate::_RouteInverse(
    std::function<bool()> inverse) {
    if (!UsdQtUndoRouter::IsMuted())
        UsdQtUndoRouter::Get()._AddInverse(inverse);
    else{
	TF_WARN("Performance Warning.  Inverse should be muted earlier in stack.");
    }
}

bool UsdQt_UndoStateDelegate::_InvertSetField(const SdfPath& path,
                                                   const TfToken& fieldName,
                                                   const VtValue& inverse) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Inverting Field '%s' for Spec '%s'\n", fieldName.GetText(),
             path.GetText());
    if (!_layer) {
        TF_CODING_ERROR("Cannot invert field for expired layer.");
        return false;
    }
    SetField(SdfAbstractDataSpecId(&path), fieldName, inverse);
    return true;
}

bool UsdQt_UndoStateDelegate::_InvertSetFieldDictValueByKey(
    const SdfPath& path, const TfToken& fieldName, const TfToken& keyPath,
    const VtValue& inverse) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Inverting Field '%s' By Key '%s' for Spec '%s'\n",
             fieldName.GetText(), keyPath.GetText(), path.GetText());
    if (!_layer) {
        TF_CODING_ERROR(
            "Cannot invert field dictionary value for expired layer.");
        return false;
    }
    SetFieldDictValueByKey(SdfAbstractDataSpecId(&path), fieldName, keyPath,
                           inverse);
    return true;
}

bool UsdQt_UndoStateDelegate::_InvertSetTimeSample(
    const SdfPath& path, double time, const VtValue& inverse) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Inverting TimeSample '%f' for Spec '%s'\n", time, path.GetText());
    if (!_layer) {
        TF_CODING_ERROR("Cannot invert time sample for expired layer.");
        return false;
    }
    SetTimeSample(SdfAbstractDataSpecId(&path), time, inverse);
    return true;
}

bool UsdQt_UndoStateDelegate::_InvertCreateSpec(const SdfPath& path,
                                                     bool inert) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Inverting Creation of Spec '%s'\n", path.GetText());
    if (!_layer) {
        TF_CODING_ERROR("Cannot invert spec creation for expired layer.");
        return false;
    }
    DeleteSpec(path, inert);
    return true;
}

/// XXX: This is copied straight from Sd.  Should this be refactored and
/// packaged as a part of Sdf?
static void _CopySpec(const SdfAbstractData& src, SdfAbstractData* dst,
                      const SdfAbstractDataSpecId& specId) {
    dst->CreateSpec(specId, src.GetSpecType(specId));

    std::vector<TfToken> fields = src.List(specId);
    TF_FOR_ALL(i, fields) { dst->Set(specId, *i, src.Get(specId, *i)); }
}

bool UsdQt_UndoStateDelegate::_InvertDeleteSpec(
    const SdfPath& path, bool inert, SdfSpecType deletedSpecType,
    const SdfDataRefPtr& deletedData) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Inverting Deletion of Spec '%s'\n", path.GetText());
    if (!_layer) {
        TF_CODING_ERROR("Cannot invert spec deletion for expired layer.");
        return false;
    }
    SdfChangeBlock changeBlock;

    CreateSpec(path, deletedSpecType, inert);

    struct _SpecCopier : public SdfAbstractDataSpecVisitor {
        explicit _SpecCopier(SdfAbstractData* dst_) : dst(dst_) {}

        virtual bool VisitSpec(const SdfAbstractData& src,
                               const SdfAbstractDataSpecId& specId) {
            _CopySpec(src, dst, specId);
            return true;
        }

        virtual void Done(const SdfAbstractData&) {
            // Do nothing
        }

        SdfAbstractData* const dst;
    };

    _SpecCopier specCopier(boost::get_pointer(_GetLayerData()));
    deletedData->VisitSpecs(&specCopier);
    return true;
}

bool UsdQt_UndoStateDelegate::_InvertMoveSpec(const SdfPath& oldPath,
                                                   const SdfPath& newPath) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Inverting move of '%s' to '%s'\n", oldPath.GetText(),
             newPath.GetText());
    if (!_layer) {
        TF_CODING_ERROR("Cannot invert spec move for expired layer.");
        return false;
    }
    MoveSpec(newPath, oldPath);
    return true;
}

bool UsdQt_UndoStateDelegate::_InvertPushTokenChild(
    const SdfPath& parentPath, const TfToken& fieldName, const TfToken& value) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Inverting push field '%s' of '%s'\n", fieldName.GetText(),
             value.GetText());
    if (!_layer) {
        TF_CODING_ERROR("Cannot invert push child for expired layer.");
        return false;
    }
    PopChild(parentPath, fieldName, value);
    return true;
}
bool UsdQt_UndoStateDelegate::_InvertPopTokenChild(
    const SdfPath& parentPath, const TfToken& fieldName, const TfToken& value) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Inverting pop field '%s' of '%s'\n", fieldName.GetText(),
             value.GetText());
    if (!_layer) {
        TF_CODING_ERROR("Cannot invert pop child for expired layer.");
        return false;
    }
    PushChild(parentPath, fieldName, value);

    return true;
}
bool UsdQt_UndoStateDelegate::_InvertPushPathChild(
    const SdfPath& parentPath, const TfToken& fieldName, const SdfPath& value) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Inverting push field '%s' of '%s'\n", fieldName.GetText(),
             value.GetText());
    if (!_layer) {
        TF_CODING_ERROR("Cannot invert push child for expired layer.");
        return false;
    }
    PopChild(parentPath, fieldName, value);
    return true;
}
bool UsdQt_UndoStateDelegate::_InvertPopPathChild(
    const SdfPath& parentPath, const TfToken& fieldName, const SdfPath& value) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Inverting pop field '%s' of '%s'\n", fieldName.GetText(),
             value.GetText());
    if (!_layer) {
        TF_CODING_ERROR("Cannot invert pop child for expired layer.");
        return false;
    }
    PushChild(parentPath, fieldName, value);
    return true;
}

void UsdQt_UndoStateDelegate::_OnSetFieldImpl(
    const SdfAbstractDataSpecId& id, const TfToken& fieldName) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Setting Field '%s' for Spec '%s'\n", fieldName.GetText(),
             id.GetFullSpecPath().GetText());
    _MarkCurrentStateAsDirty();
    const VtValue inverseValue = _layer->GetField(id, fieldName);
    _RouteInverse(std::bind(&UsdQt_UndoStateDelegate::_InvertSetField,
                            this, id.GetFullSpecPath(), fieldName,
                            inverseValue));
}

void UsdQt_UndoStateDelegate::_OnSetFieldDictValueByKeyImpl(
    const SdfAbstractDataSpecId& id, const TfToken& fieldName,
    const TfToken& keyPath) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Setting Dictionary Field '%s' By Key '%s' for Spec '%s'\n",
             fieldName.GetText(), keyPath.GetText(),
             id.GetFullSpecPath().GetText());
    _MarkCurrentStateAsDirty();
    const VtValue inverseValue =
        _layer->GetFieldDictValueByKey(id, fieldName, keyPath);
    _RouteInverse(std::bind(
        &UsdQt_UndoStateDelegate::_InvertSetFieldDictValueByKey, this,
        id.GetFullSpecPath(), fieldName, keyPath, inverseValue));
}

void UsdQt_UndoStateDelegate::_OnSetTimeSampleImpl(
    const SdfAbstractDataSpecId& id, double time) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Setting Time Sample '%f' for Spec '%s'\n", time,
             id.GetFullSpecPath().GetText());
    _MarkCurrentStateAsDirty();

    if (!_GetLayer()->HasField(id, SdfFieldKeys->TimeSamples)) {
        _RouteInverse(std::bind(&UsdQt_UndoStateDelegate::_InvertSetField,
                                this, id.GetFullSpecPath(),
                                SdfFieldKeys->TimeSamples, VtValue()));
    } else {
        VtValue oldValue;
        _GetLayer()->QueryTimeSample(id, time, &oldValue);
        _RouteInverse(
            std::bind(&UsdQt_UndoStateDelegate::_InvertSetTimeSample, this,
                      id.GetFullSpecPath(), time, oldValue));
    }
}

void UsdQt_UndoStateDelegate::_OnSetField(const SdfAbstractDataSpecId& id,
                                               const TfToken& fieldName,
                                               const VtValue& value) {
    _OnSetFieldImpl(id, fieldName);
}

void UsdQt_UndoStateDelegate::_OnSetField(
    const SdfAbstractDataSpecId& id, const TfToken& fieldName,
    const SdfAbstractDataConstValue& value) {
    _OnSetFieldImpl(id, fieldName);
}

void UsdQt_UndoStateDelegate::_OnSetFieldDictValueByKey(
    const SdfAbstractDataSpecId& id, const TfToken& fieldName,
    const TfToken& keyPath, const VtValue& value) {
    _OnSetFieldDictValueByKeyImpl(id, fieldName, keyPath);
}

void UsdQt_UndoStateDelegate::_OnSetFieldDictValueByKey(
    const SdfAbstractDataSpecId& id, const TfToken& fieldName,
    const TfToken& keyPath, const SdfAbstractDataConstValue& value) {
    _OnSetFieldDictValueByKeyImpl(id, fieldName, keyPath);
}

void UsdQt_UndoStateDelegate::_OnSetTimeSample(
    const SdfAbstractDataSpecId& id, double time, const VtValue& value) {
    _OnSetTimeSampleImpl(id, time);
}

void UsdQt_UndoStateDelegate::_OnSetTimeSample(
    const SdfAbstractDataSpecId& id, double time,
    const SdfAbstractDataConstValue& value) {
    _OnSetTimeSampleImpl(id, time);
}

void UsdQt_UndoStateDelegate::_OnCreateSpec(const SdfPath& path,
                                                 SdfSpecType specType,
                                                 bool inert) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Creating spec at '%s'\n", path.GetText());
    _MarkCurrentStateAsDirty();

    _RouteInverse(std::bind(&UsdQt_UndoStateDelegate::_InvertCreateSpec,
                            this, path, inert));
}

// XXX: This is copied from SdLayer
static void _CopySpecAtPath(const SdfAbstractData& src, SdfAbstractData* dst,
                            const SdfPath& path) {
    _CopySpec(src, dst, SdfAbstractDataSpecId(&path));
}

void UsdQt_UndoStateDelegate::_OnDeleteSpec(const SdfPath& path,
                                                 bool inert) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Deleting spec at '%s'\n", path.GetText());
    _MarkCurrentStateAsDirty();

    SdfDataRefPtr deletedData = TfCreateRefPtr(new SdfData());
    SdfLayer::TraversalFunction copyFunc = boost::bind(
        &_CopySpecAtPath, boost::cref(*boost::get_pointer(_GetLayerData())),
        boost::get_pointer(deletedData), _1);
    _GetLayer()->Traverse(path, copyFunc);

    const SdfSpecType deletedSpecType = _GetLayer()->GetSpecType(path);

    _RouteInverse(std::bind(&UsdQt_UndoStateDelegate::_InvertDeleteSpec,
                            this, path, inert, deletedSpecType, deletedData));
}

void UsdQt_UndoStateDelegate::_OnMoveSpec(const SdfPath& oldPath,
                                               const SdfPath& newPath) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Moving spec at '%s' to '%s'\n", oldPath.GetText(),
             newPath.GetText());
    _MarkCurrentStateAsDirty();

    _RouteInverse(std::bind(&UsdQt_UndoStateDelegate::_InvertMoveSpec,
                            this, oldPath, newPath));
}
void UsdQt_UndoStateDelegate::_OnPushChild(const SdfPath& parentPath,
                                                const TfToken& fieldName,
                                                const TfToken& value) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Pushing field '%s' of '%s'\n", fieldName.GetText(),
             parentPath.GetText());
    _MarkCurrentStateAsDirty();

    _RouteInverse(
        std::bind(&UsdQt_UndoStateDelegate::_InvertPushTokenChild, this,
                  parentPath, fieldName, value));
}
void UsdQt_UndoStateDelegate::_OnPushChild(const SdfPath& parentPath,
                                                const TfToken& fieldName,
                                                const SdfPath& value) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Pushing field '%s' of '%s'\n", fieldName.GetText(),
             parentPath.GetText());
    _MarkCurrentStateAsDirty();

    _RouteInverse(std::bind(&UsdQt_UndoStateDelegate::_InvertPushPathChild,
                            this, parentPath, fieldName, value));
}

void UsdQt_UndoStateDelegate::_OnPopChild(const SdfPath& parentPath,
                                               const TfToken& fieldName,
                                               const TfToken& oldValue) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Popping field '%s' of '%s'\n", fieldName.GetText(),
             parentPath.GetText());
    _MarkCurrentStateAsDirty();

    _RouteInverse(std::bind(&UsdQt_UndoStateDelegate::_InvertPopTokenChild,
                            this, parentPath, fieldName, oldValue));
}

void UsdQt_UndoStateDelegate::_OnPopChild(const SdfPath& parentPath,
                                               const TfToken& fieldName,
                                               const SdfPath& oldValue) {
    TF_DEBUG(USDQT_DEBUG_UNDOSTATEDELEGATE)
        .Msg("Popping field '%s' of '%s'\n", fieldName.GetText(),
             parentPath.GetText());
    _MarkCurrentStateAsDirty();

    _RouteInverse(std::bind(&UsdQt_UndoStateDelegate::_InvertPopPathChild,
                            this, parentPath, fieldName, oldValue));
}

PXR_NAMESPACE_CLOSE_SCOPE
