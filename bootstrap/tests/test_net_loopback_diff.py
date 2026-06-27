"""Cross-backend differential test for the in-memory socket model.

`std/net.lang`'s socket builtins (netListen/accept/connect/recv/send/close) are
backed three different ways:

  * the Python reference interpreter  -> deterministic in-memory loopback
  * the self-hosted interpreter        -> the same model, written in Glang
  * the native compiled binary         -> real BSD sockets

A single-process loopback round-trip (listen -> connect -> accept -> send/recv)
must produce byte-identical output on all three. The interpreter legs use no real
networking, so they run everywhere; the compiled leg needs gcc + loopback and is
skipped under GLANG_SKIP_NET=1.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

from lexer.lexer import Lexer
from parser.parser import Parser
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter

from tests.glang_interp_backend import gi_run

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Uses only builtins + alloc + pointer indexing — no imports — so the very same
# source runs on the import-free interp_dump driver, the Python interpreter, and
# the native compiler without any loader differences muddying the comparison.
RAW = """
int main() {
    int lis = netListen(0);
    int port = netLocalPort(lis);
    print(port > 0);

    int client = netConnect("127.0.0.1", port);
    int server = netAccept(lis);

    byte* msg = alloc(byte, 8);
    msg[0] = (byte)0x48; msg[1] = (byte)0x49;   // "HI"
    int sent = netSend(client, msg, 2);
    print(sent);

    byte* inbuf = alloc(byte, 64);
    int n = netRecv(server, inbuf, 64);
    print(n);
    print((int)(inbuf[0]));
    print((int)(inbuf[1]));

    byte* reply = alloc(byte, 8);
    reply[0] = (byte)((int)(inbuf[0]) + 1);
    netSend(server, reply, 1);
    byte* back = alloc(byte, 64);
    int m = netRecv(client, back, 64);
    print(m);
    print((int)(back[0]));

    netClose(client); netClose(server); netClose(lis);
    return 0;
}
"""

EXPECTED = ["true", "2", "2", "72", "73", "1", "73"]


def _py_run(src: str) -> "list[str]":
    prog = Parser(Lexer(src).tokenize()).parse()
    interp = Interpreter(Analyser().analyse(prog))
    interp.run(prog)
    return interp.output


def _compiled_run(src: str) -> "list[str]":
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
        assert proc.returncode == 0, proc.stderr
        return [ln for ln in proc.stdout.split("\n") if ln]


def test_python_interpreter_loopback():
    """In-memory model in the Python reference interpreter."""
    assert _py_run(RAW) == EXPECTED


def test_self_hosted_interpreter_loopback():
    """The same model, implemented in Glang (interp.lang)."""
    code, output = gi_run(RAW)
    assert code == 0
    assert output == EXPECTED


@pytest.mark.skipif(
    os.environ.get("GLANG_SKIP_NET") == "1" or which("gcc") is None,
    reason="needs gcc + real loopback sockets (set GLANG_SKIP_NET=1 to skip)",
)
def test_compiled_matches_interpreters():
    """Real BSD sockets agree with both in-memory interpreter models."""
    compiled = _compiled_run(RAW)
    assert compiled == EXPECTED
    assert compiled == _py_run(RAW) == gi_run(RAW)[1]
