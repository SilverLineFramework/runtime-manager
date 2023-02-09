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

#include "module.h"
#include "runtime.h"

runtime_t runtime;


bool run_module(module_t *mod) {
    message_t msg;
    char openmsg[256];
    msg.h1 = 0x80 | 0x00;
    msg.h2 = 0x03;
    openmsg[0] = 0x00;
    openmsg[1] = 0x02;
    sprintf(&openmsg[2], "std/%s", mod->meta.uuid);
    msg.payload = openmsg;
    msg.payloadlen = strlen(&openmsg[2]) + 2;
    slsocket_write(runtime.socket, &msg);

    bool res = (
        wamr_create_module(&mod->wamr, &mod->args) &&
        wamr_inst_module(&mod->wamr, NULL) &&
        wamr_run_module(&mod->wamr, &mod->args));
    wamr_destroy_module(&mod->wamr);

    char exitmsg[] = "{\"status\": \"exited\"}";
    msg.h1 = 0x80 | 0x00;
    msg.h2 = 0x02;
    msg.payload = exitmsg;
    msg.payloadlen = strlen(exitmsg);
    slsocket_write(runtime.socket, &msg);

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

void destroy_module(module_t *mod) {
    destroy_module_args(&mod->args);
    destroy_metadata_args(&mod->meta);
}


int main(int argc, char **argv) {
    if (argc < 1) { exit(-1); }
    runtime.socket = slsocket_open(atoi(argv[1]), -1);
    if (runtime.socket < 0) { exit(-1); }

    bool res = wamr_init(NULL);
    if (!res) { exit(-1); }

    log_msg(L_INF, "Runtime launched and connected to socket.");
    while (1) {
        message_t *msg = slsocket_read(runtime.socket);
        if (msg != NULL) {
            if ((msg->h1 & 0x80) != 0) {
                log_msg(L_DBG, "Runtime received message: %s", msg->payload);
                if (create_module(&runtime.mod, msg)) {
                    run_module(&runtime.mod);
                    destroy_module(&runtime.mod);
                }
            }
            free(msg->payload);
            free(msg);
        }
    }
}

/** @} */
