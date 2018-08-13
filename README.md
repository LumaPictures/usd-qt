# UsdQt

**Qt components for building custom USD tools**

## Project Goals

The UI components that make up `usdview` are good reference for functionality,
but they’re purpose-built for the application, and are implemented in ways that 
make them difficult to decouple from it.

This project is meant to provide application components that can provide similar
(as well as new) functionality, to allow for ad-hoc use in custom tools.

Longer-term, we hope this project will grow to the point that it can be used to
build a fully-functional `usdview` application.

## Contents

This project contains a mixture of pure Python and wrapped C++ code. All Qt code
is written in pure Python to avoid the need to link against Qt and get `moc`
involved in the build process. This may change in the future if deemed 
beneficial/necessary.

The compiled extension module provides a set of helper classes that interface
with the USD C++ API to accelerate certain USD queries, operations, etc.

#### Installed Python Packages

- `pxr.UsdQt`: Contains various Qt item data models, helper classes for building
UIs, and some other USD and Qt utility code. The `_bindings` module currently
contains all of the wrapped classes from the compiled extension module.
- `pxr.UsdQtEditors`: Contains various Qt UI elements. These range from
purpose-built display/editor widgets to an extensible outliner UI that also
serves as a good usage example for many of the utilities in `pxr.UsdQt`.
- `treemodel`: Contains a generic item tree and a Qt item model mixin that uses
it, which are used by some of the classes in `pxr.UsdQt`.

## Building/Installation

The recommended (and currently only tested) way to build the project is using 
CMake. A `setup.py` file is provided as well, but it has not been tested with
the most recent updates.

#### Build Requirements 

- Boost Python
- USD
- TBB

#### CMake Options

- `INSTALL_PURE_PYTHON (BOOL)`: Whether to install the pure Python code in
addition to the compiled extension module. This defaults to `ON`.

#### A note about `UsdQt.py` and `UsdQtEditors.py`

You may notice that the source contains `UsdQt.py` and `UsdQtEditors.py` files
alongside the package source directories. These are "shim" modules that we've 
found to be very useful during the development of this project, as they enable
us to do more rapid editing and testing on the pure Python code without needing
to run a CMake build and install between each minor edit. They are not installed
with the project.

## Using an alternate Qt API

`UsdQt` expects the Qt API it uses to supply the PySide5/Qt5 module layout.

By default, it will attempt to import and use `PySide2`. This can be overridden
by setting the `PXR_QT_PYTHON_BINDING` environment variable to the name of the
API package/module you wish to use instead.

This works with the popular [Qt.py](https://github.com/mottosso/Qt.py) project.
