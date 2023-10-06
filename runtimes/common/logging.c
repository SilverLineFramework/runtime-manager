/**
 * @addtogroup logging
 * @{
 * @file logging.c
 * @brief Socket logging implementation.
 */

#include <stdarg.h>
#include <stdio.h>

#include "logging.h"
#include "sockets.h"

/** Global socket (to avoid having to pass `socket` as context everywhere) */
static int _socket;

/**
 * @brief Initialize logging.
 * @param fd File descriptor to write logging messages to.
 */
void log_init(int fd) {
    _socket = fd;
}

/**
 * @brief Logging function; should be implemented by including programs.
 * 
 * @param level Logging level; uses Python's log level convention.
 * @param format Format string.
 * @param ap Argument list (varargs).
 */
void log_msg(int level, const char *format, ...) {
    va_list args;
    va_start(args, format);

    char buf[LOG_MAX_LEN];
    int len = vsnprintf(&buf[1], LOG_MAX_LEN - 1, format, args);
    if (len > LOG_MAX_LEN) { len = LOG_MAX_LEN; }
    buf[0] = H_CONTROL | (level < 256 ? level : 256);

    slsocket_rwrite(_socket, H_CONTROL | 0x00, H_LOG_RUNTIME, buf, len + 1);
}

/** @} */
