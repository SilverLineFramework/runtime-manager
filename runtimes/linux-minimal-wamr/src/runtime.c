/**
 * @addtogroup linux-minimal-wamr
 * @{
 * @file runtime.c
 * @brief Main runtime.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <unistd.h>
#include "cJSON/cJSON.h"
#include "logging.h"
#include "sockets.h"
#include "json_parse.h"
#include "wamr.h"

#include "module.h"
#include "runtime.h"

#define STD_MAX_LEN 4096

runtime_t runtime;

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

    bool res = wamr_run_once(&mod->args, NULL);

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
    log_init(runtime.socket);

    bool res = wamr_init(NULL);
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
