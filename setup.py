from setuptools import setup, find_packages
from Cython.Build import cythonize
import glob
import os

# Collect all .py files except tests, examples, and main entry point
# These modules use deep recursion that overflows the C stack when Cython
# compiles them (Cython bypasses Python's recursion counter on direct calls).
# Keep them as pure Python so the recursion limit is enforced.
KEEP_AS_PYTHON = {
    "analyser/monomorphize.py",
    "analyser/pass2_checker.py",
    "analyser/namespace_resolver.py",
    "interpreter/interpreter.py",
}

modules = []
for pattern in [
    "lexer/*.py",
    "parser/*.py",
    "analyser/*.py",
    "interpreter/*.py",
    "glang_loader/*.py",
    "errors/*.py",
    "compiler/*.py",
]:
    for path in glob.glob(pattern):
        base = os.path.basename(path)
        if base != "__init__.py" and path not in KEEP_AS_PYTHON:
            modules.append(path)

setup(
    name="glang",
    packages=find_packages(),
    ext_modules=cythonize(
        modules,
        language_level=3,
        compiler_directives={"boundscheck": False, "wraparound": False},
    ),
)
