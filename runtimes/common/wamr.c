/**
 * @addtogroup wamr
 * @{
 * @file common/wamr.c
 * @brief WAMR launch utility
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <stdbool.h>

#include "bh_platform.h"
#include "bh_read_file.h"
#include "wasm_export.h"
#include "wasm_runtime.h"
#include "aot_runtime.h"

#include "module.h"
#include "logging.h"

#define ERROR_SIZE 256


/**
 * @brief Setup default WAMR settings
 */
static void wamr_init_settings(module_settings_t *settings) {
    bh_log_set_verbose_level(settings->log_verbose_level);
    wasm_runtime_set_max_thread_num(settings->max_threads);
}

/**
 * @brief Initialize WAMR.
 */
bool wamr_init(module_settings_t *settings, NativeSymbol *exports, const char* native_name) {

    wamr_init_settings(settings);

    // Initialize WAMR init arguments
    RuntimeInitArgs init_args;
    memset(&init_args, 0, sizeof(RuntimeInitArgs));

    // Set WAMR allocator
    init_args.mem_alloc_type = Alloc_With_Allocator;
    init_args.mem_alloc_option.allocator.malloc_func = malloc;
    init_args.mem_alloc_option.allocator.realloc_func = realloc;
    init_args.mem_alloc_option.allocator.free_func = free;

    // Register native API
    if (exports != NULL) {
        init_args.native_symbols = exports;
        init_args.n_native_symbols = sizeof(exports) / sizeof(NativeSymbol *);
    } else {
        init_args.native_symbols = NULL;
        init_args.n_native_symbols = 0;
    }
    init_args.native_module_name = native_name ? native_name : "env";

    // Initialize runtime
    return wasm_runtime_full_init(&init_args);
}

/**
 * @brief Read from file.
 */
static bool wamr_read_module(module_wamr_t *mod, module_args_t *args) {
    log_msg(L_DBG, "Reading module...");
    mod->file = (char *) bh_read_file_to_buffer(args->path, &mod->size);
    return (mod->file != NULL);
}

/**
 * @brief Load WASM module.
 */
static bool wamr_load_module(module_wamr_t *mod) {
    char err[ERROR_SIZE];
    log_msg(L_DBG, "Loading module...");
    mod->module = wasm_runtime_load(mod->file, mod->size, err, ERROR_SIZE);
    if (mod->module == NULL) { log_msg(L_ERR, "%s", err); }
    return (mod->module != NULL);
}

/**
 * @brief Set WASI arguments (always successful).
 */
static bool wamr_set_wasi_args(module_wamr_t *mod, module_args_t *args) {
#if WASM_ENABLE_LIBC_WASI != 0
    wasm_runtime_set_wasi_args(
        mod->module,
        (const char **) args->dirs.data, args->dirs.len,
        NULL, 0,
        (const char **) args->env.data, args->env.len,
        args->argv.data, args->argv.len);
#endif
    return true;
}

/**
 * @brief Instantiate (or reinstantiate) WASM module.
 */
bool wamr_inst_module(module_wamr_t *mod, module_settings_t *settings, void *context) {
    if (mod->inst != NULL) {
        log_msg(L_DBG, "Reinstantiating module...");
        wasm_runtime_deinstantiate(mod->inst);
    } else {
        log_msg(L_DBG, "Instantiating module...");
    }

    char err[ERROR_SIZE];
    mod->inst = wasm_runtime_instantiate(
        mod->module, settings->stack_size, settings->heap_size, 
        err, ERROR_SIZE);

    if (mod->inst == NULL) { log_msg(L_ERR, "%s", err); }
    else { wasm_runtime_set_custom_data(mod->inst, context); }
    return (mod->inst != NULL);
}

/**
 * @brief Run module.
 */
bool wamr_run_module(module_wamr_t *mod, module_args_t *args) {
    const char* exception;
    int argc = args->argv.len;
    char **argv = args->argv.data;
    log_msg(L_INF, "Running main: %s | argc: %d", args->path, argc);
    bool res = wasm_application_execute_main(mod->inst, argc, argv);
    if ((exception = wasm_runtime_get_exception(mod->inst))) {
        log_msg(L_ERR, exception);
    } else {
        log_msg(L_INF, "Successfully executed main.");
    }
    return res;
}

/**
 * @brief Load WAMR WebAssembly module.
 */
bool wamr_create_module(module_wamr_t *mod, module_args_t *args) {
    // `&&` chaining should short-circuit and skip steps once any of these
    // functions return false.
    log_msg(L_INF, "Creating WAMR module...");
    bool result = (
        wasm_runtime_init_thread_env() &&
        wamr_read_module(mod, args) &&
        wamr_load_module(mod) &&
        wamr_set_wasi_args(mod, args));
    log_msg(L_INF, "Done creating WAMR module.");
    return result;
}

/**
 * @brief Destroy a WAMR WebAssembly module.
 * @note Child `NULL` checks required here since WAMR does not
 * allow/recommend destroying `NULL` objects.
 */
void wamr_destroy_module(module_wamr_t *mod) {
#if WAMR_DISABLE_HW_BOUND_CHECK == 0
    // aot_signal_destroy();
#endif
    if (mod != NULL) {
        if (mod->inst != NULL) { wasm_runtime_deinstantiate(mod->inst); }
        if (mod->module != NULL) { wasm_runtime_unload(mod->module); }
        if (mod->file != NULL) { wasm_runtime_free(mod->file); }
    }
}


/**
 * @brief Create and run a WAMR WebAssembly module once.
 *
 * @param args Module arguments.
 * @param context Optional context to add to module in WAMR.
 * @return success indicator.
 */
bool wamr_run_once(module_args_t *args, module_settings_t *settings, void *context) {
    module_wamr_t mod;
    memset(&mod, 0, sizeof(mod));
    bool res = (
        wamr_create_module(&mod, args) &&
        wamr_inst_module(&mod, settings, context) &&
        wamr_run_module(&mod, args));
    wamr_destroy_module(&mod);
    return res;
}

/** @} */
