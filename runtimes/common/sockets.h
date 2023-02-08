/**
 * @file sockets.h
 * @brief 
 */

#ifndef SOCKETS_H
#define SOCKETS_H

/**
 * @brief Silverline manager message; see runtime-manager for documentation.
 */
typedef struct {
    int payloadlen;
    char h1;
    char h2;
    char *payload;
} message_t;


int slsocket_open(int runtime, int module);
message_t *slsocket_read(int fd);
void slsocket_write(int fd, message_t *msg);

#endif
