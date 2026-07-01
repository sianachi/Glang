#include "glang_runtime.h"
#include <ctype.h>
#include <time.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <dirent.h>
#include <poll.h>
#include <termios.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>

/* ── Globals ──────────────────────────────────────────────────────────── */
int    glang_argc = 0;
char** glang_argv = NULL;
GlangExcFrame* __glang_exc_top = NULL;

/* ── Time ──────────────────────────────────────────────────────────────── */
/* A monotonic clock in nanoseconds (for durations/benchmarks) and a wall clock
   in milliseconds since the Unix epoch, plus a millisecond sleep. */
int64_t glang_now_nanos(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000000000LL + (int64_t)ts.tv_nsec;
}

int64_t glang_wall_millis(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (int64_t)ts.tv_sec * 1000LL + (int64_t)ts.tv_nsec / 1000000LL;
}

void glang_sleep_ms(int64_t ms) {
    if (ms <= 0) return;
    struct timespec ts;
    ts.tv_sec = (time_t)(ms / 1000);
    ts.tv_nsec = (long)((ms % 1000) * 1000000L);
    nanosleep(&ts, NULL);
}

/* ── TCP sockets ───────────────────────────────────────────────────────────
   BSD sockets for an event-loop HTTP server / reverse proxy. File descriptors
   are plain ints. Calls return -1 on error; the errno is stashed in
   glang_net_errno so callers can distinguish would-block from a real failure
   (glang_net_would_block). Sockets can be made non-blocking and multiplexed
   with glang_net_poll. The interpreters back the same builtins with a
   deterministic in-memory loopback instead of real networking. */

int glang_net_errno = 0;   /* errno from the most recent net call */

/* SIGPIPE would kill the process when writing to a peer that hung up. Ignore it
   once, lazily, so a closed connection surfaces as an EPIPE return instead. */
static void glang_net_ignore_sigpipe(void) {
    static int done = 0;
    if (!done) { signal(SIGPIPE, SIG_IGN); done = 1; }
}

/* MSG_NOSIGNAL (Linux) suppresses SIGPIPE per-send; macOS lacks it and relies on
   the SO_NOSIGPIPE socket option set at creation plus the global ignore above. */
#ifndef MSG_NOSIGNAL
#define MSG_NOSIGNAL 0
#endif

static void glang_net_set_nosigpipe(int fd) {
#ifdef SO_NOSIGPIPE
    int yes = 1;
    setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &yes, sizeof(yes));
#else
    (void)fd;
#endif
}

int64_t glang_net_listen(int64_t port) {
    glang_net_ignore_sigpipe();
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) { glang_net_errno = errno; return -1; }
    int yes = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons((unsigned short)port);
    if (bind(fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) { glang_net_errno = errno; close(fd); return -1; }
    if (listen(fd, 128) < 0) { glang_net_errno = errno; close(fd); return -1; }
    return fd;
}

int64_t glang_net_local_port(int64_t fd) {
    struct sockaddr_in addr;
    socklen_t len = sizeof(addr);
    if (getsockname((int)fd, (struct sockaddr*)&addr, &len) < 0) { glang_net_errno = errno; return -1; }
    return (int64_t)ntohs(addr.sin_port);
}

int64_t glang_net_accept(int64_t fd) {
    int c = accept((int)fd, NULL, NULL);
    if (c < 0) { glang_net_errno = errno; return -1; }
    glang_net_set_nosigpipe(c);
    return (int64_t)c;
}

/* Resolve host:port and return a connected socket, or one whose connect is in
   progress when `nonblock` is set (check completion with glang_net_sock_error
   once the fd reports writable). */
static int64_t glang_net_connect_impl(const char* host, int64_t port, int nonblock) {
    glang_net_ignore_sigpipe();
    char portstr[16];
    snprintf(portstr, sizeof(portstr), "%d", (int)port);
    struct addrinfo hints, *res = NULL;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    int gai = getaddrinfo(host ? host : "127.0.0.1", portstr, &hints, &res);
    if (gai != 0) { glang_net_errno = errno ? errno : EHOSTUNREACH; return -1; }
    int fd = -1;
    for (struct addrinfo* ai = res; ai != NULL; ai = ai->ai_next) {
        fd = socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol);
        if (fd < 0) { glang_net_errno = errno; continue; }
        glang_net_set_nosigpipe(fd);
        if (nonblock) {
            int fl = fcntl(fd, F_GETFL, 0);
            fcntl(fd, F_SETFL, fl | O_NONBLOCK);
            int rc = connect(fd, ai->ai_addr, ai->ai_addrlen);
            if (rc == 0 || errno == EINPROGRESS) break;   /* connecting */
            glang_net_errno = errno; close(fd); fd = -1;
        } else {
            if (connect(fd, ai->ai_addr, ai->ai_addrlen) == 0) break;
            glang_net_errno = errno; close(fd); fd = -1;
        }
    }
    freeaddrinfo(res);
    return (int64_t)fd;
}

int64_t glang_net_connect(const char* host, int64_t port) {
    return glang_net_connect_impl(host, port, 0);
}

int64_t glang_net_connect_nb(const char* host, int64_t port) {
    return glang_net_connect_impl(host, port, 1);
}

/* Receive up to `max` bytes into `buf`; returns bytes read (0 = peer closed,
   -1 = error/would-block — inspect glang_net_would_block). */
int64_t glang_net_recv(int64_t fd, uint8_t* buf, int64_t max) {
    if (max <= 0) return 0;
    ssize_t n = recv((int)fd, buf, (size_t)max, 0);
    if (n < 0) { glang_net_errno = errno; return -1; }
    return (int64_t)n;
}

/* Send up to `len` bytes from `buf`; returns bytes written (may be < len on a
   non-blocking socket), or -1 (would-block / broken pipe — see errno). */
int64_t glang_net_send(int64_t fd, uint8_t* buf, int64_t len) {
    if (len <= 0) return 0;
    ssize_t n = send((int)fd, buf, (size_t)len, MSG_NOSIGNAL);
    if (n < 0) { glang_net_errno = errno; return -1; }
    return (int64_t)n;
}

void glang_net_close(int64_t fd) {
    close((int)fd);
}

/* Put a socket into non-blocking mode (0 ok, -1 error). */
int64_t glang_net_set_nonblocking(int64_t fd) {
    int fl = fcntl((int)fd, F_GETFL, 0);
    if (fl < 0) { glang_net_errno = errno; return -1; }
    if (fcntl((int)fd, F_SETFL, fl | O_NONBLOCK) < 0) { glang_net_errno = errno; return -1; }
    return 0;
}

/* Disable Nagle's algorithm for lower latency (0 ok, -1 error). */
int64_t glang_net_set_nodelay(int64_t fd) {
    int yes = 1;
    if (setsockopt((int)fd, IPPROTO_TCP, TCP_NODELAY, &yes, sizeof(yes)) < 0) {
        glang_net_errno = errno; return -1;
    }
    return 0;
}

/* Half-close: how 0=read, 1=write, 2=both (0 ok, -1 error). */
int64_t glang_net_shutdown(int64_t fd, int64_t how) {
    int h = how == 0 ? SHUT_RD : (how == 1 ? SHUT_WR : SHUT_RDWR);
    if (shutdown((int)fd, h) < 0) { glang_net_errno = errno; return -1; }
    return 0;
}

/* Pending socket error via SO_ERROR (0 = connected/clean), used to finish a
   non-blocking connect once the fd reports writable. */
int64_t glang_net_sock_error(int64_t fd) {
    int err = 0; socklen_t len = sizeof(err);
    if (getsockopt((int)fd, SOL_SOCKET, SO_ERROR, &err, &len) < 0) { glang_net_errno = errno; return -1; }
    return (int64_t)err;
}

int64_t glang_net_last_errno(void) { return (int64_t)glang_net_errno; }

/* Was the last net call a would-block (the socket is non-blocking and has no
   data / cannot send right now)? */
int64_t glang_net_would_block(void) {
    return (glang_net_errno == EAGAIN || glang_net_errno == EWOULDBLOCK
            || glang_net_errno == EINPROGRESS) ? 1 : 0;
}

/* Multiplex `count` fds. events[i]/revents[i] are bitmasks: 1=read, 2=write,
   4=error. Waits up to timeoutMs (-1 = forever). Returns the number of fds with
   a non-zero revents, or -1 on error. */
int64_t glang_net_poll(int64_t* fds, int64_t* events, int64_t* revents,
                       int64_t count, int64_t timeout_ms) {
    if (count <= 0) return 0;
    struct pollfd* pfds = (struct pollfd*)calloc((size_t)count, sizeof(struct pollfd));
    if (!pfds) { glang_net_errno = ENOMEM; return -1; }
    for (int64_t i = 0; i < count; ++i) {
        pfds[i].fd = (int)fds[i];
        short ev = 0;
        if (events[i] & 1) ev |= POLLIN;
        if (events[i] & 2) ev |= POLLOUT;
        pfds[i].events = ev;
    }
    int rc = poll(pfds, (nfds_t)count, (int)timeout_ms);
    if (rc < 0) { glang_net_errno = errno; free(pfds); return -1; }
    int64_t ready = 0;
    for (int64_t i = 0; i < count; ++i) {
        int64_t r = 0;
        if (pfds[i].revents & POLLIN)  r |= 1;
        if (pfds[i].revents & POLLOUT) r |= 2;
        if (pfds[i].revents & (POLLERR | POLLHUP | POLLNVAL)) r |= 4;
        revents[i] = r;
        if (r) ready++;
    }
    free(pfds);
    return ready;
}

/* ── Managed memory (GC) ──────────────────────────────────────────────────
   A tracked allocate-and-sweep-at-exit collector for `managed class` instances.
   Every managed object is recorded here; the registry is freed once at program
   exit, so managed objects are reclaimed without any explicit `delete`. */
static void**  glang_managed_objs = NULL;
static size_t  glang_managed_count = 0;
static size_t  glang_managed_cap = 0;
static int     glang_managed_atexit_set = 0;

void glang_managed_sweep(void) {
    for (size_t i = 0; i < glang_managed_count; ++i) {
        free(glang_managed_objs[i]);
        glang_managed_objs[i] = NULL;
    }
    free(glang_managed_objs);
    glang_managed_objs = NULL;
    glang_managed_count = 0;
    glang_managed_cap = 0;
}

/* ── Debug allocator ──────────────────────────────────────────────────────
   When GLANG_DEBUG_ALLOC is set (to anything but "" or "0"), raw alloc()/free()
   are routed through these wrappers, which record every live block to detect
   leaks (reported once at exit) and double/invalid frees. When the variable is
   unset they passthrough to malloc/calloc/free, so normal output is unchanged.
   This is a compiled-path diagnostic: the interpreters already reject
   double-free and use-after-free at runtime, and never leak under host GC. */
static int     glang_dbg_mode = -1;     /* -1 = not yet probed, 0 = off, 1 = on */
static void**  glang_dbg_ptrs = NULL;
static size_t  glang_dbg_count = 0;
static size_t  glang_dbg_cap = 0;
static long    glang_dbg_allocs = 0;
static long    glang_dbg_frees = 0;
static long    glang_dbg_bad_frees = 0;

static void glang_dbg_report(void) {
    if (glang_dbg_count > 0) {
        fprintf(stderr, "glang: %zu leaked allocation(s)\n", glang_dbg_count);
    }
    if (glang_dbg_bad_frees > 0) {
        fprintf(stderr, "glang: %ld invalid free(s)\n", glang_dbg_bad_frees);
    }
    free(glang_dbg_ptrs);
    glang_dbg_ptrs = NULL;
}

static int glang_dbg_on(void) {
    if (glang_dbg_mode < 0) {
        const char* e = getenv("GLANG_DEBUG_ALLOC");
        glang_dbg_mode = (e && e[0] != '\0' && !(e[0] == '0' && e[1] == '\0')) ? 1 : 0;
        if (glang_dbg_mode) { atexit(glang_dbg_report); }
    }
    return glang_dbg_mode;
}

static void glang_dbg_track(void* p) {
    if (!p) return;
    if (glang_dbg_count == glang_dbg_cap) {
        size_t ncap = glang_dbg_cap == 0 ? 64 : glang_dbg_cap * 2;
        glang_dbg_ptrs = (void**)realloc(glang_dbg_ptrs, ncap * sizeof(void*));
        glang_dbg_cap = ncap;
    }
    glang_dbg_ptrs[glang_dbg_count++] = p;
    glang_dbg_allocs++;
}

static int glang_dbg_untrack(void* p) {
    for (size_t i = 0; i < glang_dbg_count; ++i) {
        if (glang_dbg_ptrs[i] == p) {
            glang_dbg_ptrs[i] = glang_dbg_ptrs[--glang_dbg_count];
            glang_dbg_frees++;
            return 1;
        }
    }
    return 0;  /* not a live tracked block: double or invalid free */
}

void* glang_alloc(size_t size) {
    void* p = malloc(size);
    if (glang_dbg_on()) { glang_dbg_track(p); }
    return p;
}

void* glang_alloc_n(size_t count, size_t size) {
    void* p = calloc(count, size);
    if (glang_dbg_on()) { glang_dbg_track(p); }
    return p;
}

void glang_free(void* p) {
    if (glang_dbg_on() && p) {
        if (!glang_dbg_untrack(p)) {
            glang_dbg_bad_frees++;
            fprintf(stderr, "glang: invalid or double free\n");
            return;  /* don't pass a bad pointer to free() */
        }
    }
    free(p);
}

/* ── Sanitizer (compile with GLANG_SANITIZE=1) ──────────────────────────────
   A size-aware allocation registry so the emitted code can bounds-check every
   index into an alloc'd block and detect use-after-free / double-free. Entries
   are kept (marked dead on free) so a freed block still reports UAF. Pointers
   not produced by the checked alloc paths (foreign/string blocks) pass through
   unchecked. Off by default: only the *_checked functions consult it, and those
   are emitted only under GLANG_SANITIZE. */
typedef struct { char* base; size_t size; int live; } GlangSanBlock;
static GlangSanBlock* glang_san = NULL;
static size_t glang_san_len = 0, glang_san_cap = 0;

static void glang_san_register(void* p, size_t size) {
    if (!p) return;
    if (glang_san_len == glang_san_cap) {
        glang_san_cap = glang_san_cap ? glang_san_cap * 2 : 128;
        glang_san = (GlangSanBlock*)realloc(glang_san, glang_san_cap * sizeof(GlangSanBlock));
    }
    glang_san[glang_san_len].base = (char*)p;
    glang_san[glang_san_len].size = size;
    glang_san[glang_san_len].live = 1;
    glang_san_len++;
}

/* Index of the block whose range contains addr, or -1. */
static long glang_san_find(void* addr) {
    char* a = (char*)addr;
    for (long i = (long)glang_san_len - 1; i >= 0; --i) {
        if (a >= glang_san[i].base && a < glang_san[i].base + glang_san[i].size) return i;
    }
    return -1;
}

void* glang_alloc_checked(size_t size) {
    void* p = glang_alloc(size);
    glang_san_register(p, size);
    return p;
}
void* glang_alloc_n_checked(size_t count, size_t elem) {
    void* p = glang_alloc_n(count, elem);
    glang_san_register(p, count * elem);
    return p;
}

void* glang_checked_index(void* p, int64_t i, size_t elem) {
    long b = glang_san_find(p);
    char* target = (char*)p + i * (int64_t)elem;
    if (b >= 0) {
        if (!glang_san[b].live) {
            fprintf(stderr, "glang: use-after-free (index into freed block)\n");
            abort();
        }
        char* base = glang_san[b].base;
        if (target < base || target + elem > base + glang_san[b].size) {
            fprintf(stderr, "glang: index %lld out of bounds\n", (long long)i);
            abort();
        }
    }
    return target;
}

void glang_free_checked(void* p) {
    if (!p) return;
    for (long i = (long)glang_san_len - 1; i >= 0; --i) {
        if (glang_san[i].base == (char*)p) {
            if (!glang_san[i].live) {
                fprintf(stderr, "glang: double free\n");
                abort();
            }
            glang_san[i].live = 0;
            glang_free(p);
            return;
        }
    }
    glang_free(p);   /* untracked (foreign block) */
}

void* glang_managed_alloc(size_t size) {
    if (!glang_managed_atexit_set) {
        atexit(glang_managed_sweep);
        glang_managed_atexit_set = 1;
    }
    void* obj = calloc(1, size);
    if (!obj) { fprintf(stderr, "glang: out of memory (managed)\n"); exit(1); }
    if (glang_managed_count == glang_managed_cap) {
        size_t ncap = glang_managed_cap == 0 ? 64 : glang_managed_cap * 2;
        glang_managed_objs = (void**)realloc(glang_managed_objs, ncap * sizeof(void*));
        if (!glang_managed_objs) { fprintf(stderr, "glang: out of memory (managed registry)\n"); exit(1); }
        glang_managed_cap = ncap;
    }
    glang_managed_objs[glang_managed_count++] = obj;
    return obj;
}

/* ── String operations ────────────────────────────────────────────────── */

char* glang_str_concat(const char* a, const char* b) {
    if (!a) a = "";
    if (!b) b = "";
    size_t la = strlen(a), lb = strlen(b);
    char* out = (char*)malloc(la + lb + 1);
    memcpy(out, a, la);
    memcpy(out + la, b, lb + 1);
    return out;
}

char* glang_str_substr(const char* s, int64_t start, int64_t end) {
    if (!s) return strdup("");
    int64_t n = (int64_t)strlen(s);
    if (start < 0) start = 0;
    if (end > n)   end = n;
    if (start > end) start = end;
    size_t len = (size_t)(end - start);
    char* out = (char*)malloc(len + 1);
    memcpy(out, s + start, len);
    out[len] = '\0';
    return out;
}

int64_t glang_str_len(const char* s) {
    return s ? (int64_t)strlen(s) : 0;
}

int64_t glang_indexof_str(const char* s, const char* needle) {
    if (!s || !needle) return -1;
    const char* p = strstr(s, needle);
    return p ? (int64_t)(p - s) : -1;
}

int glang_startswith(const char* s, const char* prefix) {
    if (!s || !prefix) return 0;
    size_t lp = strlen(prefix);
    return strncmp(s, prefix, lp) == 0;
}

int glang_endswith(const char* s, const char* suffix) {
    if (!s || !suffix) return 0;
    size_t ls = strlen(s), lf = strlen(suffix);
    if (lf > ls) return 0;
    return strcmp(s + ls - lf, suffix) == 0;
}

int glang_strcontains(const char* s, const char* needle) {
    if (!s || !needle) return 0;
    return strstr(s, needle) != NULL;
}

char* glang_inttostr(int64_t n) {
    char buf[32];
    snprintf(buf, sizeof(buf), "%" PRId64, n);
    return strdup(buf);
}

char* glang_floattostr(double f) {
    char buf[64];
    /* %.15g: up to 15 significant digits, trailing zeros trimmed. Note this
       renders whole values without a fractional part ("9", not "9.0"). */
    snprintf(buf, sizeof(buf), "%.15g", f);
    return strdup(buf);
}

char* glang_chartostr(char c) {
    char buf[2] = { c, '\0' };
    return strdup(buf);
}

char* glang_booltostr(int b) {
    return strdup(b ? "true" : "false");
}

int64_t glang_parseint(const char* s) {
    if (!s) return 0;
    /* Support 0x hex prefix */
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X'))
        return (int64_t)strtoll(s, NULL, 16);
    return (int64_t)strtoll(s, NULL, 10);
}

double glang_parsefloat(const char* s) {
    if (!s) return 0.0;
    return strtod(s, NULL);
}

char* glang_readfile(const char* path) {
    FILE* f = fopen(path, "rb");
    if (!f) return strdup("");
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    char* buf = (char*)malloc((size_t)sz + 1);
    fread(buf, 1, (size_t)sz, f);
    buf[sz] = '\0';
    fclose(f);
    return buf;
}

void glang_writefile(const char* path, const char* content) {
    FILE* f = fopen(path, "wb");
    if (!f) { fprintf(stderr, "glang: cannot write '%s'\n", path); return; }
    fputs(content ? content : "", f);
    fclose(f);
}

char* glang_appendfile(const char* path, const char* content) {
    FILE* f = fopen(path, "ab");
    if (!f) { fprintf(stderr, "glang: cannot append '%s'\n", path); return strdup(""); }
    fputs(content ? content : "", f);
    fclose(f);
    return strdup("");
}

int glang_fileexists(const char* path) {
    FILE* f = fopen(path, "rb");
    if (f) { fclose(f); return 1; }
    return 0;
}

/* ── Binary-safe file I/O ──────────────────────────────────────────────────
   readFile/writeFile go through char* (NUL-terminated), so they truncate binary
   data. These move raw bytes through a caller-provided buffer instead, so images,
   fonts, uploads, etc. round-trip intact. */

/* Byte length of a file, or -1 if it can't be opened. */
int64_t glang_filesize(const char* path) {
    FILE* f = fopen(path, "rb");
    if (!f) return -1;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return -1; }
    long sz = ftell(f);
    fclose(f);
    return (int64_t)sz;
}

/* Read up to `cap` bytes of `path` into `buf`; returns bytes read, or -1. */
int64_t glang_readfile_into(const char* path, uint8_t* buf, int64_t cap) {
    if (!buf || cap <= 0) return 0;
    FILE* f = fopen(path, "rb");
    if (!f) return -1;
    size_t n = fread(buf, 1, (size_t)cap, f);
    fclose(f);
    return (int64_t)n;
}

/* Write `len` bytes of `buf` to `path` (truncating it); returns bytes written,
   or -1 on error. */
int64_t glang_writefile_from(const char* path, uint8_t* buf, int64_t len) {
    if (len < 0) return -1;
    FILE* f = fopen(path, "wb");
    if (!f) return -1;
    size_t n = (len == 0 || !buf) ? 0 : fwrite(buf, 1, (size_t)len, f);
    int ok = (fclose(f) == 0);
    if (!ok) return -1;
    return (int64_t)n;
}

static int glang_strcmp_qsort(const void* a, const void* b) {
    return strcmp(*(const char* const*)a, *(const char* const*)b);
}

/* Newline-separated directory entry names (excluding . and ..), sorted for a
   deterministic result that matches the interpreters. "" on error. Caller owns
   the returned string. */
char* glang_listdir(const char* path) {
    DIR* d = opendir(path);
    if (!d) return strdup("");
    size_t ncap = 16, n = 0;
    char** names = (char**)malloc(ncap * sizeof(char*));
    struct dirent* ent;
    while ((ent = readdir(d)) != NULL) {
        const char* name = ent->d_name;
        if (name[0] == '.' && (name[1] == '\0' ||
            (name[1] == '.' && name[2] == '\0'))) { continue; }
        if (n == ncap) { ncap *= 2; names = (char**)realloc(names, ncap * sizeof(char*)); }
        names[n++] = strdup(name);
    }
    closedir(d);
    qsort(names, n, sizeof(char*), glang_strcmp_qsort);

    size_t cap = 256, used = 0;
    char* out = (char*)malloc(cap);
    out[0] = '\0';
    for (size_t i = 0; i < n; ++i) {
        size_t nl = strlen(names[i]);
        if (used + nl + 2 > cap) {
            while (used + nl + 2 > cap) { cap *= 2; }
            out = (char*)realloc(out, cap);
        }
        memcpy(out + used, names[i], nl);
        used += nl;
        out[used++] = '\n';
        out[used] = '\0';
        free(names[i]);
    }
    free(names);
    return out;
}

char* glang_readstdin(void) {
    size_t cap = 4096, used = 0;
    char* buf = (char*)malloc(cap);
    int c;
    while ((c = getchar()) != EOF) {
        if (used + 1 >= cap) { cap *= 2; buf = (char*)realloc(buf, cap); }
        buf[used++] = (char)c;
    }
    buf[used] = '\0';
    return buf;
}

/* Read one byte from stdin, or -1 at EOF. Lets a server frame messages by
   exact byte count without waiting for EOF (cf. glang_readstdin). */
int64_t glang_readbyte(void) {
    int c = getchar();
    return c == EOF ? -1 : (int64_t)c;
}

/* Write a string to stdout with no trailing newline, then flush. The print
   builtins all append '\n', which corrupts length-prefixed wire protocols. */
void glang_writestdout(const char* v) {
    if (v) { fputs(v, stdout); }
    fflush(stdout);
}

/* ── Terminal control (raw mode, size, timed input) ─────────────────────────
   Primitives for building TUIs. Raw mode disables canonical line-editing and
   echo so a program sees each keystroke immediately; the original settings are
   saved and restored on termRawOff and — defensively — via atexit(), so a plain
   exit() or a return from main() never leaves the user's shell in raw mode.
   SIGWINCH (resize) and SIGINT are caught into flags the program polls, rather
   than acted on directly, so the app loop stays in control of when to redraw or
   quit. In raw mode Ctrl-C arrives as the byte 0x03 (ISIG is off); the SIGINT
   flag then only reflects an external `kill -INT`. */

static struct termios          glang_term_saved;
static int                     glang_term_raw_active = 0;
static volatile sig_atomic_t   glang_term_winch = 0;
static volatile sig_atomic_t   glang_term_intr  = 0;

static void glang_term_restore(void) {
    if (glang_term_raw_active) {
        tcsetattr(STDIN_FILENO, TCSAFLUSH, &glang_term_saved);
        glang_term_raw_active = 0;
    }
}
static void glang_term_on_winch(int sig) { (void)sig; glang_term_winch = 1; }
static void glang_term_on_intr(int sig)  { (void)sig; glang_term_intr  = 1; }

/* Enter raw mode. Returns 0 on success, -1 if stdin is not a terminal or a
   termios call fails. The first successful call saves the original settings,
   registers the atexit restore, and installs the SIGWINCH/SIGINT handlers. */
int64_t glang_term_raw_on(void) {
    struct termios raw;
    if (!isatty(STDIN_FILENO)) return -1;
    if (tcgetattr(STDIN_FILENO, &raw) != 0) return -1;
    if (!glang_term_raw_active) {
        glang_term_saved = raw;
        atexit(glang_term_restore);
        struct sigaction sa;
        memset(&sa, 0, sizeof(sa));
        sa.sa_handler = glang_term_on_winch;
        sigaction(SIGWINCH, &sa, NULL);
        sa.sa_handler = glang_term_on_intr;
        sigaction(SIGINT, &sa, NULL);
    }
    raw.c_lflag &= ~(tcflag_t)(ECHO | ICANON | ISIG | IEXTEN);
    raw.c_iflag &= ~(tcflag_t)(IXON | ICRNL | BRKINT | INPCK | ISTRIP);
    raw.c_oflag &= ~(tcflag_t)(OPOST);
    raw.c_cflag |=  (tcflag_t)(CS8);
    raw.c_cc[VMIN]  = 0;   /* read returns immediately; we gate on poll() */
    raw.c_cc[VTIME] = 0;
    if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw) != 0) return -1;
    glang_term_raw_active = 1;
    return 0;
}

/* Leave raw mode (restore saved settings). Returns 0. Safe if never entered. */
int64_t glang_term_raw_off(void) {
    glang_term_restore();
    return 0;
}

/* Terminal width (columns) / height (rows), or -1 if not a sized terminal. */
int64_t glang_term_width(void) {
    struct winsize ws;
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) != 0 || ws.ws_col == 0) return -1;
    return (int64_t)ws.ws_col;
}
int64_t glang_term_height(void) {
    struct winsize ws;
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) != 0 || ws.ws_row == 0) return -1;
    return (int64_t)ws.ws_row;
}

/* Read one byte from stdin, waiting at most `ms` milliseconds (ms < 0 blocks).
   Returns the byte (0..255), -1 at EOF, or -2 on timeout or EINTR so the caller
   can re-check the resize/interrupt flags between polls. */
int64_t glang_read_byte_timeout(int64_t ms) {
    struct pollfd pfd;
    pfd.fd = STDIN_FILENO;
    pfd.events = POLLIN;
    int r = poll(&pfd, 1, (ms < 0) ? -1 : (int)ms);
    if (r <= 0) return -2;                 /* timeout, EINTR, or poll error */
    unsigned char b;
    ssize_t n = read(STDIN_FILENO, &b, 1);
    if (n <= 0) return -1;                 /* EOF */
    return (int64_t)b;
}

/* Return-and-clear the SIGWINCH / SIGINT flags (1 if the signal arrived since
   the last call, else 0). GLang-typed as bool. */
int64_t glang_term_resized(void) {
    if (glang_term_winch) { glang_term_winch = 0; return 1; }
    return 0;
}
int64_t glang_term_interrupted(void) {
    if (glang_term_intr) { glang_term_intr = 0; return 1; }
    return 0;
}

/* ── Shell ────────────────────────────────────────────────────────────────
   Run `cmd` via /bin/sh, capture its stdout, and return it as a heap string
   (empty on failure). Intended for local system-introspection tools (reading
   netstat/ifconfig/route output). The interpreters back this the same way. */
char* glang_shell(const char* cmd) {
    if (!cmd) { return strdup(""); }
    FILE* p = popen(cmd, "r");
    if (!p) { return strdup(""); }
    size_t cap = 4096, used = 0;
    char* buf = (char*)malloc(cap);
    char chunk[4096];
    size_t n;
    while ((n = fread(chunk, 1, sizeof(chunk), p)) > 0) {
        if (used + n + 1 > cap) {
            while (used + n + 1 > cap) { cap *= 2; }
            buf = (char*)realloc(buf, cap);
        }
        memcpy(buf + used, chunk, n);
        used += n;
    }
    buf[used] = '\0';
    pclose(p);
    return buf;
}

/* ── Filesystem & environment ───────────────────────────────────────────── */

/* Value of environment variable `name`, or "" if unset. */
char* glang_getenv(const char* name) {
    const char* v = name ? getenv(name) : NULL;
    return strdup(v ? v : "");
}

/* Delete a file. Returns 1 on success, 0 on failure. */
int64_t glang_remove_file(const char* path) {
    return (path && remove(path) == 0) ? 1 : 0;
}

/* Create a directory (mode 0755). Returns 1 on success, 0 on failure. */
int64_t glang_make_dir(const char* path) {
    return (path && mkdir(path, 0755) == 0) ? 1 : 0;
}

/* Rename/move a path. Returns 1 on success, 0 on failure. */
int64_t glang_rename_file(const char* from, const char* to) {
    return (from && to && rename(from, to) == 0) ? 1 : 0;
}

/* True (1) if `path` exists and is a directory. */
int64_t glang_is_dir(const char* path) {
    struct stat st;
    if (!path || stat(path, &st) != 0) { return 0; }
    return S_ISDIR(st.st_mode) ? 1 : 0;
}

/* ── Print ────────────────────────────────────────────────────────────── */

void glang_print_int(int64_t v)       { printf("%" PRId64 "\n", v); }
void glang_print_uint(uint64_t v)     { printf("%" PRIu64 "\n", v); }
void glang_print_float(double v)      {
    /* Single source of truth for float formatting: glang_floattostr. */
    char* s = glang_floattostr(v);
    printf("%s\n", s);
    free(s);
}
void glang_print_bool(int v)          { printf("%s\n", v ? "true" : "false"); }
void glang_print_char(char v)         { printf("%c\n", v); }
void glang_print_string(const char* v){ printf("%s\n", v ? v : "null"); }

void glang_printerr_int(int64_t v)       { fprintf(stderr, "%" PRId64 "\n", v); }
void glang_printerr_uint(uint64_t v)     { fprintf(stderr, "%" PRIu64 "\n", v); }
void glang_printerr_float(double v)      { char* s = glang_floattostr(v); fprintf(stderr, "%s\n", s); free(s); }
void glang_printerr_bool(int v)          { fprintf(stderr, "%s\n", v ? "true" : "false"); }
void glang_printerr_char(char v)         { fprintf(stderr, "%c\n", v); }
void glang_printerr_string(const char* v){ fprintf(stderr, "%s\n", v ? v : "null"); }

/* ── toString ─────────────────────────────────────────────────────────── */

char* glang_tostring_int(int64_t v)    { return glang_inttostr(v); }
char* glang_tostring_uint(uint64_t v)  {
    char buf[32]; snprintf(buf, sizeof(buf), "%" PRIu64, v); return strdup(buf);
}
char* glang_tostring_float(double v)   { return glang_floattostr(v); }
char* glang_tostring_bool(int v)       { return glang_booltostr(v); }
char* glang_tostring_char(char v)      { return glang_chartostr(v); }
char* glang_tostring_string(const char* v) { return v ? strdup(v) : strdup("null"); }

/* ── Exceptions ───────────────────────────────────────────────────────── */

void glang_throw(void* obj, const char* class_name) {
    if (__glang_exc_top == NULL) {
        fprintf(stderr, "Unhandled exception: %s\n",
                class_name ? class_name : "unknown");
        exit(1);
    }
    __glang_exc_top->obj = obj;
    __glang_exc_top->class_name = class_name ? class_name : "Exception";
    longjmp(__glang_exc_top->env, 1);
}

int glang_instanceof(const char* actual, const char* target,
                     const char** hier, int hier_len) {
    /* Walk up the hierarchy table from 'actual' until we reach 'target'
       or exhaust the chain. */
    if (!actual || !target) return 0;
    const char* cur = actual;
    while (cur) {
        if (strcmp(cur, target) == 0) return 1;
        /* Find parent in table */
        const char* parent = NULL;
        for (int i = 0; i < hier_len; i += 2) {
            if (strcmp(hier[i], cur) == 0) { parent = hier[i+1]; break; }
        }
        if (!parent || strcmp(parent, "") == 0) break;
        cur = parent;
    }
    return 0;
}
