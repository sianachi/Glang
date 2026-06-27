"""End-to-end integration test for the Glang web server + reverse proxy.

Compiles real-world-applications/web-server/main.lang with glangc, links the
runtime, and runs the binary against a real Python upstream. Exercises local
routes, HTML escaping, the reverse proxy, and concurrent connections over real
loopback sockets.

Needs gcc + loopback; skipped under GLANG_SKIP_NET=1.
"""

import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_APP = os.path.join(_ROOT, "real-world-applications", "web-server", "main.lang")

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


def _wait_listening(port: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"server on :{port} never came up")


def _get(port: int, path: str) -> "tuple[int, str]":
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def _put_bytes(port: int, path: str, data: bytes) -> int:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def _get_raw(port: int, path: str) -> "tuple[int, bytes, dict]":
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def _raw_request(port: int, raw: bytes) -> bytes:
    """Send a literal request (bypasses client-side path normalization)."""
    with socket.create_connection(("127.0.0.1", port), timeout=5) as s:
        s.sendall(raw)
        s.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            d = s.recv(65536)
            if not d:
                break
            chunks.append(d)
    return b"".join(chunks)


def _status_of(resp: bytes) -> int:
    return int(resp.split(b"\r\n", 1)[0].split(b" ")[1])


class _UpstreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (f"UPSTREAM {self.path} host={self.headers.get('Host')} "
                f"via={self.headers.get('Via')}\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture
def server_binary():
    with tempfile.TemporaryDirectory() as d:
        cfile = os.path.join(d, "ws.c")
        binary = os.path.join(d, "ws")
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", _APP, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True,
        )
        subprocess.run(
            ["gcc", "-O2", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True,
        )
        yield binary


def test_server_and_proxy(server_binary):
    up_port = _free_port()
    srv_port = _free_port()

    upstream = ThreadingHTTPServer(("127.0.0.1", up_port), _UpstreamHandler)
    up_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    up_thread.start()

    proc = subprocess.Popen(
        [server_binary, str(srv_port), "127.0.0.1", str(up_port)],
        cwd=_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        _wait_listening(srv_port)

        # local routes
        assert _get(srv_port, "/health") == (200, "ok\n")
        status, body = _get(srv_port, "/")
        assert status == 200 and "Glang web server" in body

        # HTML escaping (XSS-safe echo)
        status, body = _get(srv_port, "/echo?msg=<script>")
        assert status == 200
        assert "&lt;script&gt;" in body and "<script>" not in body

        # reverse proxy to the upstream
        status, body = _get(srv_port, "/api/users/42")
        assert status == 200
        assert "UPSTREAM /api/users/42" in body
        assert "via=1.1 glang" in body          # proxy injected Via
        assert f"host=127.0.0.1:{up_port}" in body  # Host rewritten to upstream

        # 404 for unknown local route
        assert _get(srv_port, "/does-not-exist")[0] == 404

        # concurrency: many simultaneous clients on the single event loop
        results = []
        lock = threading.Lock()

        def hit():
            code, _ = _get(srv_port, "/health")
            with lock:
                results.append(code)

        threads = [threading.Thread(target=hit) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert results == [200] * 20
    finally:
        proc.terminate()
        proc.wait(timeout=5)
        upstream.shutdown()


def test_file_store_upload_download_and_cors(server_binary):
    srv_port = _free_port()
    dead_upstream = _free_port()   # proxy mount is registered but never hit here
    with tempfile.TemporaryDirectory() as uploads:
        proc = subprocess.Popen(
            [server_binary, str(srv_port), "127.0.0.1", str(dead_upstream), uploads],
            cwd=_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            _wait_listening(srv_port)

            # Upload a binary blob with NUL/0xFF bytes (string I/O would truncate).
            blob = bytes([0, 255, 65, 0, 66, 255, 137, 10])
            assert _put_bytes(srv_port, "/files/blob.bin", blob) == 201

            # JSON listing includes it.
            status, body = _get(srv_port, "/files")
            assert status == 200 and "blob.bin" in body

            # Download is byte-identical (binary round-trip over the wire).
            status, data, _ = _get_raw(srv_port, "/files/blob.bin")
            assert status == 200 and data == blob

            # MIME by extension on download.
            _put_bytes(srv_port, "/files/p.png", b"\x89PNG\x00\x01\x02")
            status, _, headers = _get_raw(srv_port, "/files/p.png")
            assert status == 200
            assert headers.get("Content-Type", "").startswith("image/png")

            # Missing file -> 404.
            assert _get(srv_port, "/files/nope")[0] == 404

            # Path traversal (sent literally to bypass client normalization) -> 403.
            resp = _raw_request(
                srv_port,
                b"GET /files/../../etc/hosts HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n",
            )
            assert _status_of(resp) == 403
            # And it did not leak the file.
            assert b"localhost" not in resp.lower()

            # CORS preflight -> 204 with the allow-origin header.
            resp = _raw_request(
                srv_port,
                b"OPTIONS /files/x HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n",
            )
            assert _status_of(resp) == 204
            assert b"access-control-allow-origin: *" in resp.lower()

            # A normal response also carries the CORS header.
            _, _, headers = _get_raw(srv_port, "/files")
            assert headers.get("Access-Control-Allow-Origin") == "*"
        finally:
            proc.terminate()
            proc.wait(timeout=5)
