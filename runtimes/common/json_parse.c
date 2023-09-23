/**
 * @addtogroup json
 * @{
 * @file common/json_parse.c
 * @brief Common JSON parsing routines.
 */

#include <stdlib.h>
#include <string.h>
#include "cJSON/cJSON.h"
#include "module.h"
#include "json_utils.h"


static bool parse_argv(cJSON *args, module_args_t *dst) {
    array_string_t tmp;
    if(!get_string_array(args, "argv", &tmp)) { return false; };
    dst->argv.len = 1;
    dst->argv.data = malloc(sizeof(char *) * 1);
    dst->argv.data[0] = malloc(strlen(dst->path) + 1);
    strcpy(dst->argv.data[0], dst->path);

    string_array_concat(&dst->argv, &tmp);
    return true;
}

static bool parse_instrumentation(cJSON *args, module_args_t *dst) {
#if ENABLE_INSTRUMENTATION
    cJSON *inst = cJSON_GetObjectItem(args, "instrument");
    module_instrumentation_t *dstinst = &dst->instrumentation;
    return (
      (inst != NULL) &&
      get_string_value(inst, "scheme", &dstinst->scheme) &&
      get_string_array(inst, "instargs", &dstinst->args));
#else
    return true;
#endif
}

/**
 * @brief Parse module arguments (path, env, argv, dirs, etc).
 */
bool parse_module_args(cJSON *data, module_args_t *dst) {
    cJSON *args = cJSON_GetObjectItem(data, "args");
    return (
        (args != NULL) &&
        get_string_value(data, "file", &dst->path) &&
        get_string_array(args, "dirs", &dst->dirs) &&
        get_string_array(args, "env", &dst->env) && 
        get_integer_value(args, "repeat", &dst->repeat) &&
        parse_argv(args, dst) &&
        parse_instrumentation(args, dst));
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
#if ENABLE_INSTRUMENTATION
        free(dst->instrumentation.scheme);
        string_array_destroy(&dst->instrumentation.args);
#endif
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
