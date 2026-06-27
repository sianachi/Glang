"""Native tests for std/net.lang over real BSD sockets.

These exercise the compiled path specifically: compile with glangc, link the
runtime, and run the binary against real kernel sockets. A single process does a
loopback round-trip: connect() completes via the kernel backlog before accept(),
so listen -> connect -> accept -> send/recv works single-threaded.

(The interpreters back the same builtins with an in-memory loopback instead;
cross-backend agreement is checked in test_net_loopback_diff.py.)

Set GLANG_SKIP_NET=1 to skip (e.g. sandboxes without loopback sockets).
"""

import os
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.skipif(
    os.environ.get("GLANG_SKIP_NET") == "1",
    reason="GLANG_SKIP_NET=1",
)


def _have_gcc() -> bool:
    from shutil import which
    return which("gcc") is not None


def _compile_run(src: str):
    if not _have_gcc():
        pytest.skip("gcc not available")
    with tempfile.TemporaryDirectory() as d:
        lang = os.path.join(d, "p.lang")
        cfile = os.path.join(d, "p.c")
        binary = os.path.join(d, "p")
        with open(lang, "w", encoding="utf-8") as f:
            f.write(src)
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", lang, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True,
        )
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True,
        )
        proc = subprocess.run([binary], cwd=_ROOT, capture_output=True, text=True, timeout=20)
        return proc.returncode, proc.stdout


LOOPBACK = """
import "std/net.lang";
import "std/bytes.lang";

int main() {
    TcpListener lis = TcpListener(0);
    int port = lis.port();
    print(port > 0);

    TcpSocket* client = tcpConnect("127.0.0.1", port);
    TcpSocket* server = lis.accept();

    Bytes msg = Bytes(8);
    msg.append(0x48); msg.append(0x49);   // "HI"
    client.send(msg);

    Bytes inbuf = Bytes(64);
    int n = server.recv(inbuf);
    print(n);
    print((int)(inbuf.get(0)));
    print((int)(inbuf.get(1)));

    Bytes reply = Bytes(8);
    reply.append((byte)((int)(inbuf.get(0)) + 1));
    server.send(reply);
    Bytes back = Bytes(64);
    int m = client.recv(back);
    print(m);
    print((int)(back.get(0)));

    client.close(); server.close(); lis.close();
    delete client; delete server;
    return 0;
}
"""


def test_loopback_roundtrip():
    code, out = _compile_run(LOOPBACK)
    assert code == 0
    assert out.split() == ["true", "2", "72", "73", "1", "73"]
