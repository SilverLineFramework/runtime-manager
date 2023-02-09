/**
 * @defgroup logging
 * @{
 * @file common/logging.h
 * @brief Interface for logging library
 */

#ifndef LOGGING_H
#define LOGGING_H

#include <stdarg.h>
#include <stdbool.h>

#define L_CRI 50
#define L_ERR 40
#define L_WRN 30
#define L_INF 20
#define L_DBG 10
#define L_ALL 0

#define LOG_MAX_LEN 1024

/**
 * @brief Logging function; should be implemented by including programs.
 * 
 * @param level Logging level; uses Python's log level convention.
 * @param format Format string.
 * @param ap Argument list (varargs).
 */
void log_msg(int level, const char *format, ...);

#endif /* LOGGING_H */
/** @} */
