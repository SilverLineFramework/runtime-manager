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

#define H_KEEPALIVE   0x00
#define H_LOG_RUNTIME 0x01
#define H_EXITED      0x02
#define H_CH_OPEN     0x03
#define H_CH_CLOSE    0x04
#define H_LOG_MODULE  0x05
#define H_PROFILE     0x06

#define H_CREATE      0x00
#define H_DELETE      0x01
#define H_STOP        0x02

#define H_CONTROL     0x80
#define H_INDEX       0x7f

#define CH_RDONLY     0x01
#define CH_WRONLY     0x02
#define CH_RDWR       0x03

#define CH_QOS0       0x00
#define CH_QOS1       0x40
#define CH_QOS2       0x80

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
void slsocket_rwrite(int fd, int h1, int h2, char *payload, int payloadlen);
#endif

#endif

/** @} */
