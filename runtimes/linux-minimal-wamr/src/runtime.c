/**
 * @file runtime.c
 * @brief Main runtime.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "logging.h"
#include "sockets.h"

#include "module.h"
#include "runtime.h"

runtime_t runtime;


int main(int argc, char **argv) {
    if (argc < 1) { exit(-1); }
    runtime.socket = slsocket_open(atoi(argv[1]), -1);
    if (runtime.socket < 0) { exit(-1); }

    log_msg(L_INF, "Launched runtime.");
    while (1) {
        message_t *msg = slsocket_read(runtime.socket);
        if (msg != NULL) {
            if ((msg->h1 & 0x80) != 0) {
                log_msg(L_DBG, "Runtime received message: %s", msg->payload);
                // parse json from msg.payload
                // start module
            }
            free(msg->payload);
            free(msg);
        }

    }
}
