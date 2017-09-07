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
#include "pxr/base/tf/pyPtrHelpers.h"
#include "pxr/base/tf/pyNoticeWrapper.h"

#include "undoBlock.h"
#include "undoInverse.h"
#include "undoRouter.h"

using namespace boost::python;

PXR_NAMESPACE_USING_DIRECTIVE

TF_INSTANTIATE_NOTICE_WRAPPER(UsdQt::UndoStackNotice, TfNotice);

class UsdQt_PythonUndoBlock {
public:
    explicit UsdQt_PythonUndoBlock() : _block(0) {}

    void Open() {
        if (!TF_VERIFY(_block == 0)) {
            return;
        }
        _block = new UsdQtUndoBlock();
    }

    void Close(object, object, object) {
        if (!TF_VERIFY(_block != 0)) {
            return;
        }
        delete _block;
        _block = 0;
    }

    ~UsdQt_PythonUndoBlock() { delete _block; }

private:
    UsdQtUndoBlock* _block;
};

void wrapUndoRouter() {
    {
        typedef UsdQt_PythonUndoBlock This;
        class_<This, boost::noncopyable>("UndoBlock", init<>())
            .def("__enter__", &This::Open)
            .def("__exit__", &This::Close);
    }
    {
        typedef UsdQtUndoRouter This;
        class_<This, boost::noncopyable>("UndoRouter", no_init)
            .def("TrackLayer", &This::TrackLayer)
            .def("TransferEdits", &This::TransferEdits)
            .staticmethod("TrackLayer")
            .staticmethod("TransferEdits");
    }
    {
        typedef UsdQt::UndoStackNotice This;
        TfPyNoticeWrapper<This, TfNotice>::Wrap();
    }
    {
        typedef UsdQtUndoInverse This;
        class_<This, boost::noncopyable>("UndoInverse", init<>())
            .def("Invert", &This::Invert);
    }
}
