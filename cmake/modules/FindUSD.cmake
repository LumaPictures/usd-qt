# Simple module to find USD.

if (EXISTS "$ENV{USD_ROOT}")
    set(USD_ROOT $ENV{USD_ROOT})
endif ()

find_path(USD_INCLUDE_DIR pxr/pxr.h
          PATHS ${USD_ROOT}/include
          DOC "USD Include directory")

find_path(USD_LIBRARY_DIR libusd.so
          PATHS ${USD_ROOT}/lib
          DOC "USD Librarires directory")

find_file(USD_GENSCHEMA
          names usdGenSchema
          PATHS ${USD_ROOT}/bin
          DOC "USD Gen schema application")

# USD Maya components

find_path(USD_KATANA_INCLUDE_DIR usdKatana/api.h
          PATHS ${USD_ROOT}/third_party/katana/include
          DOC "USD Katana Include directory")

find_path(USD_KATANA_LIBRARY_DIR libusdKatana.so
          PATHS ${USD_ROOT}/third_party/katana/lib
          DOC "USD Katana Library directory")

# USD Katana components

include(FindPackageHandleStandardArgs)

find_package_handle_standard_args(
    USD
    REQUIRED_VARS
    USD_INCLUDE_DIR
    USD_LIBRARY_DIR
    USD_GENSCHEMA)
