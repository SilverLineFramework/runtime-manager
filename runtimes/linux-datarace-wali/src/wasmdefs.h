#pragma once
#include "../wasm-instrument/wasmops.h"
#include <stdint.h>

/* Must be a C-compatible header for designated init */
typedef enum {
  NOACCESS = 0,
  STORE,
  LOAD,
} access_type;

typedef enum {
  ATOMIC = 0,
  NON_ATOMIC,
} atomic_mode;

typedef struct {
  const char* mnemonic;
  access_type type;
  uint8_t width;
  atomic_mode mode;
} opaccess;

/* Defined in C file so we can use designated initializers */
extern const opaccess opcode_access[];

