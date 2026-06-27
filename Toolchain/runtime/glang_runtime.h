#ifndef GLANG_RUNTIME_H
#define GLANG_RUNTIME_H

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <setjmp.h>
#include <math.h>

/* ── Closures / first-class functions ───────────────────────────────────── */
/* All fn(...)->... values are represented as a (fn, cap) pair. */
typedef struct { void* fn; void* cap; } GlangFn;

/* ── Bool ─────────────────────────────────────────────────────────────── */
/* Glang bool maps to int (0 = false, 1 = true) */
#ifndef true
#define true  1
#define false 0
#endif

/* ── String ───────────────────────────────────────────────────────────── */
/* MVP: Glang strings are heap-allocated null-terminated char*.
   Callers own the memory; leaks are acceptable in Phase 1. */

char* glang_str_concat(const char* a, const char* b);
char* glang_str_substr(const char* s, int64_t start, int64_t end);
int64_t glang_str_len(const char* s);
int64_t glang_indexof_str(const char* s, const char* needle);
int   glang_startswith(const char* s, const char* prefix);
int   glang_endswith(const char* s, const char* suffix);
int   glang_strcontains(const char* s, const char* needle);
char* glang_inttostr(int64_t n);
char* glang_floattostr(double f);
char* glang_chartostr(char c);
char* glang_booltostr(int b);
int64_t glang_parseint(const char* s);
double  glang_parsefloat(const char* s);
char*   glang_readfile(const char* path);
void    glang_writefile(const char* path, const char* content);
int     glang_fileexists(const char* path);
char*   glang_readstdin(void);
char*   glang_appendfile(const char* path, const char* content);

/* ── Print ────────────────────────────────────────────────────────────── */
void glang_print_int(int64_t v);
void glang_print_float(double v);
void glang_print_bool(int v);
void glang_print_char(char v);
void glang_print_string(const char* v);
void glang_printerr_int(int64_t v);
void glang_printerr_float(double v);
void glang_printerr_bool(int v);
void glang_printerr_char(char v);
void glang_printerr_string(const char* v);

/* ── toString ─────────────────────────────────────────────────────────── */
char* glang_tostring_int(int64_t v);
char* glang_tostring_float(double v);
char* glang_tostring_bool(int v);
char* glang_tostring_char(char v);
char* glang_tostring_string(const char* v);

/* ── Args ─────────────────────────────────────────────────────────────── */
extern int    glang_argc;
extern char** glang_argv;

/* ── Exceptions ───────────────────────────────────────────────────────── */
typedef struct GlangExcFrame {
    void*                  obj;
    const char*            class_name;
    jmp_buf                env;
    struct GlangExcFrame*  prev;
} GlangExcFrame;

extern GlangExcFrame* __glang_exc_top;

void glang_throw(void* obj, const char* class_name);
int  glang_instanceof(const char* actual, const char* target,
                      const char** hier, int hier_len);

/* Macro helpers for try/catch emission */
#define GLANG_TRY_BEGIN \
    { \
    GlangExcFrame __exc_frame__; \
    __exc_frame__.obj = NULL; __exc_frame__.class_name = NULL; \
    __exc_frame__.prev = __glang_exc_top; \
    __glang_exc_top = &__exc_frame__; \
    if (setjmp(__exc_frame__.env) == 0) {

#define GLANG_TRY_END \
    __glang_exc_top = __exc_frame__.prev; \
    } else { \
    __glang_exc_top = __exc_frame__.prev;

/* Each catch clause is emitted between GLANG_TRY_END and GLANG_CATCH_DONE:
       if (glang_instanceof(__exc_frame__.class_name, "T", hier, n)) { T* v = ...; ... }
       else { glang_throw(__exc_frame__.obj, __exc_frame__.class_name); }
*/
#define GLANG_CATCH_DONE \
    } }

#define GLANG_THROW(obj, cname) glang_throw((void*)(obj), (cname))

/* ── Class hierarchy table (for instanceof) ───────────────────────────── */
/* Generated code populates __glang_class_hier[] and __glang_class_hier_len */
typedef struct { const char* name; const char* parent; } GlangClassEntry;

/* ── Alloc helpers ────────────────────────────────────────────────────── */
/* alloc(T) and alloc(T, n) are emitted inline by the transpiler */

/* ── Managed memory (GC) ──────────────────────────────────────────────────
   Instances of a `managed class` are allocated through glang_managed_alloc,
   which zero-initialises the block and records it in a global registry. The
   registry is swept once at program exit (registered lazily via atexit on the
   first managed allocation), so managed objects are reclaimed automatically and
   never leak — the program never calls `delete` on a managed handle.
   This is the refcount/cycle collector's allocation seam; today it is a
   tracked allocate-and-sweep-at-exit collector. */
void* glang_managed_alloc(size_t size);
void  glang_managed_sweep(void);

/* Debug allocator wrappers for raw alloc()/free(); GLANG_DEBUG_ALLOC-gated
   leak + double/invalid-free detection (passthrough when the var is unset). */
void* glang_alloc(size_t size);
void* glang_alloc_n(size_t count, size_t size);
void  glang_free(void* p);

/* Time: monotonic nanoseconds, wall-clock milliseconds, and a millisecond sleep. */
int64_t glang_now_nanos(void);
int64_t glang_wall_millis(void);
void    glang_sleep_ms(int64_t ms);

/* TCP sockets (fds as int; -1 on error, errno stashed in glang_net_errno). */
int64_t glang_net_listen(int64_t port);
int64_t glang_net_local_port(int64_t fd);
int64_t glang_net_accept(int64_t fd);
int64_t glang_net_connect(const char* host, int64_t port);
int64_t glang_net_connect_nb(const char* host, int64_t port);
int64_t glang_net_recv(int64_t fd, uint8_t* buf, int64_t max);
int64_t glang_net_send(int64_t fd, uint8_t* buf, int64_t len);
void    glang_net_close(int64_t fd);
int64_t glang_net_set_nonblocking(int64_t fd);
int64_t glang_net_set_nodelay(int64_t fd);
int64_t glang_net_shutdown(int64_t fd, int64_t how);
int64_t glang_net_sock_error(int64_t fd);
int64_t glang_net_last_errno(void);
int64_t glang_net_would_block(void);
int64_t glang_net_poll(int64_t* fds, int64_t* events, int64_t* revents,
                       int64_t count, int64_t timeout_ms);

#endif /* GLANG_RUNTIME_H */
