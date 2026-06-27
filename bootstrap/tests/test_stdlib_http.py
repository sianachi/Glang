"""Differential test for the pure HTTP stack (std/http.lang, router, html).

These modules are plain Glang over strings/Bytes — no sockets — so the same
program runs under the Python reference interpreter (via the loader) and through
the native compiler. We assert byte-identical output across the two backends,
which is the project's correctness contract.

(The self-hosted interp_dump driver doesn't resolve `std/` imports, so it can't
run these multi-module programs; socket-free cross-backend agreement for the
builtins themselves is covered by test_net_loopback_diff.py.)
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROG = r"""
import "std/http.lang";
import "std/router.lang";
import "std/html.lang";

HttpResponse* home(HttpRequest* req) {
    return httpHtml(200, htmlTag("h1", "Hi <there> & \"you\""));
}
HttpResponse* api(HttpRequest* req) {
    return httpText(201, "api path=" + req->path);
}

HttpRequest* mkReq(string method, string path) {
    HttpRequest* r = new HttpRequest();
    r->method = method; r->path = path; r->target = path; r->version = "HTTP/1.1";
    return r;
}

int main() {
    // --- parsing ---
    Bytes* buf = new Bytes(64);
    bytesAppendStr(buf, "POST /submit?x=1&y=2 HTTP/1.1\r\nHost: h\r\nContent-Length: 4\r\n\r\nbody");
    HttpParseResult* pr = tryParseRequest(buf);
    print(pr->complete);
    print(pr->request->method);
    print(pr->request->path);
    print(pr->request->query);
    print(pr->request->headers->get("content-length"));
    print(pr->request->body->length());
    print(pr->consumed);

    // --- incomplete head returns not-complete ---
    Bytes* partial = new Bytes(16);
    bytesAppendStr(partial, "GET / HTTP/1.1\r\nHost: h");
    HttpParseResult* pp = tryParseRequest(partial);
    print(pp->complete);

    // --- routing + escaping ---
    Router router = Router();
    router.get("/", home);
    router.mount("/api", api);
    HttpResponse* a = router.dispatch(mkReq("GET", "/"));
    print(a->status);
    print(bytesRangeToStr(a->body, 0, a->body->length()));
    HttpResponse* b = router.dispatch(mkReq("GET", "/api/x"));
    print(b->status);
    print(bytesRangeToStr(b->body, 0, b->body->length()));
    HttpResponse* c = router.dispatch(mkReq("GET", "/nope"));
    print(c->status);

    // --- rendering --- (print a clean prefix; the full blob has CRLFs)
    HttpResponse* resp = httpText(200, "hello");
    Bytes* out = renderResponse(resp, true);
    print(out->length() > 100);
    print(bytesRangeToStr(out, 0, 15));
    return 0;
}
"""

EXPECTED = [
    "true", "POST", "/submit", "x=1&y=2", "4", "4", "65",
    "false",
    "200", "<h1>Hi &lt;there&gt; &amp; &quot;you&quot;</h1>",
    "201", "api path=/api/x",
    "404",
    "true", "HTTP/1.1 200 OK",
]


def _interp_run(path: str) -> "list[str]":
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", path],
        cwd=_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.split("\n")[:-1] if proc.stdout.endswith("\n") else proc.stdout.split("\n")


def _compiled_run(path: str) -> "list[str]":
    with tempfile.TemporaryDirectory() as d:
        cfile = os.path.join(d, "p.c")
        binary = os.path.join(d, "p")
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", path, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True,
        )
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True,
        )
        proc = subprocess.run([binary], cwd=_ROOT, capture_output=True, text=True, timeout=20)
        assert proc.returncode == 0, proc.stderr
        out = proc.stdout
        return out.split("\n")[:-1] if out.endswith("\n") else out.split("\n")


def _write_prog() -> str:
    fd, path = tempfile.mkstemp(suffix=".lang")
    with os.fdopen(fd, "w") as f:
        f.write(PROG)
    return path


def test_http_stack_interpreter():
    path = _write_prog()
    try:
        assert _interp_run(path) == EXPECTED
    finally:
        os.unlink(path)


@pytest.mark.skipif(which("gcc") is None, reason="gcc not available")
def test_http_stack_compiled_matches_interpreter():
    path = _write_prog()
    try:
        assert _compiled_run(path) == EXPECTED == _interp_run(path)
    finally:
        os.unlink(path)
