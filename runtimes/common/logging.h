/**
 * @defgroup logging
 * @{
 * @file common/logging.h
 * @brief Interface for logging library
 */

#ifndef LOGGING_H
#define LOGGING_H

#include <stdbool.h>

#define L_CRI 50
#define L_ERR 40
#define L_WRN 30
#define L_INF 20
#define L_DBG 10
#define L_ALL 0

#define LOG_MSG_MAX_LEN 1023

#if !defined(DOXYGEN_SHOULD_SKIP_THIS)
void log_init(int fd);
void log_msg(int level, const char *format, ...);
#endif

#endif /* LOGGING_H */
/** @} */
