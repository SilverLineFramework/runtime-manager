/**
 * @defgroup wamr
 * 
 * WebAssembly Micro Runtime management utilities.
 *
 * Usage
 * -----
 * Create, instantiate, run, reinstantiate, run again:
 * ```c
 * wamr_create_module(mod, args);
 * while (!done) {
 *     wamr_inst_module(mod);
 *     wamr_run_module(mod);
 * }
 * wamr_destroy_module(mod);
 * ```
 * 
 * @{
 * @file common/wamr.h
 * @brief WAMR launch utility
 */

#ifndef COMMON_WAMR_H
#define COMMON_WAMR_H

#include <stdint.h>
#include <stdbool.h>
#include "wasm_export.h"
#include "wasm_runtime.h"
#include "aot_runtime.h"

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
 * @brief Module arguments passed to WASI.
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


#if !defined(DOXYGEN_SHOULD_SKIP_THIS)
bool wamr_init(static NativeSymbol *exports);
bool wamr_create_module(module_wamr_t *mod, module_args_t *args);
bool wamr_inst_module(module_wamr_t *mod, void *context);
bool wamr_run_module(module_wamr_t *mod, module_args_t *args);
void wamr_destroy_module(module_t *mod);
#endif

#endif
/** @} */
