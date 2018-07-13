set(PXR_PREFIX pxr/usdQtEditors)
set(PXR_PACKAGE usdQtEditors)

if (INSTALL_PURE_PYTHON)
    set(PYTHON_FILES
        _Qt.py
        __init__.py
        hierarchyEditor.py
        layerTextEditor.py
        opinionEditor.py
        outliner.py
        treeView.py
    )
else ()
    set(PYTHON_FILES
        __init__.py)
endif()


_pxr_python_module(usdQtEditors
	PYTHON_LIBRARY
    PYTHON_FILES
        ${PYTHON_FILES}
)
