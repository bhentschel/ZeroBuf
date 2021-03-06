# Copyright (c) HBP 2015 Grigori Chevtchenko <grigori.chevtchenko@epfl.ch>

cmake_minimum_required(VERSION 2.8 FATAL_ERROR)

project(ZeroBuf)
list(APPEND CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/CMake
  ${PROJECT_SOURCE_DIR}/zerobuf/share/zerobuf/CMake
  ${CMAKE_SOURCE_DIR}/CMake/common)
include(GitExternal)

set(VERSION_MAJOR "0")
set(VERSION_MINOR "1")
set(VERSION_PATCH "0")
set(VERSION_ABI 1)

include(Common)

set(COMMON_PROJECT_DOMAIN eu.humanbrainproject)
set(ZEROBUF_DESCRIPTION "ZeroBuf is a replacement for FlatBuffers")
set(ZEROBUF_DEPENDENT_LIBRARIES Servus)

common_package(Boost 1.49 COMPONENTS unit_test_framework)
common_package(Servus REQUIRED)
common_package_post()

add_subdirectory(zerobuf)
add_subdirectory(tests)

set(DOXYGEN_MAINPAGE_MD README.md)
set(DOXYGEN_EXTRA_INPUT ${PROJECT_SOURCE_DIR}/README.md)
include(CPackConfig)
include(DoxygenRule)
