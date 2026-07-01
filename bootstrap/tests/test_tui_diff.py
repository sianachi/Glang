"""Cross-backend differential test for the std TUI widget layer.

Exercises std/tui.lang (which pulls in std/term.lang, std/input.lang,
std/ansi.lang) without a real terminal: a widget tree is rendered into an
off-screen `Screen`, the resulting cell grid is read back as text, and a few
synthetic key events drive the list selection and text input. The Python
reference interpreter and the native compiled binary must agree exactly.

Both legs run as subprocesses so the std/ loader resolves the same way as the
CLI (`main.py` runs the compiler with cwd=Toolchain).
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROG = """
import "std/tui.lang";

void dump(Screen s) {
    for (int y = 0; y < s.height; ++y) {
        string row = "";
        for (int x = 0; x < s.width; ++x) {
            Cell c = s.back.get(y * s.width + x);
            row = row + toString(c.ch);
        }
        print(row);
    }
}

int main() {
    List<string> items = List<string>();
    items.add("Apple"); items.add("Banana"); items.add("Cherry");
    ListModel* m = new ListModel(items);
    Widget* root = box("Menu", listView(m));

    Screen sc = Screen(12, 5);
    sc.clear();
    renderWidget(root, sc, Rect(0, 0, 12, 5));
    dump(sc);

    handleWidget(root, new Key.KSpecial(keys::DOWN()));
    print("sel=" + strings::intToStr(m->selected) + " " + m->current());
    handleWidget(root, new Key.KSpecial(keys::DOWN()));
    handleWidget(root, new Key.KSpecial(keys::DOWN()));
    print("cur=" + m->current());

    InputModel* im = new InputModel();
    Widget* inp = inputField(im, "Name: ");
    handleWidget(inp, new Key.KChar('H'));
    handleWidget(inp, new Key.KChar('i'));
    print("in=" + im->text);
    handleWidget(inp, new Key.KSpecial(keys::BACKSPACE()));
    print("in=" + im->text);
    return 0;
}
"""

EXPECTED = [
    "+ Menu ----+",
    "|Apple     |",
    "|Banana    |",
    "|Cherry    |",
    "+----------+",
    "sel=1 Banana",
    "cur=Cherry",
    "in=Hi",
    "in=H",
]


def _lines(text: str) -> "list[str]":
    return [ln for ln in text.split("\n") if ln]


def _run_py(src: str) -> "list[str]":
    with tempfile.TemporaryDirectory() as d:
        lang = os.path.join(d, "p.lang")
        with open(lang, "w", encoding="utf-8") as f:
            f.write(src)
        proc = subprocess.run(
            [sys.executable, "bootstrap/main.py", "run", lang],
            cwd=_ROOT, capture_output=True, timeout=60,
        )
        assert proc.returncode == 0, proc.stderr.decode(errors="replace")
        return _lines(proc.stdout.decode())


def _run_native(src: str) -> "list[str]":
    with tempfile.TemporaryDirectory() as d:
        lang = os.path.join(d, "p.lang")
        cfile = os.path.join(d, "p.c")
        binary = os.path.join(d, "p")
        with open(lang, "w", encoding="utf-8") as f:
            f.write(src)
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", lang, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True, timeout=180,
        )
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True, timeout=60,
        )
        proc = subprocess.run([binary], cwd=_ROOT, capture_output=True, timeout=20)
        assert proc.returncode == 0, proc.stderr.decode(errors="replace")
        return _lines(proc.stdout.decode())


def test_widget_render_python_reference():
    assert _run_py(PROG) == EXPECTED


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
def test_widget_render_native_matches_reference():
    native = _run_native(PROG)
    assert native == EXPECTED
    assert native == _run_py(PROG)
