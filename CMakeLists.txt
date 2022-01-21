
# >=3.1 is required for CMAKE_CXX_STANDARD
cmake_minimum_required(VERSION 3.1)
project(usdqt)

if (UNIX AND NOT APPLE)
    set(LINUX TRUE)
endif ()

set(CMAKE_MODULE_PATH "${CMAKE_MODULE_PATH};${CMAKE_CURRENT_SOURCE_DIR}/cmake/modules;${CMAKE_CURRENT_SOURCE_DIR}/cmake/macros")

if (NOT MSVC)
  add_compile_options(-Wall -Wno-unused-local-typedefs -Wno-deprecated )
else()
  add_compile_options("/DNOMINMAX")
endif()

add_compile_options(-DBUILD_OPTLEVEL_OPT -DBUILD_COMPONENT_SRC_PREFIX="")

option(INSTALL_PURE_PYTHON "Install pure python files. Disable to only install compiled extension" ON)

set(BOOST_SYMBOL_NAMESPACE "boost"
    CACHE STRING
    "The symbol namespace used in the Boost build. Defaults to \"boost\"")

include(Private)

if (NOT DEFINED CMAKE_CXX_STANDARD)
    set(CMAKE_CXX_STANDARD 14)
endif()
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(USD REQUIRED)
find_package(TBB REQUIRED)

find_package(PythonInterp REQUIRED)
find_package(PythonLibs REQUIRED)

set(BUILD_SHARED_LIBS ON)
set(Boost_USE_STATIC_LIBS OFF)
find_package(Boost COMPONENTS python27)
if (NOT Boost_FOUND)
    find_package(Boost COMPONENTS python REQUIRED)
endif()

include_directories(${Boost_INCLUDE_DIRS})

include_directories(${USD_INCLUDE_DIR})
link_directories(${USD_LIBRARY_DIR})

include_directories(SYSTEM ${PYTHON_INCLUDE_DIRS})
include_directories(SYSTEM ${TBB_INCLUDE_DIRS})

add_subdirectory(pxr)

# TODO: Compile installed .py files as well
install(DIRECTORY treemodel
        DESTINATION lib/python
        PATTERN "*.py")
