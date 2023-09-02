/**
 * @file common/module.h
 * @brief Common module definitions.
 */

#ifndef COMMON_MODULE_H
#define COMMON_MODULE_H

#include <stdint.h>

#include "wasm_export.h"
#include "json_utils.h"

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

#endif
