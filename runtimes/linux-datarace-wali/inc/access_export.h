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

//#ifdef __cplusplus
//extern "C" {
//#endif
//
///* Instrumentation exports */
//void logstart_wrapper(wasm_exec_env_t exec_env, uint32_t max_instructions);
//
//void logend_wrapper(wasm_exec_env_t exec_env);
//
//void logaccess_wrapper(wasm_exec_env_t exec_env, uint32_t addr, 
//    uint32_t opcode, uint32_t inst_idx);

/* Exported symbols */
extern NativeSymbol native_access_symbols[];
extern uint32_t num_native_access_symbols;

//#ifdef __cplusplus
//}
//#endif

#endif /* end of _ACCESS_EXPORT_H_ */

/** @} */
