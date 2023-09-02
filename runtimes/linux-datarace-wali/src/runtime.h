/**
 * @defgroup linux-datarace-wali
 * 
 * Minimal WAMR-based linux C runtime 
 * for single module data-race checking.
 * 
 * @{
 * @file runtime.h
 * @brief Main runtime.
 */

#include "module.h"

#ifndef RUNTIME_H
#define RUNTIME_H

/**
 * @brief Module data.
 */
typedef struct {
    /** Args */
    module_args_t args;
    /** Metadata */
    module_metadata_t meta;
} module_t;


typedef struct {
    /** Only supports one module. */
    module_t mod;
    /** Socket fd. */
    int socket;
} runtime_t;


extern runtime_t runtime;

#endif
/** @} */
