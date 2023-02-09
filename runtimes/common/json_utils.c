/**
 * @addtogroup json
 * @{
 * @file arts/json_utils.c
 * @brief JSON parsing abstractions
 */

#include <string.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdio.h>
#include <uuid/uuid.h>

#include "cJSON/cJSON.h"
#include "logging.h"

#include "json_utils.h"

/**
 * @brief Helper to malloc & copy a string.
 * @note This helper is included due to numerous bugs involving forgetting to
 * allocate space for NULL termination.
 */
static char *make_string_copy(char *src) {
    char *dst = malloc(sizeof(char) * (strlen(src) + 1));
    if (dst == NULL) { return NULL; }
    strcpy(dst, src);
    return dst;
}

/**
 * @brief Generate a new random UUID
 * @return A pointer to a UUID string. Free with free()
 */
char *new_uuid() {
    uuid_t uuid_bin;
    char *uuid_str = malloc(UUID_STR_LEN);

    uuid_generate_random(uuid_bin);
    uuid_unparse(uuid_bin, uuid_str);

    return uuid_str;
}

/**
 * @brief Retrieve cJSON string attribute as reference.
 * @param data JSON object
 * @param key JSON key in `data`
 * @param[out] dst Pointer to `char*` to populate with reference to attribute.
 *      Whoever passes `dst` is responsible for ensuring it is NULL.
 * @return success indicator (`false` on exception).
 */
bool get_string_attr(cJSON *data, char *key, char **dst) {
    cJSON *attr = cJSON_GetObjectItemCaseSensitive(data, key);
    if ((attr == NULL) || !cJSON_IsString(attr)) {
        *dst = NULL;
        return false;
    }
    else {
        *dst = attr->valuestring;
        return true;
    }
}

/**
 * @brief Retrieve cJSON string attribute as copy.
 * @param data JSON object
 * @param key JSON key in `data`
 * @param[out] dst Pointer to `char*` to populate with copy of attribute.
 *      Whoever passes `dst` is responsible for ensuring it is NULL.
 * @return success indicator (`false` on exception).
 */
bool get_string_value(cJSON *data, char *key, char **dst) {
    cJSON *attr = cJSON_GetObjectItemCaseSensitive(data, key);
    if ((attr == NULL) || !cJSON_IsString(attr)) {
        *dst = NULL;
        return false;
    }
    else {
        *dst = make_string_copy(attr->valuestring);
        return true;
    }
}

/**
 * @brief Helper to retrieve cJSON string list.
 * 
 * If the attribute is not present, returns an empty array. Returns `false`
 * if attribute value is not an array of strings.
 * 
 * @param data JSON object
 * @param key JSON key in `data`
 * @param[out] dst Array to populate with copies of strings.
 * @return success indicator (`false` on exception).
 */
bool get_string_array(cJSON *data, char *key, array_string_t *dst) {
    cJSON *attr = cJSON_GetObjectItemCaseSensitive(data, key);

    dst->data = NULL;
    dst->len = 0;

    // No such attr -> assume empty list, no exception
    if (attr == NULL) {
        return true;
    }
    // Attr exists, but not array -> raise exception
    else if (!cJSON_IsArray(attr)) {
        log_msg(L_WRN, "Key '%s' should be an array.\n", key);
        return false;
    }
    // Attr exists and is a proper array
    else {
        dst->len = cJSON_GetArraySize(attr);
        dst->data = calloc(dst->len, sizeof(char *));
        if(dst->data == NULL) { return false; }
        for(int i = 0; i < dst->len; i++) {
            cJSON *element = cJSON_GetArrayItem(attr, i);
            if (!cJSON_IsString(element)) {
                log_msg(L_WRN, "Key '%s'/[%d] should be a string.\n", key, i);
                free(dst->data);
                return false;
            }
            dst->data[i] = make_string_copy(
                cJSON_GetArrayItem(attr, i)->valuestring);
            if(dst->data[i] == NULL) { return false; }
        }
        return true;
    }
}

/**
 * @brief Retrive cJSON int attribute
 * @param data JSON object
 * @param key JSON key in `data`
 * @param dst Where to set integer value.
 * @return value.
 */
bool get_integer_value(cJSON *data, char *key, int *dst) {
    cJSON *attr = cJSON_GetObjectItemCaseSensitive(data, key);
    if(!cJSON_IsNumber(attr)) {
        log_msg(L_WRN, "Key '%s' should be a number.\n", key);
        return false;
    } else {
        *dst = attr->valueint;
        return true;
    }
}

/**
 * @brief Parse enum by matching a (short) list of strings.
 * 
 * @param data JSON object
 * @param key JSON Key in `data`
 * @param cfg Parsing instructions
 * @param out output pointer; should be cast to int
 */
bool get_enum_value(
        cJSON *data, char *key, const parse_enum_config_t *cfg, int *out) {
    cJSON *attr = cJSON_GetObjectItemCaseSensitive(data, key);
    if (attr == NULL) {
        *out = cfg->default_value; return true;
    }
    if (!cJSON_IsString(attr)) { return false; }
    for (int i = 0; i < cfg->num_options; i++) {
        if (!strcmp(attr->valuestring, cfg->options[i])) {
            *out = i; return true;
        }
    }
    *out = cfg->default_value; return false;
}

/**
 * @brief Concatenate string arrays.
 * @param[out] dst Modified by appending `src`.
 * @param[in] src Array to concatenate; read-only.
 * @return Success indicator.
 */
bool string_array_concat(array_string_t *dst, array_string_t *src) {
    int len = dst->len + src->len;
    char **data = malloc(sizeof(char *) * len);
    if (data == NULL) { return false; }
    
    memcpy(data, dst->data, dst->len * sizeof(char *));
    for (int i = 0; i < src->len; i++) {
        data[dst->len + i] = make_string_copy(src->data[i]);
    }

    free(dst->data);
    dst->data = data;
    dst->len = len;
    return true;
}

/**
 * @brief Destroy string array (contents only).
 */
void string_array_destroy(array_string_t *arr) {
    if(arr != NULL && arr->data != NULL) {
        for(int i = 0; i < arr->len; i++) { free(arr->data[i]); }
        free(arr->data);
    }
}

/**
 * @brief Create JSON array from string array.
 */
void string_array_to_json(cJSON *data, array_string_t *arr, const char *name) {
    cJSON *arr_json = cJSON_AddArrayToObject(data, name);
    for(int i = 0; i < arr->len; i++) {
        cJSON_AddItemToArray(arr_json, cJSON_CreateString(arr->data[i]));
    }
}

/**
 * @brief Append to string array.
 */
void string_array_append(array_string_t *dst, char *append) {
    if(dst->data == NULL) {
        dst->data = malloc(sizeof(char **));
        dst->data[0] = append;
        dst->len = 1;
    } else {
        dst->data = realloc(dst->data, dst->len + 1);
        dst->data[dst->len] = append;
        dst->len += 1;
    }
}

/**
 * @brief Join strings to form filepath.
 * @param a Parent directory
 * @param b Child directory/file
 * @param out Pointer to location to store result path string.
 */
bool path_concat(char *a, char *b, char **out) {
    size_t path_len = (strlen(a) + 1 + strlen(b) + 1);
    *out = malloc(path_len * sizeof(char));
    if(out == NULL) { return false; }

    snprintf(*out, path_len, "%s/%s", a, b);
    return true;
}

/** @} */
