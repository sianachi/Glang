"""Pytest setup after the bootstrap/Toolchain split.

The Python reference implementation lives under ``bootstrap/``; the GScript
toolchain (compiler sources, stdlib, runtime, examples) lives under ``Toolchain/``.

This makes the existing absolute-package imports (``import lexer``,
``from analyser.analyser import ...``) resolve against ``bootstrap/`` and points
the Glang loader's ``std/...`` resolution at ``Toolchain/stdlib``.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))   # .../bootstrap
_REPO = os.path.dirname(_HERE)                        # repo root

if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

os.environ.setdefault("GLANG_STDLIB", os.path.join(_REPO, "Toolchain", "stdlib"))
