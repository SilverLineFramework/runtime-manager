#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <sys/mman.h>

#include "wasm_export.h"
#include "lib_export.h"
#include "opaccess.h"
#include "access_export.h"

#include <map>
#include <set>
#include <unordered_set>
#include <mutex>
#include <vector>
#include <fstream>
#include <atomic>

#define INSTRUMENT 1
#define TRACE_ACCESS 0


typedef std::unordered_set<uint32_t> InstSet;
typedef uint8_t byte;

/* Access Logger */
typedef struct {
  uint64_t last_tid;
  InstSet inst_idxs;
  uint64_t freq;
  bool shared;
  bool write_encountered;
  std::mutex mtx;
} acc_entry;

static acc_entry *access_table = NULL;
static size_t table_size = sizeof(acc_entry) * ((size_t)1 << 32);
static uint32_t addr_min = -1;
static uint32_t addr_max = 0;

static std::mutex shared_inst_mtx;
static std::set<uint32_t> shared_inst_idxs;
/*  */

void logaccess_wrapper(wasm_exec_env_t exec_env, uint32_t addr, uint32_t opcode, uint32_t inst_idx) {
  #if INSTRUMENT == 1
  uint64_t tid = wasm_runtime_get_exec_env_uid(exec_env);
  bool is_write = (opcode_access[opcode].type == STORE);
  #if TRACE_ACCESS == 1
  printf("I: %u | A: %u | T: %lu\n", inst_idx, addr, tid);
  #endif
  acc_entry *entry = access_table + addr;

  entry->mtx.lock();
  bool new_tid_acc = (tid != entry->last_tid);
  /* First access to address: Construct instruction set */
  if (!entry->last_tid) {
    new (&entry->inst_idxs) InstSet;
    entry->inst_idxs.insert(inst_idx);
  }
  /* Shared accesses from any thread write to global set */
  else if (entry->shared) {
    shared_inst_mtx.lock();
    shared_inst_idxs.insert(inst_idx);
    shared_inst_mtx.unlock();
  }
  /* Unshared access from new thread: Mark as shared and append logged insts */
  else if (new_tid_acc) {
    entry->shared = true;
    shared_inst_mtx.lock();
    shared_inst_idxs.insert(entry->inst_idxs.begin(), entry->inst_idxs.end());
    shared_inst_idxs.insert(inst_idx);
    shared_inst_mtx.unlock();
    /* Save some memory by deleting unused set */
    entry->inst_idxs.~InstSet();
  }
  /* Unshared access from only one thread: Log inst */
  else {
    entry->inst_idxs.insert(inst_idx);
  }
  entry->last_tid = tid;
  entry->freq += 1;
  entry->write_encountered = is_write;
  entry->mtx.unlock();

  addr_min = (addr < addr_min) ? addr : addr_min;
  addr_max = (addr > addr_max) ? addr : addr_max;
  #endif
}



void logstart_wrapper(wasm_exec_env_t exec_env, uint32_t max_instructions) {}
void logend_wrapper(wasm_exec_env_t exec_env) {}

/* Initialization routine */
bool init_instrumentation_state(uint32_t max_mem) {
  table_size = (size_t)max_mem * sizeof(acc_entry);
  access_table = (acc_entry*) mmap(NULL, table_size, PROT_READ|PROT_WRITE, 
                    MAP_PRIVATE|MAP_ANONYMOUS|MAP_NORESERVE, -1, 0);
  if (access_table == MAP_FAILED) {
    perror("access table mmap error");
    return false;
  }

  shared_inst_idxs.clear();
  addr_min = -1;
  addr_max = 0;

  return true;
}

/* Destruction routine */
bool destroy_instrumentation_state() {
  int status = munmap(access_table, table_size);
  if (status == -1) {
    perror("munmap error");
    return false;
  }
  access_table = NULL;
  return true;
}

int64_t get_instrumentation_profile(char **buf_ptr, char *pre_buf, int pre_len) {
#define OB_WRITE(ptr, len)  { \
  outbuf.insert(outbuf.end(), ptr, ptr + len);  \
}

#define PWRITE(elem) {  \
  char* addr = (char*) &elem; \
  partials.insert(partials.end(), addr, addr + sizeof(elem));  \
}

#define PWRITE_FIX(ptr, sz) { \
  char* addr = (char*) ptr; \
  partials.insert(partials.end(), addr, addr + sz); \
}
  std::vector<byte> outbuf;

  OB_WRITE(pre_buf, pre_len);

  #if INSTRUMENT == 1
  std::vector<uint32_t> inst_idxs(shared_inst_idxs.begin(), shared_inst_idxs.end());

  std::vector<uint32_t> shared_addrs;
  std::vector<byte> partials;

  /* Access table dump  */
  for (uint32_t i = 0; i <= addr_max; i++) {
    acc_entry *entry = access_table + i;
    if (entry->last_tid) {
      if (entry->shared) {
        //printf("Addr [%u] | Accesses: %lu [SHARED]\n", i, entry->freq);
        shared_addrs.push_back(i);
      } else {
        //printf("Addr [%u] | Accesses: %lu\n", i, entry->freq);
        /* Write partial content */
        PWRITE (i);
        PWRITE (entry->last_tid);
        PWRITE (entry->write_encountered);
        std::vector<uint32_t> entry_idxs(entry->inst_idxs.begin(), entry->inst_idxs.end());
        uint32_t num_entry_idxs = entry_idxs.size();
        PWRITE (num_entry_idxs);
        PWRITE_FIX (entry_idxs.data(), num_entry_idxs * sizeof(uint32_t));
      }
    }
  }

  uint32_t num_inst_idxs = inst_idxs.size();
  uint32_t num_shared_addrs = shared_addrs.size();

  /* Log shared instructions */
  OB_WRITE((char*) &num_inst_idxs, sizeof(num_inst_idxs));
  OB_WRITE((char*) inst_idxs.data(), num_inst_idxs * sizeof(uint32_t));

  /* Log shared addrs */
  OB_WRITE((char*) &num_shared_addrs, sizeof(num_shared_addrs));
  OB_WRITE((char*) shared_addrs.data(), num_shared_addrs * sizeof(uint32_t));

  /* Log partial addr + idx */
  OB_WRITE((char*) partials.data(), partials.size());

  #endif

  /* Generate C array */
  int64_t buf_size = outbuf.size();
  *buf_ptr = (char*) malloc(outbuf.size());
  if (*buf_ptr == NULL) { goto fail; }
  std::copy(outbuf.begin(), outbuf.end(), *buf_ptr);

  printf("Generated outbuf -- Size: %ld\n", buf_size);

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

/* Unused */
uint32_t delay_param = 0;
