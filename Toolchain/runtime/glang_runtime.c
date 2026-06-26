#include "glang_runtime.h"
#include <ctype.h>

/* ── Globals ──────────────────────────────────────────────────────────── */
int    glang_argc = 0;
char** glang_argv = NULL;
GlangExcFrame* __glang_exc_top = NULL;

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
    /* Strip trailing zeros like Python's repr */
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

/* ── Print ────────────────────────────────────────────────────────────── */

void glang_print_int(int64_t v)       { printf("%" PRId64 "\n", v); }
void glang_print_float(double v)      {
    /* Match interpreter: no trailing zeros */
    char buf[64]; snprintf(buf, sizeof(buf), "%.15g", v);
    printf("%s\n", buf);
}
void glang_print_bool(int v)          { printf("%s\n", v ? "true" : "false"); }
void glang_print_char(char v)         { printf("%c\n", v); }
void glang_print_string(const char* v){ printf("%s\n", v ? v : "null"); }

void glang_printerr_int(int64_t v)       { fprintf(stderr, "%" PRId64 "\n", v); }
void glang_printerr_float(double v)      { fprintf(stderr, "%.15g\n", v); }
void glang_printerr_bool(int v)          { fprintf(stderr, "%s\n", v ? "true" : "false"); }
void glang_printerr_char(char v)         { fprintf(stderr, "%c\n", v); }
void glang_printerr_string(const char* v){ fprintf(stderr, "%s\n", v ? v : "null"); }

/* ── toString ─────────────────────────────────────────────────────────── */

char* glang_tostring_int(int64_t v)    { return glang_inttostr(v); }
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
