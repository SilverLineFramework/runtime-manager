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
 *     wamr_inst_module(mod, context);
 *     wamr_run_module(mod, args);
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

#include "module.h"
#include "lib_export.h"

#if !defined(DOXYGEN_SHOULD_SKIP_THIS)
typedef struct {
  NativeSymbol *exports;
  uint32_t num_exports;
  char module_name[100];
} NativeSymbolPackage;

bool wamr_init(module_settings_t *settings, NativeSymbolPackage *ns_packages);
bool wamr_create_module(module_wamr_t *mod, module_args_t *args, module_settings_t *settings);
bool wamr_inst_module(module_wamr_t *mod, module_settings_t *settings, void *context);
bool wamr_run_module(module_wamr_t *mod, module_args_t *args, uint64_t *cpu_time);
void wamr_destroy_module(module_wamr_t *mod);
bool wamr_run_once(module_args_t *args, module_settings_t *settings, 
    void *context, module_rusage_t *rusage);
#endif

#endif
/** @} */
