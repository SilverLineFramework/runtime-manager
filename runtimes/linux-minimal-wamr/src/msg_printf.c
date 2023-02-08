/**
 * @addtogroup linux-minimal-wamr
 * @{
 * @file linux-minimal-wamr/msg_printf.c
 * @brief stdout redirection for WAMR.
 */

#include <stdarg.h>

#include "../../common/sockets.h"

/**
 * @brief vprintf override to redirect stdout to socket.
 */
int socket_vprintf(const char *format, va_list ap) {
    message_t msg;
    char buf[4096];
    vsnprintf(buf, sizeof(buf), format, ap);

    buf[4095] = '\0';
    msg.payloadlen = strlen(buf);
    msg.h1 = 0;
    msg.h2 = 0;
    msg.payload = buf;
    slsocket_write(runtime.socket, &msg);
}

/** @} */
