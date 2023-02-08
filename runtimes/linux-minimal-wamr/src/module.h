/**
 * @addtogroup linux-minimal-wamr
 * @{
 */

#include "../../common/wamr.h"

#ifndef LINUX_MINIMAL_WAMR_MODULE_H
#define LINUX_MINIMAL_WAMR_MODULE_H

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

#endif

/** @} */
