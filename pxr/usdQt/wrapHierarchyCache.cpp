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

#include <boost/python.hpp>
#include <boost/python/class.hpp>

#include "pxr/pxr.h"
#include "pxr/base/tf/pyPtrHelpers.h"

#include "hierarchyCache.h"

using namespace boost::python;

PXR_NAMESPACE_USING_DIRECTIVE

TF_REFPTR_CONST_VOLATILE_GET(UsdQt_HierarchyCache::Proxy)

void wrapHierarchyCache() {
    {
        typedef UsdQt_HierarchyCache This;
        scope obj =
            class_<This, boost::noncopyable>(
                "_HierarchyCache", init<UsdPrim, Usd_PrimFlagsPredicate>())
                .def("GetChildCount", &This::GetChildCount)
                .def("GetChild", &This::GetChild)
                .def("GetRoot", &This::GetRoot)
                .def("IsRoot", &This::IsRoot)
                .def("GetParent", &This::GetParent)
                .def("GetRow", &This::GetRow)
                .def("ResyncSubtrees", &This::ResyncSubtrees)
                .def("ContainsPath", &This::ContainsPath)
                .def("GetProxy", &This::GetProxy)
                .def("GetPredicate", &This::GetPredicate)
                .def("DebugFullIndex", &This::DebugFullIndex);
        class_<This::Proxy, TfWeakPtr<This::Proxy>, boost::noncopyable>("Proxy",
                                                                        no_init)
            .def(TfPyRefAndWeakPtr())
            .def("GetPrim", &This::Proxy::GetPrim);
    }
}
