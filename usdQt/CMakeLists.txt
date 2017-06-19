set(PXR_PREFIX pxr/usdImaging)
set(PXR_PACKAGE usdQt)

if (NOT PYSIDE_FOUND)
    message(WARNING "Not building ${PXR_PACKAGE} because of missing dependency: PySide")
    return()
endif()

pxr_library(usdQt
    LIBRARIES
        tf
        usd
        sdf
        ${Boost_PYTHON_LIBRARY}
        ${TBB_tbb_LIBRARY}

    INCLUDE_DIRS
        ${Boost_INCLUDE_DIRS}
        ${TBB_INCLUDE_DIRS}

    PUBLIC_CLASSES
        primFilterCache
        
    PRIVATE_CLASSES
        primIdTable

    CPPFILES
        moduleDeps.cpp
        
    PYMODULE_CPPFILES
        module.cpp
        wrapPrimIdTable.cpp
        wrapPrimFilterCache.cpp

    PYTHON_FILES
        __init__.py
        _bindings.py
)
