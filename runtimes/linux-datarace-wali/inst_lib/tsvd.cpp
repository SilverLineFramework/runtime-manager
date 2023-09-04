#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>

#include "wasm_export.h"
#include "lib_export.h"
#include "opaccess.h"
#include "access_export.h"

#include <unordered_set>
#include <mutex>
#include <queue>
#include <atomic>
#include <cstring>

#define INSTRUMENT 1
#define TRACE_ACCESS 0
#define TRACE_VIOLATION 0

#define DELAY 500

/* Code Access Record */
struct access_record {
  wasm_exec_env_t tid;
  uint32_t inst_idx;
  uint32_t opcode;
  uint32_t addr;

  bool operator==(const access_record& record) const {
    return (inst_idx == record.inst_idx) && (opcode == record.opcode);
  }
};

/* Violation Record */
typedef std::pair<access_record, access_record> AccessRecordPair;
struct AccessRecordPairHashFunction {
  size_t operator()(const AccessRecordPair &p) const {
    return std::hash<uint32_t>{}(p.first.inst_idx) ^ std::hash<uint32_t>{}(p.second.inst_idx);
  }
};
struct AccessRecordPairEqualFunction {
  bool operator()(const AccessRecordPair &lhs, const AccessRecordPair &rhs) const {
    return (lhs == rhs) || ((lhs.first == rhs.second) && (lhs.second == rhs.first));
  }
};
typedef std::unordered_set<AccessRecordPair, AccessRecordPairHashFunction, AccessRecordPairEqualFunction> ViolationSet;


static ViolationSet violation_set;
static std::mutex violation_mtx;

/* TSV Access Logging */
struct tsv_entry {
  std::atomic_bool probe;
  std::atomic_llong freq_diff_tid_consec;
  access_record access;
  std::mutex access_mtx;
};
tsv_entry *tsv_table = NULL;
size_t table_size = sizeof(tsv_entry) * ((size_t)1 << 32);

struct inst_entry {
  std::atomic_llong freq;
};
//inst_entry* instruction_map = NULL;
/*  */


/* Delay without nanosleep since we don't want syscall overhead */
/* Delay is relative to processor speed */
static inline void delay(uint32_t punits) {
  for (int i = 0; i < punits; i++) {
    asm volatile ("nop");
  }
}

void logaccess_wrapper(wasm_exec_env_t exec_env, uint32_t addr, uint32_t opcode, uint32_t inst_idx) {
  #if INSTRUMENT == 1
  #if TRACE_ACCESS == 1
  if (cur_access.type == STORE) 
    printf("I: %u | A: %u | T: %p (W)\n", inst_idx, addr, tid); 
  else 
    printf("I: %u | A: %u | T: %p (R)\n", inst_idx, addr, tid); 
  #endif

  access_record cur_access {exec_env, inst_idx, opcode, addr};
  tsv_entry *entry = tsv_table + addr;
  /* Only one thread sets/checks the probe at any time 
  * Unlock happens within if-else block to allow unlocking before the delay */
  entry->access_mtx.lock();
  bool probed = entry->probe.exchange(true);
  /* If not probed, setup probe info and delay */
  if (!probed) {
    /* Access record must be updated atomically */
    entry->access = cur_access;
    entry->access_mtx.unlock();
    delay(DELAY);
    entry->probe.store(false);
  }
  /* If probed, check if at least one write from different thread */
  else {
    /* Access checked atomically */
    if (exec_env != entry->access.tid) {
      const opaccess opacc1 = opcode_access[entry->access.opcode];
      const opaccess opacc2 = opcode_access[opcode];
      if ( ((opacc1.type == STORE) || (opacc2.type == STORE))
            && ((opacc1.mode == NON_ATOMIC) || (opacc2.mode == NON_ATOMIC)) ) {
        /* Log as violation */
        violation_mtx.lock();
        std::pair<ViolationSet::iterator, bool> result = violation_set.insert(std::make_pair(entry->access, cur_access));
        #if TRACE_VIOLATION == 1
        printf("Current violation: %d, %d\n", entry->access.inst_idx, cur_access.inst_idx);
        #endif
        violation_mtx.unlock();
      }
      /* Probed accesses from different threads recorded */
      entry->freq_diff_tid_consec++;
    }
    entry->access_mtx.unlock();
  }
  //instruction_map[inst_idx].freq++;
  #endif
}


void logstart_wrapper(wasm_exec_env_t exec_env, uint32_t max_instructions) {}
void logend_wrapper(wasm_exec_env_t exec_env) {}

/* Initialization routine */
bool init_instrumentation_state() {
  tsv_table = (tsv_entry*) mmap(NULL, table_size, PROT_READ|PROT_WRITE, 
                    MAP_PRIVATE|MAP_ANONYMOUS|MAP_NORESERVE, -1, 0);
  if (tsv_table == NULL) {
    perror("malloc error");
    return false;
  }

  violation_set.clear();
  return true;
}

/* Destruction routine */
bool destroy_instrumentation_state() {
  int status = munmap(tsv_table, table_size);
  if (status == -1) {
    perror("munmap error");
    return false;
  }
  tsv_table = NULL;
  return true;
}

typedef struct __attribute__((packed)) {
  uint32_t addr;
  uint32_t instidx_1;
  uint32_t op_1;
  uint32_t instidx_2;
  uint32_t op_2;
} profile_elem_t;

int64_t get_instrumentation_profile(char **buf_ptr, char *pre_buf, int pre_len) {

  int64_t buf_size = 0;

  #if INSTRUMENT == 1
  uint32_t i = 0;
  profile_elem_t *profile_data = NULL;
  uint32_t num_violations = violation_set.size();

  buf_size = pre_len + sizeof(uint32_t) + (sizeof(profile_elem_t) * violation_set.size());
  *buf_ptr = (char *) malloc(buf_size);
  if (*buf_ptr == NULL) { goto fail; }

  memcpy(*buf_ptr, pre_buf, pre_len);
  memcpy((*buf_ptr) + pre_len, &num_violations, sizeof(uint32_t));
  profile_data = (profile_elem_t *)((*buf_ptr) + pre_len + sizeof(uint32_t));

  for (auto &violation : violation_set) {
    const access_record *first = &violation.first;
    const access_record *second = &violation.second;
    if ((first->tid == second->tid) || (first->addr != second->addr)) {
      goto fail;
    }
    profile_data[i++] = {
      .addr = first->addr,
      .instidx_1 = first->inst_idx,
      .op_1 = first->opcode,
      .instidx_2 = second->inst_idx,
      .op_2 = second->opcode
    };
    //printf("Instructions (%-8u, %-8u) at Addr [%-10u]  --> [%-22s, %-22s] | %d %d\n", 
    //        first->inst_idx, second->inst_idx, 
    //        first->addr,
    //        opcode_access[first->opcode].mnemonic, opcode_access[second->opcode].mnemonic,
    //        first->tid == second->tid,
    //        first->addr != second->addr);
  }

  #endif

  printf("Generated outbuf -- Size: %d\n", buf_size);

  return buf_size;

fail:
  return -1;
}




/* WAMR Native Exports Registration Hook */
NativeSymbol native_access_symbols[] = {
  EXPORT_WASM_API_WITH_SIG2(logstart, "(i)"),
  EXPORT_WASM_API_WITH_SIG2(logaccess, "(iii)"),
  EXPORT_WASM_API_WITH_SIG2(logend, "()")
};

uint32_t num_native_access_symbols = sizeof(native_access_symbols) / sizeof(NativeSymbol);

