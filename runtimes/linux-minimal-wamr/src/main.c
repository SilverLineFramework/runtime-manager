
#include "module.h"

runtime_t runtime;


int main() {
    runtime.socket = slsocket_open(atoi(argv[1]), -1);

    while (1) {
        message_t *msg = slsocket_read(runtime.socket);
        if (msg != NULL) {
            if (msg.h1 & 0x80 != 0) {
                // parse json from msg.payload
                // start module
            }
            free(msg);
            free(msg->payload);
        }

    }

}
