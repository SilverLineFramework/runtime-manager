/**
 * @addtogroup json
 * @{
 * @file common/json_parse.c
 * @brief Common JSON parsing routines.
 */

#include "cJSON/cJSON.h"
#include "module.h"

#ifndef COMMON_JSON_PARSE_H

bool parse_module_args(cJSON *data, module_args_t *dst);
bool parse_metadata_args(cJSON *data, module_metadata_t *dst);

void destroy_module_args(module_args_t *dst);
void destroy_metadata_args(module_metadata_t *dst);

#endif

/** @} */
