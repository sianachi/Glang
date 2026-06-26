"""End-to-end tests for std/bytes.lang (the Bytes byte buffer).

Imports the shipped stdlib through the Loader so the real module is exercised.
Out-of-range access throws a catchable Exception (not a GlangRuntimeError), so
bounds cases are checked by catching inside Glang and asserting the message.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter


def run_out(src: str):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "prog.lang")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        program = Loader().load(path)
        env = Analyser().analyse(program)
        interp = Interpreter(env)
        code = interp.run(program)
        return code, interp.output


IMP = 'import "std/bytes.lang";\n'


def test_append_get_length_grow():
    _, out = run_out(IMP + """
    int main() {
        Bytes b = Bytes(1);          // tiny cap forces growth
        b.append(10); b.append(20); b.append(30);
        print(b.length());
        print((int)(b.get(0)));
        print((int)(b.get(2)));
        b.dispose();
        return 0;
    }
    """)
    assert out == ["3", "10", "30"]


def test_set_and_clear():
    _, out = run_out(IMP + """
    int main() {
        Bytes b = Bytes(4);
        b.append(1); b.append(2);
        b.set(0, 99);
        print((int)(b.get(0)));
        b.clear();
        print(b.length());
        print(b.isEmpty());
        b.dispose();
        return 0;
    }
    """)
    assert out == ["99", "0", "true"]


def test_int_packing_roundtrips():
    _, out = run_out(IMP + """
    int main() {
        Bytes p = Bytes(8);
        for (int i = 0; i < 8; ++i) { p.append(0); }
        p.putU16LE(0, 0xBEEF); print(p.getU16LE(0));
        p.putU16BE(2, 0xBEEF); print(p.getU16BE(2));
        p.putU32LE(4, 0x01020304); print(p.getU32LE(4));
        p.putU32BE(4, 0x01020304); print(p.getU32BE(4));
        p.dispose();
        return 0;
    }
    """)
    assert out == ["48879", "48879", "16909060", "16909060"]


def test_endianness_byte_order():
    # Confirm LE vs BE actually differ at the byte level.
    _, out = run_out(IMP + """
    int main() {
        Bytes p = Bytes(2);
        p.append(0); p.append(0);
        p.putU16LE(0, 0x0102);
        print((int)(p.get(0)));   // 0x02 low byte first
        print((int)(p.get(1)));   // 0x01
        p.putU16BE(0, 0x0102);
        print((int)(p.get(0)));   // 0x01 high byte first
        print((int)(p.get(1)));   // 0x02
        p.dispose();
        return 0;
    }
    """)
    assert out == ["2", "1", "1", "2"]


def test_get_out_of_range_throws_catchable():
    code, out = run_out(IMP + """
    int main() {
        Bytes b = Bytes(4);
        b.append(7);
        try { byte x = b.get(5); print((int)x); }
        catch (Exception* e) { print(e->message); }
        b.dispose();
        return 0;
    }
    """)
    assert code == 0
    assert out == ["Bytes.get: index out of range"]


def test_packing_offset_out_of_range_throws():
    code, out = run_out(IMP + """
    int main() {
        Bytes b = Bytes(2);
        b.append(0); b.append(0);
        try { b.putU32LE(0, 1); print(1); }
        catch (Exception* e) { print(e->message); }
        b.dispose();
        return 0;
    }
    """)
    assert code == 0
    assert out == ["Bytes.putU32LE: range out of bounds"]
