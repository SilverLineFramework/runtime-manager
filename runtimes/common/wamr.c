/**
 * @addtogroup wamr
 * @{
 * @file common/wamr.c
 * @brief WAMR launch utility
 */

#include <stdbool.h>

#include "bh_read_file.h"
#include "wasm_export.h"

#include "wamr.h"

#define STACK_SIZE (1024 * 1024)
#define HEAP_SIZE (1024 * 1024)
#define ERROR_SIZE 256

/**
 * @brief Initialize WAMR.
 */
bool wamr_init(static NativeSymbol *exports) {
    // Initialize WAMR init arguments
    RuntimeInitArgs init_args;
    memset(&init_args, 0, sizeof(RuntimeInitArgs));

    // Set WAMR allocator
    init_args.mem_alloc_type = Alloc_With_Allocator;
    init_args.mem_alloc_option.allocator.malloc_func = malloc;
    init_args.mem_alloc_option.allocator.realloc_func = realloc;
    init_args.mem_alloc_option.allocator.free_func = free;

    // Register native API
    init_args.native_symbols = exports;
    init_args.n_native_symbols = sizeof(exports) / sizeof(NativeSymbol);
    init_args.native_module_name = "env";

    // Initialize runtime
    return wasm_runtime_full_init(&init_args);
}

/**
 * @brief Read from file.
 */
static bool wamr_read_module(module_wamr_t *mod, module_args_t *args) {
    log_msg(LOG_TRACE, "Reading module...");
    mod->file = (char *) bh_read_file_to_buffer(args->path, &mod->file_size);
    return (mod->file != NULL);
}

/**
 * @brief Load WASM module.
 */
static bool wamr_load_module(module_wamr_t *mod) {
    char err[ERROR_SIZE];
    log_msg(LOG_TRACE, "Loading module...");
    mod->module = wasm_runtime_load(mod->file, mod->size, err, ERROR_SIZE);
    if (mod->module == NULL) { log_msg(LOG_ERROR, "%s\n", err); }
    return (mod->module != NULL);
}

/**
 * @brief Set WASI arguments (always successful).
 */
static bool wamr_set_wasi_args(module_wamr_t *mod, module_args_t *args) {
#if WASM_ENABLE_LIBC_WASI != 0
    log_msg(LOG_TRACE, "Set WASI args...\n");
    wasm_runtime_set_wasi_args(
        mod->module,
        (const char **) args->dirs.data, args->dirs.len,
        NULL, 0,
        (const char **) args->env.data, args->dirs.len,
        args->argv.data, args->argv.len);
#endif
    return true;
}

/**
 * @brief Instantiate (or reinstantiate) WASM module.
 */
bool wamr_inst_module(module_wamr_t *mod, void *context) {
    if (mod->inst != NULL) {
        log_msg(LOG_TRACE, "Reinstantiating module...\n");
        wasm_runtime_deinstantiate(mod->inst);
    } else {
        log_msg(LOG_TRACE, "Instantiating module...\n");
    }

    char err[ERROR_SIZE];
    mod->inst = wasm_runtime_instantiate(
        mod->wamr.module, STACK_SIZE, HEAP_SIZE, err, ERROR_SIZE);

    if (mod->wamr.inst == NULL) { log_msg(LOG_ERROR, "%s\n", err); }
    else { wasm_runtime_set_custom_data(mod->inst, context); }
    return (mod->inst != NULL);
}

/**
 * @brief Initialize AOT signals.
 */
static bool wamr_init_aot_signal() {
#if WAMR_DISABLE_HW_BOUND_CHECK == 0
    log_msg(LOG_TRACE, "Initializing AOT signals...\n");
    /* Enable thread specific signal and stack guard pages */
    if (!aot_signal_init()) {
        log_msg(LOG_ERROR, "AOT Signal Init failed! Skipping module\n");
        return false;
    }
#endif
    return true;
}

/**
 * @brief Run module.
 */
bool wamr_run_module(module_wamr_t *mod, module_args_t *args) {
    int argc = args->argv.len;
    int argv = args->argv.data;
    log_msg(LOG_INFO, "Running main: %s | argc: %d\n", args->path, argc);
    bool res = wasm_application_execute_main(mod->wamr.inst, argc, argv);
    log_msg(LOG_MODULES, LOG_INFO, "Finished main.\n");
    return res;
}

/**
 * @brief Load WAMR WebAssembly module.
 */
bool wamr_create_module(module_wamr_t *mod, module_args_t *args) {
    // `&&` chaining should short-circuit and skip steps once any of these
    // functions return false.
    log_msg(LOG_DEBUG, "Creating WAMR module...\n");
    bool result = (
        wamr_init_aot_signal() &&
        wamr_read_module(mod, args) &&
        wamr_load_module(mod) &&
        wamr_set_wasi_args(mod, args));
    log_msg(LOG_DEBUG, "Done creating WAMR module.\n");
    return result;
}

/**
 * @brief Destroy a WAMR WebAssembly module.
 * @note Child `NULL` checks required here since WAMR does not
 * allow/recommend destroying `NULL` objects.
 */
void wamr_destroy_module(module_wamr_t *mod) {
#if WAMR_DISABLE_HW_BOUND_CHECK == 0
    aot_signal_destroy();
#endif
    if (mod != NULL) {
        if (mod->inst != NULL) { wasm_runtime_deinstantiate(mod->inst); }
        if (mod->module != NULL) { wasm_runtime_unload(mod->module); }
        if (mod->file != NULL) { wasm_runtime_free(mod->file); }
    }
}

/** @} */
