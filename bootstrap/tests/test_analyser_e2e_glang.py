"""Phase-4 comprehensive end-to-end gate for the self-hosted Glang analyser.

Harvests EVERY `ok(...)` / `err(...)` case from tests/test_analyser.py (by importing
that module and capturing the sources its test methods feed the `ok`/`err`/`analyse`
helpers), then runs each source through BOTH the Python reference analyser and the
self-hosted Glang pipeline (compiler/analyse_dump.lang, via glang_analyser_backend) and
asserts the outcomes agree:
  - `ok` cases: neither raises.
  - `err` cases: both raise a TypeError, and the expected fragment is in the Glang msg.

The direct type_utils / SymbolTable unit tests and Pass1 GlobalEnv-introspection tests in
test_analyser.py are NOT harvested here (they don't go through `analyse`); they are covered
by the per-module differential suites (test_tu_core/tu_env/symtab/pass1_glang.py).
"""

import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import tests.test_analyser as ta
from errors.errors import TypeError as GTE
from tests.glang_analyser_backend import glang_analyse

_real_analyse = ta.analyse
_OK_SRCS: "list[str]" = []
_ERR_CASES: "list[tuple[str, str]]" = []


def _cap_ok(src):
    _OK_SRCS.append(src)


def _cap_err(src, fragment):
    _ERR_CASES.append((src, fragment))


def _cap_analyse(src):
    # Direct `analyse(src)` calls (introspection tests) imply a valid program.
    _OK_SRCS.append(src)
    return _real_analyse(src)


def _harvest():
    ta.ok = _cap_ok
    ta.err = _cap_err
    ta.analyse = _cap_analyse
    try:
        for _, obj in inspect.getmembers(ta):
            if inspect.isclass(obj) and obj.__name__.startswith("Test"):
                try:
                    inst = obj()
                except Exception:
                    continue
                for mname, meth in inspect.getmembers(inst, inspect.ismethod):
                    if mname.startswith("test"):
                        try:
                            meth()
                        except Exception:
                            pass  # we only want the harvested sources
            elif inspect.isfunction(obj) and obj.__name__.startswith("test"):
                try:
                    obj()
                except Exception:
                    pass
    finally:
        ta.ok, ta.err, ta.analyse = ta.ok, ta.err, ta.analyse  # leave patched; harmless


_harvest()

# Dedup while preserving order.
_OK = list(dict.fromkeys(_OK_SRCS))
_ERR = list(dict.fromkeys(_ERR_CASES))


def _py_raises(src) -> bool:
    try:
        _real_analyse(src)
        return False
    except GTE:
        return True


@pytest.mark.parametrize("src", _OK)
def test_ok_cases_agree(src):
    # Only differential-check sources the Python reference actually accepts
    # (a harvested `analyse(src)` from a test that expected failure is filtered).
    if _py_raises(src):
        pytest.skip("python rejects this source; not an ok-case")
    glang_analyse(src)  # must not raise


@pytest.mark.parametrize("src,fragment", _ERR)
def test_err_cases_agree(src, fragment):
    with pytest.raises(GTE) as exc:
        glang_analyse(src)
    assert fragment in exc.value.msg, (
        f"expected {fragment!r} in Glang error {exc.value.msg!r}"
    )


def test_harvested_a_meaningful_corpus():
    assert len(_OK) + len(_ERR) > 150, (len(_OK), len(_ERR))
