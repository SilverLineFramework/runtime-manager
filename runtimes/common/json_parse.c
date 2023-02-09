/**
 * @addtogroup json
 * @{
 * @file common/json_parse.c
 * @brief Common JSON parsing routines.
 */

#include <stdlib.h>
#include "cJSON/cJSON.h"
#include "module.h"
#include "json_utils.h"

/**
 * @brief Parse module arguments (path, env, argv, dirs, etc).
 */
bool parse_module_args(cJSON *data, module_args_t *dst) {
    return (
        get_string_value(data, "filename", &dst->path) &&
        get_string_array(data, "dirs", &dst->dirs) &&
        get_string_array(data, "env", &dst->env) &&
        get_string_array(data, "args", &dst->argv));
}

/**
 * @brief Parse module metadata (name, uuid, etc).
 */
bool parse_metadata_args(cJSON *data, module_metadata_t *dst) {
    return (
        get_integer_value(data, "index", &dst->index) &&
        get_string_value(data, "name", &dst->name) &&
        get_string_value(data, "uuid", &dst->uuid) &&
        get_string_value(data, "parent", &dst->parent));
}

/**
 * @brief Destroy module arguments.
 */
void destroy_module_args(module_args_t *dst) {
    if (dst != NULL) {
        string_array_destroy(&dst->dirs);
        string_array_destroy(&dst->env);
        string_array_destroy(&dst->argv);
        free(dst->path);
    }
}

/**
 * @brief Destroy metadata arguments.
 */
void destroy_metadata_args(module_metadata_t *dst) {
    if (dst != NULL) {
        free(dst->name);
        free(dst->uuid);
        free(dst->parent);
    }
}

/** @} */
