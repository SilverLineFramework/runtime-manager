/**
 * @defgroup opaccess
 *
 * Interface for memory-access associated 
 * WASM opcodes
 *
 * @{
 * @file opaccess.h
 * @brief Memory-access opcode info
 */
#pragma once

#include "wasm-instrument/wasmops.h"
#include <stdint.h>

/**
 * @brief Memory-access type
 */
typedef enum {
  NOACCESS = 0,
  STORE,
  LOAD,
} access_type;

/**
 * @brief Atomicity designator
 */
typedef enum {
  ATOMIC = 0,
  NON_ATOMIC,
} atomic_mode;

/**
 * @brief Opcode info
 */
typedef struct {
  /** Opcode name */
  const char* mnemonic;
  access_type type;
  /** Access size */
  uint8_t width;
  atomic_mode mode;
} opaccess;

/* Defined in C file so we can use designated initializers */
extern const opaccess opcode_access[];

/** @} */
