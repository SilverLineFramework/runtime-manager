/**
 * @defgroup json
 * 
 * Primitives here should always be preferred to custom implementations in
 * order to reduce the possibility of introducing bugs.
 * 
 * All helpers return success as a boolean and provide actual return values
 * through modifying pointers; this way, function calls can be chained
 * by `&&` to generate a success boolean which can be checked at the end. See
 * `decode.c` for examples.
 * 
 * @{
 * @file common/json_utils.h
 * @brief JSON parsing abstractions
 */

#include <stdbool.h>
#include "cJSON/cJSON.h"

#ifndef COMMON_JSON_UTILS_H
#define COMMON_JSON_UTILS_H

/**
 * @brief String array struct.
 */
typedef struct {
    /** Array pointers */
    char **data;
    /** Length */
    int len;
} array_string_t;

/**
 * @brief Enum parsing configuration.
 */
typedef struct {
    /** Enum names */
    const char **options;
    /** Number of options */
    int num_options;
    /** Default value */
    int default_value;
} parse_enum_config_t;

#if !defined(DOXYGEN_SHOULD_SKIP_THIS)
char *new_uuid();

bool get_string_attr(cJSON *data, char *key, char **dst);
bool get_string_value(cJSON *data, char *key, char **dst);
bool get_string_array(cJSON *data, char *key, array_string_t *dst);
bool get_integer_value(cJSON *data, char *key, int *dst);
bool get_enum_value(
        cJSON *data, char *key, const parse_enum_config_t *cfg, int *out);

bool string_array_concat(array_string_t *dst, array_string_t *src);
void string_array_append(array_string_t *dst, char *add);
void string_array_destroy(array_string_t *arr);
void string_array_to_json(cJSON *data, array_string_t *arr, const char *name);

bool path_concat(char *a, char *b, char **out);
#endif

#endif /* COMMON_JSON_UTILS_H */
/** @} */
