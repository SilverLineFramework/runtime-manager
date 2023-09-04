/**
 * @defgroup access_export.h
 *
 * Native exports for memory-access instrumentation
 *
 * @{
 * @file access_export.h
 * @brief Memory-access instrumentation exports
 * }
 */

#ifndef _ACCESS_EXPORT_H_
#define _ACCESS_EXPORT_H_

#include <stdint.h>
#include "lib_export.h"
#include "wasm_export.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Instrumentation exports */
void logstart_wrapper(wasm_exec_env_t exec_env, uint32_t max_instructions);
void logend_wrapper(wasm_exec_env_t exec_env);
void logaccess_wrapper(wasm_exec_env_t exec_env, uint32_t addr, 
    uint32_t opcode, uint32_t inst_idx);

/* Relevant methods */
bool init_instrumentation_state();
bool destroy_instrumentation_state();

/**
 * @brief Get packed instrumentation profile 
 * @param buf_ptr pointer to buffer to store profile
 * @param pre_buf data to prepend to profile
 *
 * @returns length of profile, -1 if failed
 * @note 'buf' is owned by user who is responsible
 *       for freeing memory
 */
int64_t get_instrumentation_profile(char **buf_ptr, char *pre_buf, int pre_len);


/* Exported symbols */
extern NativeSymbol native_access_symbols[];
extern uint32_t num_native_access_symbols;

#ifdef __cplusplus
}
#endif

#endif /* end of _ACCESS_EXPORT_H_ */

/** @} */
