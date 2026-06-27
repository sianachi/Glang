"""End-to-end tests for the GLang Language Server (Toolchain/lsp/).

Builds the native `glang-lsp` binary and the `json_dump` driver via the
self-hosted compiler, then:
  * drives the LSP base protocol over stdio (initialize -> didOpen -> hover ...)
    and asserts diagnostics, capabilities, hover, definition, and symbols;
  * runs a TCP-transport smoke test;
  * checks std/json.lang round-trips against Python's json (value-stable).

These exercise the native backend (the LSP ships as a compiled binary). They
require a C compiler + the toolchain; if the build can't run, the module skips.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_RUNTIME = "Toolchain/runtime/glang_runtime.c"

_cache: dict[str, str] = {}


def _build(driver_lang: str, name: str) -> str:
    """Compile a .lang driver to a native binary (cached). Returns its path."""
    if name in _cache:
        return _cache[name]
    d = tempfile.mkdtemp(prefix="glang_lsp_")
    c = os.path.join(d, name + ".c")
    b = os.path.join(d, name)
    try:
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", driver_lang, "-o", c],
            cwd=_ROOT, check=True, capture_output=True,
        )
        subprocess.run(
            ["cc", "-w", c, _RUNTIME, "-o", b],
            cwd=_ROOT, check=True, capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        pytest.skip(f"cannot build {name}: {e}")
    _cache[name] = b
    return b


# ── LSP framing helpers ──────────────────────────────────────────────────────

def _frame(obj) -> bytes:
    body = json.dumps(obj).encode("utf-8")
    return b"Content-Length: %d\r\n\r\n" % len(body) + body


def _parse_stream(data: bytes) -> list[dict]:
    out, i = [], 0
    while i < len(data):
        he = data.find(b"\r\n\r\n", i)
        if he < 0:
            break
        clen = 0
        for line in data[i:he].decode("ascii", "replace").split("\r\n"):
            if line.lower().startswith("content-length:"):
                clen = int(line.split(":", 1)[1].strip())
        body = data[he + 4:he + 4 + clen]
        out.append(json.loads(body.decode("utf-8")))
        i = he + 4 + clen
    return out


def _drive_stdio(messages: list[dict]) -> list[dict]:
    binary = _build("Toolchain/lsp/server.lang", "glang-lsp")
    payload = b"".join(_frame(m) for m in messages)
    proc = subprocess.run([binary, "--stdio"], input=payload,
                          capture_output=True, cwd=_ROOT, timeout=60)
    return _parse_stream(proc.stdout)


def _responses_by_id(parsed: list[dict]) -> dict:
    return {m["id"]: m for m in parsed if "id" in m}


def _notifications(parsed: list[dict], method: str) -> list[dict]:
    return [m for m in parsed if m.get("method") == method]


# Sources used across tests.
GOOD = (
    "int add(int a, int b) {\n"      # line 0
    "    return a + b;\n"
    "}\n"
    "enum Color { RED, GREEN }\n"     # line 3
    "int main() {\n"                  # line 4
    "    return add(1, 2);\n"         # line 5
    "}\n"
)
BAD = "int main() {\n    int x = y;\n    return 0;\n}\n"   # undefined 'y' at line 2


def _session(extra: list[dict]) -> list[dict]:
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}]
    msgs += extra
    msgs += [{"jsonrpc": "2.0", "id": 99, "method": "shutdown"},
             {"jsonrpc": "2.0", "method": "exit"}]
    return _drive_stdio(msgs)


# ── tests ────────────────────────────────────────────────────────────────────

def test_initialize_capabilities():
    parsed = _session([])
    res = _responses_by_id(parsed)[1]["result"]
    caps = res["capabilities"]
    assert caps["hoverProvider"] is True
    assert caps["definitionProvider"] is True
    assert caps["documentSymbolProvider"] is True
    assert "completionProvider" in caps
    assert caps["textDocumentSync"] == 1
    assert res["serverInfo"]["name"] == "glang-lsp"


def test_diagnostics_bad_source_positioned():
    parsed = _session([
        {"jsonrpc": "2.0", "method": "textDocument/didOpen",
         "params": {"textDocument": {"uri": "file:///bad.lang", "text": BAD}}},
    ])
    pub = _notifications(parsed, "textDocument/publishDiagnostics")
    assert len(pub) == 1
    diags = pub[0]["params"]["diagnostics"]
    assert len(diags) == 1
    d = diags[0]
    assert "undefined variable 'y'" in d["message"]
    # 'y' is on editor line 1 (0-based), at character 12.
    assert d["range"]["start"] == {"line": 1, "character": 12}
    assert d["severity"] == 1


def test_diagnostics_good_source_empty():
    parsed = _session([
        {"jsonrpc": "2.0", "method": "textDocument/didOpen",
         "params": {"textDocument": {"uri": "file:///good.lang", "text": GOOD}}},
    ])
    pub = _notifications(parsed, "textDocument/publishDiagnostics")
    assert pub and pub[0]["params"]["diagnostics"] == []


def test_hover_function_signature():
    parsed = _session([
        {"jsonrpc": "2.0", "method": "textDocument/didOpen",
         "params": {"textDocument": {"uri": "file:///g.lang", "text": GOOD}}},
        {"jsonrpc": "2.0", "id": 2, "method": "textDocument/hover",
         "params": {"textDocument": {"uri": "file:///g.lang"},
                    "position": {"line": 5, "character": 11}}},
    ])
    hov = _responses_by_id(parsed)[2]["result"]
    assert "int add(int a, int b)" in hov["contents"]["value"]


def test_definition_jumps_to_declaration():
    parsed = _session([
        {"jsonrpc": "2.0", "method": "textDocument/didOpen",
         "params": {"textDocument": {"uri": "file:///g.lang", "text": GOOD}}},
        {"jsonrpc": "2.0", "id": 2, "method": "textDocument/definition",
         "params": {"textDocument": {"uri": "file:///g.lang"},
                    "position": {"line": 5, "character": 11}}},
    ])
    loc = _responses_by_id(parsed)[2]["result"]
    assert loc["uri"] == "file:///g.lang"
    # 'add' is declared on line 0 at character 4.
    assert loc["range"]["start"] == {"line": 0, "character": 4}


def test_document_symbols():
    parsed = _session([
        {"jsonrpc": "2.0", "method": "textDocument/didOpen",
         "params": {"textDocument": {"uri": "file:///g.lang", "text": GOOD}}},
        {"jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
         "params": {"textDocument": {"uri": "file:///g.lang"}}},
    ])
    syms = _responses_by_id(parsed)[2]["result"]
    names = {s["name"]: s["kind"] for s in syms}
    assert names.get("add") == 12      # Function
    assert names.get("main") == 12     # Function
    assert names.get("Color") == 10    # Enum


def test_completion_includes_symbols_and_keywords():
    parsed = _session([
        {"jsonrpc": "2.0", "method": "textDocument/didOpen",
         "params": {"textDocument": {"uri": "file:///g.lang", "text": GOOD}}},
        {"jsonrpc": "2.0", "id": 2, "method": "textDocument/completion",
         "params": {"textDocument": {"uri": "file:///g.lang"},
                    "position": {"line": 5, "character": 4}}},
    ])
    items = _responses_by_id(parsed)[2]["result"]
    labels = {c["label"] for c in items}
    assert {"add", "main", "Color"} <= labels       # user symbols
    assert "print" in labels                         # builtin
    assert "while" in labels or "return" in labels   # keyword


def test_tcp_transport_smoke():
    binary = _build("Toolchain/lsp/server.lang", "glang-lsp")
    # Bind an ephemeral port ourselves to avoid races, then hand it to the server.
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    proc = subprocess.Popen([binary, "--tcp", str(port)], cwd=_ROOT,
                            stderr=subprocess.PIPE)
    try:
        conn = None
        for _ in range(50):
            try:
                conn = socket.create_connection(("127.0.0.1", port), timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        assert conn is not None, "server did not start listening"
        conn.sendall(_frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}))
        conn.settimeout(10)
        data = b""
        while b"\r\n\r\n" not in data or b"capabilities" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
        parsed = _parse_stream(data)
        assert parsed and parsed[0]["result"]["capabilities"]["hoverProvider"] is True
        conn.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ── std/json.lang round-trip ─────────────────────────────────────────────────

@pytest.mark.parametrize("doc", [
    {"jsonrpc": "2.0", "id": 7, "method": "x/y", "params": {"a": [1, 2, 3], "b": True, "c": None}},
    {"nested": {"deep": {"list": [{"k": "v"}, 1.5, False]}}},
    {"unicode": "café ☃", "escapes": "tab\there\nline \"q\""},
    [1, 2, [3, [4, [5]]]],
    {"ints_vs_floats": [0, -3, 1.5, 1000000]},
    "just a string",
    42,
])
def test_json_roundtrip_matches_python(doc):
    binary = _build("Toolchain/lsp/json_dump.lang", "json_dump")
    src = json.dumps(doc).encode("utf-8")
    proc = subprocess.run([binary], input=src, capture_output=True, cwd=_ROOT, timeout=30)
    out = proc.stdout.decode("utf-8").strip()
    # Value-stable: re-serialized JSON parses back to the same value.
    assert json.loads(out) == doc
