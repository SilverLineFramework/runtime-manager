/**
 * @addtogroup linux-datarace-wali
 * @{
 * @file runtime.c
 * @brief Main runtime.
 */

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

#define STD_MAX_LEN 4096

runtime_t runtime;

module_settings_t glob_settings = {
    .stack_size = 1024 * 1024,
    .heap_size = 0,
    .log_verbose_level = 2,
    .max_threads = 20
};


int socket_vprintf(const char *format, va_list ap) {
    char buf[STD_MAX_LEN];
    int len = vsnprintf(buf, STD_MAX_LEN, format, ap);
    if (len > STD_MAX_LEN) { len = STD_MAX_LEN; }
    slsocket_rwrite(runtime.socket, 0x00, 0x00, buf, len);
    return len;
}

bool run_module(module_t *mod) {
    char openmsg[] = "__$SL/proc/stdio";
    openmsg[0] = 0x00;
    openmsg[1] = CH_WRONLY;
    slsocket_rwrite(
        runtime.socket, H_CONTROL | 0x00, H_CH_OPEN, openmsg, sizeof(openmsg));

    /** Run instrumented code **/
    module_rusage_t rusage = {0};
    if (!init_instrumentation_state()) {
      log_msg(L_ERR, "Failed to initialize instrumentation state");
      goto fail;
    }

    bool res = wamr_run_once(&mod->args, &glob_settings, NULL, &rusage);
    
    char* buf;
    int64_t buflen = get_instrumentation_profile(&buf, (char*)&rusage, sizeof(rusage));
    if (buflen == -1) {
      log_msg(L_ERR, "Instrumentation profile error");
      goto fail;
    }

    slsocket_rwrite(
        runtime.socket, H_CONTROL | 0x00, H_PROFILE, buf, buflen);

    free(buf);
    if (!destroy_instrumentation_state()) {
      log_msg(L_ERR, "Instrumentation destroy error");
      goto fail;
    }
    /** **/

    char exitmsg[] = "{\"status\": \"exited\"}";
    slsocket_rwrite(
        runtime.socket, H_CONTROL | 0x00, H_EXITED, exitmsg, strlen(exitmsg));

    destroy_module_args(&mod->args);
    destroy_metadata_args(&mod->meta);
    return res;
fail:
    return false;
}

bool create_module(module_t *mod, message_t *msg) {
    cJSON *json = cJSON_ParseWithLength(msg->payload, msg->payloadlen);
    bool res = (
        parse_module_args(json, &mod->args)
        && parse_metadata_args(json, &mod->meta));
    cJSON_Delete(json);
    return res;
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
                if (create_module(&runtime.mod, msg)) {
                    run_module(&runtime.mod);
                }
            }
            slsocket_free(msg);
        }
    }
}

/** @} */
