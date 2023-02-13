/**
 * @addtogroup linux-minimal-wamr
 * @{
 * @file runtime.c
 * @brief Main runtime.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON/cJSON.h"
#include "logging.h"
#include "sockets.h"
#include "json_parse.h"
#include "wamr.h"

#include "wasm_export.h"
#include "wasm_runtime.h"
#include "aot_runtime.h"

#include "module.h"
#include "runtime.h"

#define STD_MAX_LEN 4096

runtime_t runtime;


bool run_module(module_t *mod) {
    char openmsg[256];
    openmsg[0] = 0x00;
    openmsg[1] = CH_WRONLY;
    int len = sprintf(&openmsg[2], "std/%s", mod->meta.uuid) + 2;
    slsocket_rwrite(runtime.socket, H_CONTROL | 0x00, H_CH_OPEN, openmsg, len);

    bool res = (
        wamr_create_module(&mod->wamr, &mod->args) &&
        wamr_inst_module(&mod->wamr, NULL) &&
        wamr_run_module(&mod->wamr, &mod->args));

    uint64_t *table = ((WASMModuleInstance *) mod->wamr.inst)->opcode_table;
    slsocket_rwrite(
        runtime.socket, H_CONTROL | 0x00, H_PROFILE,
        (char *) table, 256 * sizeof(uint64_t));

    wamr_destroy_module(&mod->wamr);

    char exitmsg[] = "{\"status\": \"exited\"}";
    slsocket_rwrite(
        runtime.socket, H_CONTROL | 0x00, H_EXITED, exitmsg, strlen(exitmsg));

    destroy_module_args(&mod->args);
    destroy_metadata_args(&mod->meta);
    return res;
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

    bool res = wamr_init(NULL);
    if (!res) { exit(-1); }

    log_msg(L_INF, "Runtime launched and connected to socket.");
    while (1) {
        message_t *msg = slsocket_read(runtime.socket);
        if (msg != NULL) {
            if ((msg->h1 & H_CONTROL) != 0) {
                log_msg(L_DBG, "Runtime received message: %s", msg->payload);
                if (create_module(&runtime.mod, msg)) {
                    run_module(&runtime.mod);
                }
            }
            slsocket_free(msg);
        }
    }
}

/** @} */
