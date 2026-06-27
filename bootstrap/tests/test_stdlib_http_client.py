"""Integration test for std/http_client.lang's socket path.

The pure parts (buildRequestBytes / parseResponse) are covered differentially in
test_stdlib_extras.py. This compiles a tiny client that performs a real GET and
POST against a Python server, exercising netConnect/send/recv end-to-end.

Needs gcc + loopback; skipped under GLANG_SKIP_NET=1.
"""

import os
import socket
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.skipif(
    os.environ.get("GLANG_SKIP_NET") == "1" or which("gcc") is None,
    reason="needs gcc + loopback sockets (set GLANG_SKIP_NET=1 to skip)",
)


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"hello-from-server\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(n)
        body = b"echo:" + data
        self.send_response(201)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


CLIENT = r"""
import "std/http_client.lang";

int main() {
    HttpClientResponse* g = httpGet("127.0.0.1", __PORT__, "/thing");
    if (g == null) { print("GET failed"); return 1; }
    print(intToStr(g->status));
    print(bytesRangeToStr(g->body, 0, g->body->length()));

    Bytes* payload = new Bytes(8);
    bytesAppendStr(payload, "ping");
    HttpClientResponse* p = httpPost("127.0.0.1", __PORT__, "/submit", payload, "text/plain");
    if (p == null) { print("POST failed"); return 1; }
    print(intToStr(p->status));
    print(bytesRangeToStr(p->body, 0, p->body->length()));
    return 0;
}
"""


def test_http_client_get_and_post():
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        with tempfile.TemporaryDirectory() as d:
            lang = os.path.join(d, "client.lang")
            cfile = os.path.join(d, "client.c")
            binary = os.path.join(d, "client")
            with open(lang, "w") as f:
                f.write(CLIENT.replace("__PORT__", str(port)))
            subprocess.run(
                [sys.executable, "bootstrap/main.py", "compile", lang, "-o", cfile],
                cwd=_ROOT, check=True, capture_output=True,
            )
            subprocess.run(
                ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
                cwd=_ROOT, check=True, capture_output=True,
            )
            proc = subprocess.run([binary], cwd=_ROOT, capture_output=True, text=True, timeout=20)
            assert proc.returncode == 0, proc.stderr
            lines = [ln for ln in proc.stdout.split("\n") if ln]
            assert lines == ["200", "hello-from-server", "201", "echo:ping"]
    finally:
        server.shutdown()
