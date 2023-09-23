/**
 * @file common/module.h
 * @brief Common module definitions.
 */

#ifndef COMMON_MODULE_H
#define COMMON_MODULE_H

#include <stdint.h>

#include "wasm_export.h"
#include "json_utils.h"

#if ENABLE_INSTRUMENTATION
#include "instrument_c_api.h"
#endif

/**
 * @brief Module state used by WAMR.
 * @note Stores objects that needs to be freed on exit.
 */
typedef struct {
    /** File buffer */
    char *file;
    /** Buffer size */
    uint32_t size;
    /** WASM Module */
    wasm_module_t module;
    /** Module instance */
    wasm_module_inst_t inst;
} module_wamr_t;

#if ENABLE_INSTRUMENTATION
/**
 * @brief On-fly instrumentation parameters 
 */
typedef struct {
    /** Instrumentation scheme to execute */
    char *scheme;
    /** Arguments for specific scheme */
    array_string_t args;
} module_instrumentation_t;
#endif

/**
 * @brief Module arguments passed to WASI
 * @note Strings are presumed to be owned by module_args_t, and are freed on
 * cleanup.
 */
typedef struct {
    /** Binary path */
    char *path;
    /** Pre-opened directories */
    array_string_t dirs;
    /** Environment variables */
    array_string_t env;
    /** Arguments */
    array_string_t argv;
    /** Repeat exection */
    uint32_t repeat;
#if ENABLE_INSTRUMENTATION
    /** Optional pre-execution instrumentation */
    module_instrumentation_t instrumentation;
#endif
} module_args_t;

/**
 * @brief Module additional settings
*/
typedef struct {
    /** Stack Size */
    uint32_t stack_size;
    /** Heap Size */
    uint32_t heap_size;
    /** Log verbosity */
    int log_verbose_level;
    /** Max Threads */
    uint32_t max_threads;
    /** Native Libraries */
    char *native_libs[8];
} module_settings_t;

/**
 * @brief Module metadata.
 */
typedef struct {
    /** Module index. */
    int index;
    /** Module name. */
    char *name;
    /** Module UUID. */
    char *uuid;
    /** Runtime UUID. */
    char *parent;
} module_metadata_t;

/** 
 * @brief Module usage characteristics
 */
typedef struct {
  /** CPU time to run module (excludes create/load)  */ 
  uint64_t cpu_time;
} module_rusage_t;

/**
 * @brief Module run parameters
 */
typedef struct {
  uint32_t repeat;
} module_runparams_t;

#endif
