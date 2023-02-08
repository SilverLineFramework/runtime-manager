/**
 * @defgroup sockets
 * 
 * Common sockets implementation using AF_UNIX domain sockets to talk between
 * processes on the same system.
 * 
 * @{
 * @file common/sockets.h
 * @brief Silverline Sockets Implementation.
 */

#include <stdint.h>

#ifndef COMMON_SOCKETS_H
#define COMMON_SOCKETS_H

/**
 * @brief Silverline manager message; see runtime-manager for documentation.
 * 
 * Payloadlen, h1, and h2 are packed contiguously so that the first four bytes
 * of `(char *) message_t` correspond to the packet header.
 */
typedef struct {
    uint16_t payloadlen;
    uint8_t h1;
    uint8_t h2;
    char *payload;
} message_t;

#if !defined(DOXYGEN_SHOULD_SKIP_THIS)
int slsocket_open(int runtime, int module);
message_t *slsocket_read(int fd);
void slsocket_write(int fd, message_t *msg);
#endif

#endif

/** @} */
