/*
 * resident-memory.c — commit a resident anonymous-memory footprint, then idle.
 *
 * This intentionally touches each page once and does no continuous work. It
 * approximates a resident footprint, not a Metal/wired/model allocation.
 * Stop with Ctrl-C or SIGTERM; the process then unmaps and exits cleanly.
 */
#define _DARWIN_C_SOURCE
#include <errno.h>
#include <math.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/sysctl.h>
#include <unistd.h>

static volatile sig_atomic_t stop_requested = 0;

static void request_stop(int signal_number) {
    (void)signal_number;
    stop_requested = 1;
}

static void usage(const char *program) {
    fprintf(stderr,
        "Usage: %s (--gib N | --mib N | --bytes N) [--force]\n"
        "\nCommit and touch an anonymous memory footprint, then wait.\n"
        "N may be fractional for --gib/--mib.\n"
        "By default, targets above 80%% of physical RAM are refused.\n",
        program);
}

static int parse_number(const char *text, double *value) {
    char *end = NULL;
    errno = 0;
    double parsed = strtod(text, &end);
    if (errno != 0 || end == text || *end != '\0' || !isfinite(parsed) || parsed <= 0.0) {
        return 0;
    }
    *value = parsed;
    return 1;
}

static int physical_memory_bytes(uint64_t *bytes) {
    size_t size = sizeof(*bytes);
    return sysctlbyname("hw.memsize", bytes, &size, NULL, 0) == 0;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        usage(argv[0]);
        return 2;
    }

    double value = 0.0;
    uint64_t target = 0;
    int force = 0;
    int seen_target = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--force") == 0) {
            force = 1;
            continue;
        }
        if (i + 1 >= argc || seen_target) {
            usage(argv[0]);
            return 2;
        }
        if (!parse_number(argv[i + 1], &value)) {
            fprintf(stderr, "Invalid target: %s\n", argv[i + 1]);
            return 2;
        }
        long double multiplier = 0.0L;
        if (strcmp(argv[i], "--gib") == 0) {
            multiplier = 1024.0L * 1024.0L * 1024.0L;
        } else if (strcmp(argv[i], "--mib") == 0) {
            multiplier = 1024.0L * 1024.0L;
        } else if (strcmp(argv[i], "--bytes") == 0) {
            multiplier = 1.0L;
        } else {
            usage(argv[0]);
            return 2;
        }
        long double requested = (long double)value * multiplier;
        if (requested > (long double)SIZE_MAX || requested < 1.0L) {
            fprintf(stderr, "Target is outside supported size range.\n");
            return 2;
        }
        target = (uint64_t)requested;
        seen_target = 1;
        i++;
    }

    if (!seen_target) {
        usage(argv[0]);
        return 2;
    }

    uint64_t physical = 0;
    if (!physical_memory_bytes(&physical)) {
        perror("sysctl(hw.memsize)");
        return 1;
    }
    if (!force && (long double)target > (long double)physical * 0.80L) {
        fprintf(stderr,
            "Refusing %.2f GiB: it exceeds 80%% of %.2f GiB physical RAM. "
            "Use a smaller target or --force.\n",
            (double)target / (1024.0 * 1024.0 * 1024.0),
            (double)physical / (1024.0 * 1024.0 * 1024.0));
        return 3;
    }

    long page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0) {
        perror("sysconf(_SC_PAGESIZE)");
        return 1;
    }

    struct sigaction action;
    memset(&action, 0, sizeof(action));
    action.sa_handler = request_stop;
    sigemptyset(&action.sa_mask);
    sigaction(SIGINT, &action, NULL);
    sigaction(SIGTERM, &action, NULL);
    sigaction(SIGHUP, &action, NULL);

    unsigned char *region = mmap(NULL, (size_t)target, PROT_READ | PROT_WRITE,
                                 MAP_PRIVATE | MAP_ANON, -1, 0);
    if (region == MAP_FAILED) {
        fprintf(stderr, "mmap failed for %llu bytes: %s\n",
                (unsigned long long)target, strerror(errno));
        return 1;
    }

    /* Volatile prevents the compiler from removing the commitment pass. */
    volatile unsigned char *touch = region;
    uint64_t pages = 0;
    for (uint64_t offset = 0; offset < target && !stop_requested; offset += (uint64_t)page_size) {
        touch[offset] = (unsigned char)(pages & 0xffu);
        pages++;
    }

    printf("resident-memory: pid=%d target_bytes=%llu target_gib=%.3f page_size=%ld pages_touched=%llu\n",
           getpid(), (unsigned long long)target,
           (double)target / (1024.0 * 1024.0 * 1024.0), page_size,
           (unsigned long long)pages);
    printf("resident-memory: committed and touched once; idle now; Ctrl-C or kill %d to release\n",
           getpid());
    fflush(stdout);

    while (!stop_requested) {
        pause();
    }

    if (munmap(region, (size_t)target) != 0) {
        perror("munmap");
        return 1;
    }
    printf("resident-memory: released; exiting\n");
    return 0;
}
