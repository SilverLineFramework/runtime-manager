/**
 * @addtogroup linux-minimal-wamr
 * @{
 * @file outputs.c
 * @brief Logging and stdout handling.
 */

#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "sockets.h"
#include "logging.h"

#include "runtime.h"

#define STD_MAX_LEN 4096

/**
 * @brief Log a message
 *
 * @param level The logging level
 * @param fmt Format string to log
 */
void log_msg(int level, const char *format, ...) {
    va_list args;
    va_start(args, format);

    char buf[LOG_MAX_LEN];
    int len = vsnprintf(&buf[1], LOG_MAX_LEN, format, args);
    buf[0] = 0x80 | (level < 256 ? level : 256);

    message_t msg;
    msg.h1 = 0x80 | 0x00;
    msg.h2 = 0x01;
    msg.payload = buf;
    msg.payloadlen = len + 1;
    slsocket_write(runtime.socket, &msg);
}

/**
 * @brief vprintf override to redirect stdout to socket.
 */
int socket_vprintf(const char *format, va_list ap) {
    char buf[STD_MAX_LEN];
    int len = vsnprintf(buf, STD_MAX_LEN, format, ap);

    message_t msg;
    msg.h1 = 0x00;
    msg.h2 = 0x00;
    msg.payload = buf;
    msg.payloadlen = len;
    slsocket_write(runtime.socket, &msg);

    return len;
}

/** @} */
