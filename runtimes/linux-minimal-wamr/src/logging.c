/**
 * @addtogroup logging
 * @{
 * @file common/logging.c
 * @brief Logging levels.
 */

#include <stdarg.h>
#include "../../common/sockets.h"
#include "../../common/logging.h"

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
    vsnprintf(buf, LOG_MAX_LEN, format, args);
    buf[LOG_MAX_LEN - 1] = '\0';

    msg.payloadlen = strlen(buf);
    msg.h1 = 0;
    msg.h2 = 0;
    msg.payload = buf;
    slsocket_write(runtime.socket, &msg);

}

/** @} */
