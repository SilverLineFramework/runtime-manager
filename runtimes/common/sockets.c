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
    if (fd < 0) { return fd; }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(struct sockaddr_un));
    addr.sun_family = AF_UNIX;
    if (module == -1) {
        sprintf(addr.sun_path, "/tmp/sl/%02x.s", runtime);
    } else {
        sprintf(addr.sun_path, "/tmp/sl/%02x.%02x.s", runtime, module);
    }

    int res = connect(fd, (const struct sockaddr *) &addr, sizeof(addr));
    if (res < 0) { return res; }
    else { return fd; }
}

/**
 * @brief Read message from socket.
 * @param fd File descriptor of socket.
 * @return Message read.
 */
message_t *slsocket_read(int fd) {
    message_t *msg = malloc(sizeof(message_t));
    if(recv(fd, (char *) msg, 4, MSG_WAITALL) < 4) { return NULL; };

    int payloadlen = msg->payloadlen;
    msg->payload = malloc(payloadlen);
    char *head = msg->payload;
    while (payloadlen > 0) {
        int recv_tgt = payloadlen < 4096 ? payloadlen : 4096;
        int recv_size = recv(fd, head, recv_tgt, MSG_WAITALL);
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

/**
 * @brief Write buffer to socket (non-msg version of slsocket_write)
 * @param fd File descriptor of socket.
 * @param h1 First header value.
 * @param h2 Second header value.
 * @param payload Message payload.
 * @param payloadlen Length of payload buffer.
 */
void slsocket_rwrite(int fd, int h1, int h2, char *payload, int payloadlen) {
    message_t msg;
    msg.h1 = h1;
    msg.h2 = h2;
    msg.payload = payload;
    msg.payloadlen = payloadlen;
    slsocket_write(fd, &msg);
}

/** @} */
