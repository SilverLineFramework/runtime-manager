/**
 * @addtogroup linux-minimal-wamr
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
    /** WAMR state. */
    module_wamr_t wamr;
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
