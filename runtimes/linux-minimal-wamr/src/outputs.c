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

/**
 * @brief Log a message
 *
 * @param level The logging level
 * @param fmt Format string to log
 */
void log_msg(int level, const char *format, ...) {
    va_list args;
    va_start(args, format);

    message_t msg;
    char buf[LOG_MAX_LEN];
    vsnprintf(&buf[1], LOG_MAX_LEN - 1, format, args);
    buf[0] = 0x80 | (level < 256 ? level : 256);
    buf[LOG_MAX_LEN - 1] = '\0';

    msg.payloadlen = strlen(buf);
    msg.h1 = 0x80 | 0x00;
    msg.h2 = 0x01;
    msg.payload = buf;
    slsocket_write(runtime.socket, &msg);
}

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

    return 0;
}

/** @} */
