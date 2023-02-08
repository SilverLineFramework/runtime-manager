/**
 * @addtogroup deadline
 * @{
 * @file deadline/deadline.c
 * @brief `sched_deadline` configuration
 */

#include <stdint.h>
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>

#include "logging.h"

#include "deadline.h"

/**
 * @brief Set scheduler attributes (scheduler class, period
 * @note Flags is for future extensions, currently set it to 0 always
 * @param pid Process ID to  Module manager to initialize
 * @param flags For future extensions only, currently set it to 0 always
 * @return Success indicator
 */
int sched_setattr(pid_t pid, const sched_attr_t *attr, unsigned int flags) {
    return syscall(__NR_sched_setattr, pid, attr, flags);
}

/**
 * @brief Set scheduler attributes (scheduler class, period
 * @param pid Process ID of task to set attributes (returned by pthread_create)
 * @param attr Desired scheduler attributes
 * @param flags For future extensions only, currently set it to 0 always
 * @return Success indicator
 */
int sched_getattr(
        pid_t pid, const sched_attr_t *attr,
        unsigned int size, unsigned int flags) {
    return syscall(__NR_sched_setattr, pid, attr, size, flags);
}

/**
 * @brief Issue command on system.
 */
static void system_command (char* cmd) {
    char *line = NULL;
    ssize_t nread;
    size_t len;

    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        log_msg(LOG_ERROR, "ERROR: Could not create pipe for \'%s\' \n", cmd);
    } else {
        while((nread = getline(&line, &len, fp)) != -1) {
            log_msg(LOG_ERROR, "%s", line);
        }
        free(line);
    }
    pclose(fp);
}

/**
 * @brief Set scheduling params; always successful
 * @note `sched_deadline` is not supported on WSL.
 */
bool sched_apply(sched_attr_t *attr) {
    char command[100];
    int pid = gettid();

    // Move to CFS cpuset
    if (attr->sched_policy == SCHED_OTHER) {
        log_msg(LOG_MODULES, LOG_INFO, "Scheduler Class: CFS\n");
        sprintf(
            command,
            "(echo %d > /sys/fs/cgroup/cpuset/cfs-partition/tasks) 2>&1", pid);
        system_command(command);
    }
    // Move to RT cpuset
    else {
        uint32_t util = (attr->sched_runtime * 100) / attr->sched_period;
        log_msg(LOG_INFO, "Scheduler Class: SCHED_DEADLINE\n");
        log_msg(
            LOG_INFO, "sched_deadline: utilization=%d%% runtime=%llu \n",
            util, attr->sched_runtime);
        sprintf(
            command,
            "(echo %d > /sys/fs/cgroup/cpuset/rt-partition/tasks) 2>&1", pid);

        // Note: Cpuset assignment must be performed before setting real-time
        // attributes
        system_command(command);
        if (sched_setattr(0, (const sched_attr_t *) attr, 0) < 0) {
            log_msg(LOG_ERROR, "sched_setattr %s\n", strerror(errno));
            return false;
        }
    }
    return true;
}


/**
 * @brief Clear scheduling and return to root cpuset.
 */
void sched_clear() {
    int pid = gettid();

    sched_attr_t attr;
    attr.size = sizeof(attr);
    attr.sched_flags = 0;
    attr.sched_nice = 0;
    attr.sched_priority = 0;
    attr.sched_policy = SCHED_OTHER;
    attr.sched_runtime = 0;
    attr.sched_deadline = 0;
    attr.sched_period = 0;
    if (sched_setattr(pid, (const sched_attr_t *) &attr, 0) < 0) {
        log_msg(LOG_ERROR, "sched_setattr %s\n", strerror(errno));
    }
}

/** @} */
