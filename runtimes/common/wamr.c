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
#include "wamr.h"
#include "logging.h"

#define ERROR_SIZE 256

static module_settings_t default_settings = {
  .stack_size = 1024 * 1024,
  .heap_size = 1024 * 1024,
  .log_verbose_level = 2,
  .max_threads = 1
};

static inline uint64_t ts2us(struct timespec ts) {
  return ((uint64_t)ts.tv_sec * 1000000) + ((uint64_t)ts.tv_nsec / 1000);
}

/**
 * @brief Get raw CPU time, not subject to NTP or process suspend
 */
static inline uint64_t get_cpu_time() {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
  return ts2us(ts);
}

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
bool wamr_init(module_settings_t *settings, NativeSymbolPackage *ns_packages) {

    settings = settings ? settings : &default_settings;
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
    if (ns_packages != NULL) {
        init_args.native_symbols = ns_packages->exports;
        init_args.n_native_symbols = ns_packages->num_exports;
        bool name_provided = ns_packages->module_name[0];
        init_args.native_module_name = name_provided ? ns_packages->module_name : "env";
    } else {
        init_args.native_symbols = NULL;
        init_args.n_native_symbols = 0;
        init_args.native_module_name = NULL;
    }

    // Initialize runtime
    return wasm_runtime_full_init(&init_args);
}

/**
 * @brief Read from file.
 */
static bool wamr_read_module(module_wamr_t *mod, module_args_t *args) {
    log_msg(L_DBG, "Reading module...");
    mod->file = (char *) bh_read_file_to_buffer(args->path, &mod->size);
#if ENABLE_INSTRUMENTATION
    module_instrumentation_t *inst_params = &args->instrumentation;
    if ((mod->file != NULL) && (inst_params->scheme != NULL)) {
        uint32_t encode_size = 0;
        /* Decode, instrument, re-encode */
        wasm_instrument_mod_t ins_mod = decode_instrument_module(mod->file, mod->size);
        instrument_module (ins_mod, inst_params->scheme, inst_params->args.data, 
            inst_params->args.len);
        byte *filebuf = encode_file_buf_from_module(ins_mod, &encode_size);
        /* */
        destroy_instrument_module(ins_mod);
        wasm_runtime_free(mod->file);
        mod->file = filebuf;
        mod->size = encode_size;
    }
#endif
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
    settings = settings ? settings : &default_settings;

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
 * @return cpu_time Active execution time for running module
 */
bool wamr_run_module(module_wamr_t *mod, module_args_t *args, uint64_t *cpu_time) {
    const char* exception;
    int argc = args->argv.len;
    char **argv = args->argv.data;
    log_msg(L_INF, "Running main: %s | argc: %d", args->path, argc);
    uint64_t start_time = get_cpu_time();
    bool res = wasm_application_execute_main(mod->inst, argc, argv);
    uint64_t end_time = get_cpu_time();
    if ((exception = wasm_runtime_get_exception(mod->inst))) {
        log_msg(L_ERR, exception);
    } else {
        log_msg(L_INF, "Successfully executed main.");
    }
    *cpu_time = end_time - start_time;
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
 * @param settings Instantiate and runtime module settings.
 * @param context Optional context to add to module in WAMR.
 * @return success indicator.
 * @return rusage module resource usage stats
 */
bool wamr_run_once(module_args_t *args, module_settings_t *settings, 
      void *context, module_rusage_t *rusage) {
    module_wamr_t mod;
    memset(&mod, 0, sizeof(mod));
    bool res = (
        wamr_create_module(&mod, args) &&
        wamr_inst_module(&mod, settings, context) &&
        wamr_run_module(&mod, args, &rusage->cpu_time));
    wamr_destroy_module(&mod);
    return res;
}

/** @} */
