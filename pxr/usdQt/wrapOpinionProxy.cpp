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

#include <boost/python.hpp>
#include <boost/python/class.hpp>

#include "pxr/pxr.h"
#include "pxr/base/tf/makePyConstructor.h"
#include "pxr/base/tf/pyContainerConversions.h"
#include "pxr/base/tf/pyPtrHelpers.h"
#include "pxr/base/tf/pyResultConversions.h"

#include "pxr/usd/usd/pyConversions.h"

#include "attributeProxy.h"
#include "displayGroupProxy.h"
#include "metadataProxy.h"
#include "objectProxy.h"
#include "primProxy.h"
#include "proxyBase.h"
#include "relationshipProxy.h"
#include "variantSetsProxy.h"

using namespace boost::python;

PXR_NAMESPACE_USING_DIRECTIVE


static VtValue _GetValueMetadata(UsdQt_MetadataProxyPtr proxy) {
    VtValue result;
    if (!proxy->GetValue(&result)) {
        // TODO: Throw error.
        return VtValue();
    }
    return result;
}

static VtValue _GetValueMetadataDictKey(UsdQt_MetadataDictKeyProxyPtr proxy) {
    VtValue result;
    if (!proxy->GetValue(&result)) {
        // TODO: Throw error.
        return VtValue();
    }
    return result;
}

static VtValue _GetValueAttribute(UsdQt_AttributeProxyPtr proxy,
                                  UsdTimeCode time) {
    VtValue result;
    if (!proxy->Get(&result, time)) {
        // TODO: Throw error.
        return VtValue();
    }
    return result;
}

static SdfPathVector _GetTargets(UsdQt_RelationshipProxyPtr proxy) {
    SdfPathVector result;
    if (!proxy->GetTargets(&result)) {
        // TODO: Throw error.
        return SdfPathVector();
    }
    return result;
}

static SdfPathVector _GetForwardedTargets(UsdQt_RelationshipProxyPtr proxy) {
    SdfPathVector result;
    if (!proxy->GetForwardedTargets(&result)) {
        // TODO: Throw error.
        return SdfPathVector();
    }
    return result;
}

static bool _SetValueAttribute(UsdQt_AttributeProxyPtr proxy, object value,
                               UsdTimeCode time) {
    SdfValueTypeName typeName = proxy->GetTypeName();
    if (!typeName) {
        // Should this be a hard rule?  Should this be moved into the C++
        // API?
        TF_CODING_ERROR("Cannot set value on attributes with mixed types.");
        return false;
    }
    return proxy->Set(UsdPythonToSdfType(value, typeName), time);
}

static bool _SetValueMetadata(UsdQt_MetadataProxyPtr proxy, object value) {
    VtValue result;
    if (!UsdPythonToMetadataValue(proxy->GetName(), TfToken(), value,
                                  &result)) {
        TF_CODING_ERROR("Cannot convert python value for metadata set.");
        return false;
    }

    return proxy->SetValue(result);
}

static bool _SetValueMetadataDictKey(UsdQt_MetadataDictKeyProxyPtr proxy,
                                     VtValue value) {
    return proxy->SetValue(value);
}

static std::string _VariantSetsRepr(UsdQt_VariantSetsProxyPtr proxy) {
    return TfStringPrintf("UsdQt_VariantSetsProxy(%zu objects)",
                          proxy->GetSize());
}

static std::string _VariantSetRepr(UsdQt_VariantSetProxyPtr proxy) {
    return TfStringPrintf("UsdQt_VariantSetProxy(%zu objects)",
                          proxy->GetSize());
}

static std::string _PrimRepr(UsdQt_PrimProxyPtr proxy) {
    return TfStringPrintf("UsdQt_PrimProxy(%zu objects)", proxy->GetSize());
}

static std::string _AttributeRepr(UsdQt_AttributeProxyPtr proxy) {
    return TfStringPrintf("UsdQt_AttributeProxy('%s' for '%zu' objects)",
                          proxy->GetName().GetText(), proxy->GetSize());
}

static std::string _RelationshipRepr(UsdQt_RelationshipProxyPtr proxy) {
    return TfStringPrintf("UsdQt_RelationshipProxy('%s' for '%zu' objects)",
                          proxy->GetName().GetText(), proxy->GetSize());
}

static std::string _MetadataRepr(UsdQt_MetadataProxyPtr proxy) {
    return TfStringPrintf("UsdQt_MetadataProxy('%s' for '%zu' objects)",
                          proxy->GetName().GetText(), proxy->GetSize());
}

static std::string _MetadataDictKeyRepr(UsdQt_MetadataDictKeyProxyPtr proxy) {
    return TfStringPrintf(
        "UsdQt_MetadataDictKeyProxy('%s/%s' for '%zu' objects)",
        proxy->GetDictName().GetText(), proxy->GetEntryName().GetText(),
        proxy->GetSize());
}

static std::string _DisplayGroupRepr(UsdQt_DisplayGroupProxyPtr proxy) {
    return TfStringPrintf("UsdQt_DisplayGroupProxy('%s')",
                          proxy->GetName().GetText());
}

TF_REFPTR_CONST_VOLATILE_GET(UsdQt_ProxyBase)
TF_REFPTR_CONST_VOLATILE_GET(UsdQt_ObjectProxy)
TF_REFPTR_CONST_VOLATILE_GET(UsdQt_VariantSetsProxy)
TF_REFPTR_CONST_VOLATILE_GET(UsdQt_VariantSetProxy)
TF_REFPTR_CONST_VOLATILE_GET(UsdQt_MetadataProxy)
TF_REFPTR_CONST_VOLATILE_GET(UsdQt_MetadataDictKeyProxy)
TF_REFPTR_CONST_VOLATILE_GET(UsdQt_AttributeProxy)
TF_REFPTR_CONST_VOLATILE_GET(UsdQt_RelationshipProxy)
TF_REFPTR_CONST_VOLATILE_GET(UsdQt_PrimProxy)
TF_REFPTR_CONST_VOLATILE_GET(UsdQt_DisplayGroupProxy)

void wrapOpinionProxy() {
    {
        typedef UsdQt_ProxyBase This;
        typedef UsdQt_ProxyBasePtr ThisPtr;
        class_<This, ThisPtr, boost::noncopyable>("_ProxyBase", no_init);
    }
    {
        typedef UsdQt_ObjectProxy This;
        typedef UsdQt_ObjectProxyPtr ThisPtr;
        class_<This, ThisPtr, boost::noncopyable,
               bases<UsdQt_ProxyBase>>("_ObjectProxy", no_init)
            .def("ContainsPathOrDescendent", &This::ContainsPathOrDescendent)
            .def("ContainsPath", &This::ContainsPath);
    }
    {
        typedef UsdQt_VariantSetsProxy This;
        typedef UsdQt_VariantSetsProxyPtr ThisPtr;
        std::vector<std::string> (This::*ThisGetNames)() const =
            &This::GetNames;
        class_<This, ThisPtr, boost::noncopyable, bases<UsdQt_ProxyBase>>(
            "_VariantSetsProxy", no_init)
            .def(TfPyRefAndWeakPtr())
            .def(TfMakePyConstructor(&This::New))
            .def("GetNames", ThisGetNames,
                 return_value_policy<TfPySequenceToList>())
            .def("IsValid", &This::IsValid)
            .def("CreateVariantSetProxy", &This::CreateVariantSetProxy,
                 return_value_policy<TfPyRefPtrFactory<>>())
            .def("__repr__", &::_VariantSetsRepr);
        TfPyRegisterStlSequencesFromPython<UsdVariantSets>();
    }
    {
        typedef UsdQt_VariantSetProxy This;
        typedef UsdQt_VariantSetProxyPtr ThisPtr;

        class_<This, ThisPtr, boost::noncopyable,
               bases<UsdQt_ProxyBase>>("_VariantSetProxy", no_init)
            .def(TfPyRefAndWeakPtr())
            .def(TfMakePyConstructor(&This::New))
            .def("GetName", &This::GetName)
            .def("GetVariantNames", &This::GetVariantNames,
                 return_value_policy<TfPySequenceToList>())
            .def("GetVariantSelection", &This::GetVariantSelection)
            .def("SetVariantSelection", &This::SetVariantSelection)
            .def("ClearVariantSelection", &This::ClearVariantSelection)
            .def("__repr__", &::_VariantSetRepr);
        TfPyRegisterStlSequencesFromPython<UsdVariantSet>();
    }
    {
        typedef UsdQt_MetadataProxy This;
        typedef UsdQt_MetadataProxyPtr ThisPtr;

        class_<This, ThisPtr, boost::noncopyable,
               bases<UsdQt_ProxyBase>>("_MetadataProxy", no_init)
            .def(TfPyRefAndWeakPtr())
            .def(TfMakePyConstructor(&This::New))
            .def("GetValue", &::_GetValueMetadata)
            .def("SetValue", &::_SetValueMetadata)
            .def("ClearValue", &This::ClearValue)
            .def("GetName", &This::GetName)
            .def("GetType", &This::GetType)
            .def("GetDictKeys", &This::GetDictKeys)
            .def("GetObjects", &This::GetObjects,
                 return_value_policy<TfPySequenceToList>())
            .def("CreateMetadataDictKeyProxy",
                 &This::CreateMetadataDictKeyProxy,
                 return_value_policy<TfPyRefPtrFactory<>>())
            .def("GetSize", &This::GetSize)
            .def("__repr__", &_MetadataRepr);
    }
    {
        typedef UsdQt_MetadataDictKeyProxy This;
        typedef UsdQt_MetadataDictKeyProxyPtr ThisPtr;
        class_<This, ThisPtr, boost::noncopyable,
               bases<UsdQt_ProxyBase>>("_MetadataDictKeyProxy", no_init)
            .def(TfPyRefAndWeakPtr())
            .def(TfMakePyConstructor(&This::New))
            .def("GetValue", &::_GetValueMetadataDictKey)
            .def("GetType", &This::GetType)
            .def("SetValue", &::_SetValueMetadataDictKey)
            .def("ClearValue", &This::ClearValue)
            .def("GetDictName", &This::GetDictName)
            .def("GetEntryName", &This::GetEntryName)
            .def("__repr__", &_MetadataDictKeyRepr);
    }
    {
        typedef UsdQt_AttributeProxy This;
        typedef UsdQt_AttributeProxyPtr ThisPtr;
        class_<This, ThisPtr, boost::noncopyable, bases<UsdQt_ObjectProxy>>(
            "_AttributeProxy", no_init)
            .def(TfPyRefAndWeakPtr())
            .def(TfMakePyConstructor(&This::New))
            .def("GetName", &This::GetName)
            .def("Get", &::_GetValueAttribute)
            .def("Set", &::_SetValueAttribute)
            .def("Clear", &This::Clear)
            .def("ClearAtTime", &This::ClearAtTime)
            .def("Block", &This::Block)
            .def("GetTypeName", &This::GetTypeName)
            .def("GetVariability", &This::GetVariability)
            .def("GetAllowedTokens", &This::GetAllowedTokens)
            .def("GetDocumentation", &This::GetDocumentation)
            .def("GetMetadataFields", &This::GetMetadataFields)
            .def("CreateMetadataProxy", &This::CreateMetadataProxy,
                 return_value_policy<TfPyRefPtrFactory<>>())
            .def("GetSize", &This::GetSize)
            .def("GetAttributes", &This::GetAttributes,
                 return_value_policy<TfPySequenceToList>())
            .def("IsDefined", &This::IsDefined)
            .def("IsAuthored", &This::IsAuthored)
            .def("IsAuthoredAt", &This::IsAuthoredAt)
            .def("__repr__", &::_AttributeRepr);
    }
    {
        typedef UsdQt_RelationshipProxy This;
        typedef UsdQt_RelationshipProxyPtr ThisPtr;

        class_<This, ThisPtr, boost::noncopyable, bases<UsdQt_ObjectProxy>>(
            "_RelationshipProxy", no_init)
            .def(TfPyRefAndWeakPtr())
            .def(TfMakePyConstructor(&This::New))
            .def("GetName", &This::GetName)
            .def("GetTargets", &::_GetTargets)
            .def("GetForwardedTargets", &::_GetForwardedTargets)
            .def("ClearTargets", &This::ClearTargets)
            .def("BlockTargets", &This::BlockTargets)
            .def("GetDocumentation", &This::GetDocumentation)
            .def("GetMetadataFields", &This::GetMetadataFields)
            .def("CreateMetadataProxy", &This::CreateMetadataProxy,
                 return_value_policy<TfPyRefPtrFactory<>>())
            .def("IsDefined", &This::IsDefined)
            .def("IsAuthored", &This::IsAuthored)
            .def("IsAuthoredAt", &This::IsAuthoredAt)
            .def("__repr__", &::_RelationshipRepr);
    }
    {
        typedef UsdQt_PrimProxy This;
        typedef UsdQt_PrimProxyPtr ThisPtr;

        class_<This, ThisPtr, boost::noncopyable, bases<UsdQt_ObjectProxy>>(
            "_PrimProxy", no_init)
            .def(TfPyRefAndWeakPtr())
            .def(TfMakePyConstructor(&This::New))
            .def("GetNames", &This::GetNames,
                 return_value_policy<TfPySequenceToList>())
            .def("GetPrims", &This::GetPrims,
                 return_value_policy<TfPySequenceToList>())
            .def("GetAttributeNames", &This::GetAttributeNames)
            .def("GetRelationshipNames", &This::GetRelationshipNames)
            .def("GetMetadataFields", &This::GetMetadataFields)
            .def("CreateAttributeProxy", &This::CreateAttributeProxy,
                 return_value_policy<TfPyRefPtrFactory<>>())
            .def("CreateRelationshipProxy", &This::CreateRelationshipProxy,
                 return_value_policy<TfPyRefPtrFactory<>>())
            .def("CreateMetadataProxy", &This::CreateMetadataProxy,
                 return_value_policy<TfPyRefPtrFactory<>>())
            .def("CreateVariantSetsProxy", &This::CreateVariantSetsProxy,
                 return_value_policy<TfPyRefPtrFactory<>>())
            .def("ClearExpired", &This::ClearExpired)
            .def("__repr__", &::_PrimRepr);
    }
    {
        typedef UsdQt_DisplayGroupProxy This;
        typedef UsdQt_DisplayGroupProxyPtr ThisPtr;

        class_<This, ThisPtr, boost::noncopyable,
               bases<UsdQt_ProxyBase>>("_DisplayGroupProxy", no_init)
            .def(TfPyRefAndWeakPtr())
            .def(TfMakePyConstructor(&This::New))
            .def("GetName", &This::GetName)
            .def("__repr__", &::_DisplayGroupRepr);
    }
}
