cmake_minimum_required (VERSION 3.0)
project (linux-minimal-wamr)

get_filename_component(RUNTIMES_DIR ${CMAKE_CURRENT_SOURCE_DIR} DIRECTORY)
set (COMMON_DIR ${RUNTIMES_DIR}/common)
set (WAMR_ROOT_DIR ${COMMON_DIR}/wasm-micro-runtime)

# --------------------------------------------------------------------------- #
#                              WAMR Configuration                             #
# --------------------------------------------------------------------------- #

set (WAMR_BUILD_PLATFORM "linux")

# Reset default linker flags
set (CMAKE_SHARED_LIBRARY_LINK_C_FLAGS "")
set (CMAKE_SHARED_LIBRARY_LINK_CXX_FLAGS "")

set (CMAKE_C_STANDARD 99)

# Set WAMR_BUILD_TARGET, currently values supported:
# "X86_64", "AMD_64", "X86_32", "AARCH64[sub]", "ARM[sub]", "THUMB[sub]",
# "MIPS", "XTENSA", "RISCV64[sub]", "RISCV32[sub]"
if (NOT DEFINED WAMR_BUILD_TARGET)
  if (CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm64|aarch64)")
    set (WAMR_BUILD_TARGET "AARCH64")
  elseif (CMAKE_SYSTEM_PROCESSOR STREQUAL "riscv64")
    set (WAMR_BUILD_TARGET "RISCV64")
  elseif (CMAKE_SIZEOF_VOID_P EQUAL 8)
    # Build as X86_64 by default in 64-bit platform
    set (WAMR_BUILD_TARGET "X86_64")
  elseif (CMAKE_SIZEOF_VOID_P EQUAL 4)
    # Build as X86_32 by default in 32-bit platform
    set (WAMR_BUILD_TARGET "X86_32")
  else ()
    message(SEND_ERROR "Unsupported build target platform!")
  endif ()
endif ()

add_compile_definitions(_GNU_SOURCE)
set (CMAKE_BUILD_TYPE Debug)
set (WAMR_BUILD_INTERP 1)
set (WAMR_BUILD_AOT 1)
set (WAMR_BUILD_JIT 0)
set (WAMR_BUILD_FAST_JIT 0)
set (WAMR_BUILD_LIBC_BUILTIN 1)
set (WAMR_BUILD_LIBC_WASI 1)
set (WAMR_BUILD_FAST_INTERP 1)
set (WAMR_BUILD_MULTI_MODULE 1)
set (WAMR_BUILD_LIB_PTHREAD 0)
set (WAMR_BUILD_MINI_LOADER 0)
set (WAMR_BUILD_SIMD 1)
set (WAMR_BUILD_REF_TYPES 0)

# linker flags
set (CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,--gc-sections -pie -fPIE")
set (CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -g -Wall -Wextra -Wformat -Wformat-security")

if (WAMR_BUILD_TARGET MATCHES "X86_.*" OR WAMR_BUILD_TARGET STREQUAL "AMD_64")
  if (NOT (CMAKE_C_COMPILER MATCHES ".*clang.*" OR CMAKE_C_COMPILER_ID MATCHES ".*Clang"))
    set (CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -mindirect-branch-register")
  endif ()
endif ()

# build out vmlib
include (${WAMR_ROOT_DIR}/build-scripts/runtime_lib.cmake)

add_library(vmlib ${WAMR_RUNTIME_LIB_SOURCE})

# --------------------------------------------------------------------------- #
#                            Runtime Configuration                            #
# --------------------------------------------------------------------------- #

message(STATUS "${RUNTIMES_DIR}")
message(STATUS "${COMMON_DIR}")
message(STATUS "${WAMR_ROOT_DIR}")
message(STATUS "${CMAKE_CURRENT_LIST_DIR}")

include_directories(${CMAKE_CURRENT_LIST_DIR}/src)
include_directories(${RUNTIMES_DIR}/common)
include (${SHARED_DIR}/utils/uncommon/shared_uncommon.cmake)

add_definitions(-DBH_VPRINTF=socket_vprintf)

add_executable(
    runtime
    # cJSON
    ${COMMON_DIR}/cJSON/cJSON.c
    # Common files
    ${COMMON_DIR}/json_parse.c
    ${COMMON_DIR}/json_utils.c
    ${COMMON_DIR}/sockets.c
    ${COMMON_DIR}/wamr.c
    ${COMMON_DIR}/logging.c
    # Runtime files
    src/runtime.c
    ${UNCOMMON_SHARED_SOURCE}
)

target_link_libraries (
    runtime vmlib -lm -ldl -lpthread -lrt -lrt -larchive)
