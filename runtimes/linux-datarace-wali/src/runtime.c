/**
 * @addtogroup linux-datarace-wali
 * @{
 * @file runtime.c
 * @brief Main runtime.
 */

#include <sys/mman.h>
#include <sys/wait.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include "cJSON/cJSON.h"
#include "logging.h"
#include "sockets.h"
#include "json_parse.h"
#include "wamr.h"

#include "module.h"
#include "runtime.h"
#include "access_export.h"
#include "../interpreter/wasm_runtime.h"
#include "../aot/aot_runtime.h"

#define STD_MAX_LEN 4096

runtime_t runtime;

module_settings_t glob_settings = {
    .stack_size = 1024 * 1024,
    .heap_size = 1024 * 1024,
    .log_verbose_level = 0,
    .max_threads = 20,
};

static uint32_t get_global_value(WASMModuleInstance *inst, const char* name) {
  uint32_t gval;
  if (inst->module_type == Wasm_Module_Bytecode) {
    WASMGlobalInstance *glob = wasm_lookup_global(inst, name);
    memcpy(&gval, inst->global_data + glob->data_offset, sizeof(uint32_t));
  } else {
    AOTGlobal *glob = aot_lookup_global(inst, name)->u.glob;
    memcpy(&gval, inst->global_data + glob->data_offset, sizeof(uint32_t));
  }
  return gval;
}

static bool run_module_once(module_t *mod) {
    /** Run instrumented code **/
    module_rusage_t rusage = {0};
    bool instrument_success = false;
    
    module_wamr_t modwamr;
    memset(&modwamr, 0, sizeof(modwamr));
    bool res = (
        wamr_create_module(&modwamr, &mod->args) &&
        wamr_inst_module(&modwamr, &glob_settings, NULL));
    /* Init instrumentation after instantiate to obtain viable address space */
    if (res) {
        uint32_t max_mem = wasm_runtime_get_max_memory_size(modwamr.inst);
        if (!(res = init_instrumentation_state(max_mem))) {
            log_msg(L_ERR, "Failed to initialize instrumentation state");
        }
        else {
            /* Setup and write mask */
            module_instrumentation_t *inst_params = &mod->args.instrumentation;
            if (!strcmp(inst_params->scheme, "memaccess-stochastic")) {
                WASMModuleInstance *tmp_inst = (WASMModuleInstance*)modwamr.inst;
                uint32_t density = atoi(inst_params->args.data[0]);
                uint8_t *memstart = wasm_get_default_memory(tmp_inst)->memory_data;
                uint32_t meminst_base = get_global_value(tmp_inst, "__inst_membase") * WASM_PAGE_SIZE;
                uint32_t max_insts = get_global_value(tmp_inst, "__inst_max");
                fill_rand_instmask(memstart + meminst_base + 1, density, max_insts);
                log_msg(L_INF, "Stochastic mask with density %d written", density);
            }
        }
    }
    /* Run the module if prior successful steps */
    res = (res && wamr_run_module(&modwamr, &mod->args, &rusage.cpu_time));
    wamr_destroy_module(&modwamr);

    if (!res) {
      log_msg(L_ERR, "WAMR run failed!");
      goto cleanup;
    }

    /** Gather profile **/
    char* buf;
    int64_t buflen = get_instrumentation_profile(&buf, (char*)&rusage, sizeof(rusage));
    if (buflen == -1) {
      log_msg(L_ERR, "Instrumentation profile error");
      goto cleanup;
    }
    log_msg(L_DBG, "Generated profile data of size %ld\n", buflen);

    slsocket_rwrite(
        runtime.socket, H_CONTROL | 0x00, H_PROFILE, buf, buflen);

    free(buf);
    if (!destroy_instrumentation_state()) {
      log_msg(L_ERR, "Instrumentation destroy error");
      goto cleanup;
    }
    instrument_success = true;
    /** **/

cleanup:
    return res && instrument_success;
}

bool parse_module_create(module_t *mod, message_t *msg) {
    cJSON *json = cJSON_ParseWithLength(msg->payload, msg->payloadlen);
    bool res = (
        parse_module_args(json, &mod->args)
        && parse_metadata_args(json, &mod->meta));
    cJSON_Delete(json);
    return res;
}


__attribute__((noreturn)) static bool run_module_child(module_t *mod, int i) {
  bool succ = freopen("/dev/null", "w", stdout) && freopen("/dev/null", "w", stderr);
  if (!succ) {
    log_msg(L_ERR, "Could not redirect to /dev/null: %s", strerror(errno));
    goto fail;
  }
  if (!run_module_once(mod)) { goto fail; }
  exit(0);
fail:
  exit(11);
}

static bool run_modules(module_t *mod) {
    char exitmsg[] = "{\"status\": \"exited\"}";
    uint32_t repeat = mod->args.repeat;
    uint32_t success_exec = 0;
    for (uint32_t i = 1; i <= repeat; i++) {
        /* Create child process to run module + send profile */
        pid_t cpid = fork();
        if (cpid == 0) {
            run_module_child(mod, i);
        } else if (cpid == -1) {
            log_msg(L_ERR, "Fork failed | Error: %s", strerror(errno));
        }
        else {
            int wstatus;
            wait4(cpid, &wstatus, 0, NULL);
            if (WIFEXITED(wstatus) && !WEXITSTATUS(wstatus)) {
                success_exec++;
            } 
            else {
                int exit_code;
                log_msg(L_ERR, "\'%s\' | Iteration %u failed", mod->args.path, i);
                if (WIFEXITED(wstatus) && (exit_code = WEXITSTATUS(wstatus)))
                    log_msg(L_ERR, "Reason: Invalid exit code (%d)", exit_code);
                else if (WIFSIGNALED(wstatus)) {
                    int signo = WTERMSIG(wstatus);
                    log_msg(L_ERR, "Reason: Terminated by signal \'%s\'(%d)", strsignal(signo), signo);
#ifdef WCOREDUMP
                    if (WCOREDUMP(wstatus)) {
                      log_msg(L_ERR, "WCOREDUMP: Child faced a core dump!");
                    }
#else
                    log_msg(L_ERR, "WCOREDUMP: Cannot trace child for core-dump");
#endif
                } 
                else {
                  log_msg(L_ERR, "Reason: Unknown termination method");
                }
            } 
        }
    }

    log_msg(L_INF, "\'%s\' succesfully executed %d/%d times!", 
        mod->args.path, success_exec, repeat);
    slsocket_rwrite(
        runtime.socket, H_CONTROL | 0x00, H_EXITED, exitmsg, strlen(exitmsg));
    return true;
}

static void destroy_args(module_t *mod) {
    destroy_module_args(&mod->args);
    destroy_metadata_args(&mod->meta);
}

int main(int argc, char **argv) {
    if (argc < 2) { exit(-1); }
    runtime.socket = slsocket_open(atoi(argv[1]), -1);
    if (runtime.socket < 0) { exit(-1); }
    log_init(runtime.socket);

    NativeSymbolPackage ns_package[] = {
      {
        .exports = native_access_symbols,
        .num_exports = num_native_access_symbols,
        .module_name = "instrument"
      }
    };
    bool res = wamr_init(&glob_settings, ns_package);
    if (!res) { exit(-1); }

    log_msg(L_INF, "Runtime launched and connected to socket.");
    while (1) {
        message_t *msg = slsocket_read(runtime.socket);
        if (msg != NULL) {
            if ((msg->h1 & H_CONTROL) != 0) {
                log_msg(
                    L_DBG, "Runtime received message: %.*s",
                    msg->payloadlen, msg->payload);
                if (parse_module_create(&runtime.mod, msg)) {
                    run_modules(&runtime.mod);
                    destroy_args(&runtime.mod);
                }
            }
            slsocket_free(msg);
        }
    }
}

/** @} */
