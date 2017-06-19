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
#include <boost/python/def.hpp>
#include <boost/python/enum.hpp>
#include <boost/python/make_constructor.hpp>

#include "pxr/base/tf/pyEnum.h"
#include "pxr/base/tf/pyResultConversions.h"
#include "pxr/base/tf/makePyConstructor.h"
#include "pxr/base/tf/pyContainerConversions.h"
#include "pxr/base/tf/pyPtrHelpers.h"
#include "pxr/base/tf/pyUtils.h"

#include "primIdTable.h"

using namespace boost::python;

void wrapPrimIdTable() {
    {
        typedef UsdQt_PrimIdTable This;
        class_<This, boost::noncopyable>(
            "_PrimIdTable",
            init<UsdStagePtr, UsdPrim, Usd_PrimFlagsPredicate>())
            .def("ContainsId", &This::ContainsId)
            .def("ContainsPath", &This::ContainsPath)
            .def("GetChildCount", &This::GetChildCount)
            .def("GetChildPath", &This::GetChildPath)
            .def("GetIdFromPath", &This::GetIdFromPath)
            .def("GetLastId", &This::GetLastId)
            .def("GetParentId", &This::GetParentId)
            .def("GetPathFromId", &This::GetPathFromId)
            .def("GetPredicate", &This::GetPredicate)
            .def("GetRootPath", &This::GetRootPath)
            .def("GetRow", &This::GetRow)
            .def("IsRoot", &This::IsRoot)
            .def("PrintSubtreeIndex", &This::PrintSubtreeIndex)
            .def("PrintFullIndex", &This::PrintFullIndex)
            .def("RegisterChild", &This::RegisterChild)
            .def("ResyncSubtrees", &This::ResyncSubtrees);
    }
}
