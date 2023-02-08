/**
 * @addtogroup sockets
 * @{
 * @file common/sockets.c
 * @brief Silverline Sockets Implementation.
 */

#include <sys/socket.h>
#include <sys/un.h>
#include <stdlib.h>
#include <stdio.h>

#include "sockets.h"

/**
 * @brief Connect to Silverline manager socket.
 * @param runtime runtime index.
 * @param module module index.
 * @return Socket file descriptor, or -1 on error.
 */
int slsocket_open(int runtime, int module) {
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);

    struct sockaddr_un addr;
    addr.sun_family = AF_UNIX;
    memset(&addr, 0, sizeof(addr));
    if (module == -1) {
        sprintf(addr.sun_path, "/tmp/sl/%02x.s", runtime);
    } else {
        sprintf(addr.sun_path, "/tmp/sl/%02x.%02x.s", runtime, module);
    }

    int rc = connect(fd, (const struct sockaddr *) &addr, sizeof(addr));
    return rc;
}

/**
 * @brief Read message from socket.
 * @param fd File descriptor of socket.
 * @return Message read.
 */
message_t *slsocket_read(int fd) {
    message_t *msg = malloc(sizeof(message_t));
    recv(fd, (char *) msg, 4, MSG_WAITALL);

    int payloadlen = msg->payloadlen;
    msg->payload = malloc(payloadlen);
    char *head = msg->payload;
    while (payloadlen > 0) {
        int recv_size = payloadlen < 4096 ? payloadlen : 4096;
        recv(fd, head, recv_size, MSG_WAITALL);
        payloadlen -= recv_size;
        head += recv_size;
    }
    return msg;
}

/**
 * @brief Write message to socket.
 * @param fd File descriptor of socket.
 * @param msg Message to write. Has header values already set.
 */
void slsocket_write(int fd, message_t *msg) {
    send(fd, (char *) msg, 4, 0);
    send(fd, msg->payload, msg->payloadlen, 0);
}

/** @} */
