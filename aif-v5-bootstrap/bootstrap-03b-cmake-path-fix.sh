#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?target project directory required}"
mkdir -p "$ROOT/engine/upscale-ncnn/src/main/cpp"
cat > "$ROOT/engine/upscale-ncnn/src/main/cpp/CMakeLists.txt" <<'AIFV5_EOF'
cmake_minimum_required(VERSION 3.22.1)
project(imagefinisher_upscale)

if(NOT DEFINED REALSR_SRC_DIR)
  message(FATAL_ERROR "REALSR_SRC_DIR is required")
endif()

# GitHub/local build scripts may pass paths relative to the repository root.
# Resolve them deterministically from this module's CMake directory.
set(REPOSITORY_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../../../..")
if(DEFINED ncnn_DIR AND NOT IS_ABSOLUTE "${ncnn_DIR}")
  get_filename_component(ncnn_DIR "${ncnn_DIR}" ABSOLUTE BASE_DIR "${REPOSITORY_ROOT}")
endif()
if(NOT IS_ABSOLUTE "${REALSR_SRC_DIR}")
  get_filename_component(REALSR_SRC_DIR "${REALSR_SRC_DIR}" ABSOLUTE BASE_DIR "${REPOSITORY_ROOT}")
endif()

message(STATUS "Resolved ncnn_DIR=${ncnn_DIR}")
message(STATUS "Resolved REALSR_SRC_DIR=${REALSR_SRC_DIR}")
find_package(ncnn REQUIRED)

add_library(
  imagefinisher_upscale
  SHARED
  realsr_jni.cpp
  ${REALSR_SRC_DIR}/realsr.cpp
)
target_include_directories(imagefinisher_upscale PRIVATE ${REALSR_SRC_DIR})
target_compile_features(imagefinisher_upscale PRIVATE cxx_std_17)
target_link_libraries(imagefinisher_upscale ncnn log android)
AIFV5_EOF
