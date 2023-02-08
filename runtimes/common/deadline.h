/**
 * @addtogroup deadline
 * @{
 * @file common/deadline.h
 * @brief `sched_deadline` configuration
 */

#ifndef COMMON_DEADLINE_H
#define MODULES_DEADLINE_H

#include <stdbool.h>
#include <linux/unistd.h>
#include <linux/kernel.h>
#include <linux/types.h>
#include <sys/syscall.h>
#include <pthread.h>
#include <sched.h>

#define gettid() syscall(__NR_gettid)

#ifndef __NR_sched_setattr
#define __NR_sched_setattr 314
#endif

#ifndef __NR_sched_getattr
#define __NR_sched_getattr 315
#endif

/**
 * @brief Standard sched_attr_t struct
 * Specified here: https://man7.org/linux/man-pages/man2/sched_setattr.2.html
 * 
 */
typedef struct {
  __u32 size;
  __u32 sched_policy;
  __u64 sched_flags;

  /** SCHED_NORMAL, SCHED_BATCH */
  __s32 sched_nice;
  /** SCHED_FIFO, SCHED_RR */
  __u32 sched_priority;

  /** SCHED_DEADLINE params; all parameters are in nanoseconds! */
  __u64 sched_runtime;
  __u64 sched_deadline;
  __u64 sched_period;

} sched_attr_t;

#if !defined(DOXYGEN_SHOULD_SKIP_THIS)
int sched_setattr(pid_t pid, const sched_attr_t *attr, unsigned int flags);
int sched_getattr(
    pid_t pid, const sched_attr_t *attr,
    unsigned int size, unsigned int flags);
bool sched_apply(sched_attr_t *attr);
void sched_clear();
#endif

#endif
/** @} */
