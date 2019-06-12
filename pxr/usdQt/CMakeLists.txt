set(PXR_PREFIX pxr/usdQt)
set(PXR_PACKAGE usdQt)

add_custom_target(shared_libs)
add_custom_target(python ALL)

if (INSTALL_PURE_PYTHON)
    set(PYTHON_FILES
        _Qt.py
        __init__.py
        _bindings.py
        compatability.py
        hierarchyModel.py
        hooks.py
        layerModel.py
        opinionModel.py
        opinionStackModel.py
        qtUtils.py
        roles.py
        stageCacheModel.py
        usdUtils.py
        valueDelegate.py
        valueWidgets.py
    )
else ()
    set(PYTHON_FILES
        __init__.py)
endif()


_pxr_python_module(usdQt
	PYTHON_LIBRARY
    LIBRARIES
        tf
        sdf
        vt
        pcp
        arch
        usd
        ${Boost_PYTHON_LIBRARY}
        ${PYTHON_LIBRARIES}

    INCLUDE_DIRS
        ${Boost_INCLUDE_DIRS}
        ${PYTHON_INCLUDE_DIRS}

    CPPFILES
        attributeProxy.cpp
        debugCodes.cpp
        displayGroupProxy.cpp
        hierarchyCache.cpp
        metadataProxy.cpp
        objectProxy.cpp
        primFilterCache.cpp
        primProxy.cpp
        proxyBase.cpp
        relationshipProxy.cpp
        variantSetsProxy.cpp
        utils.cpp
        undoBlock.cpp
        undoInverse.cpp
        undoRouter.cpp
        undoStateDelegate.cpp
        wrapHierarchyCache.cpp
        wrapOpinionProxy.cpp
        wrapPrimFilterCache.cpp
        wrapUndoRouter.cpp
        module.cpp
        moduleDeps.cpp

    PYTHON_FILES
        ${PYTHON_FILES}
)
