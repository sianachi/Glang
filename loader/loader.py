"""Phase 6 — module loader.

Resolves a program's transitive `import` graph into a single merged
``Program``. Given a root source file, the loader lexes and parses each file,
follows its imports (relative to that file's own directory), de-duplicates
files reached more than once (include-guard semantics), detects circular
imports, and concatenates every file's top-level declarations into one
``Program``.

The merged program is then handed to the existing analyser and interpreter
unchanged — Glang has a single global namespace (spec §12), so merging
declarations is all that import resolution requires.
"""

from __future__ import annotations

import os
from typing import List, Optional

from lexer.lexer import Lexer
from parser.parser import Parser
from parser.ast_nodes import Program, ImportDecl, Decl
from errors.errors import ImportError


class Loader:
    """Resolves imports starting from a root file into one merged Program."""

    def __init__(self) -> None:
        # Realpaths of files fully merged already (include-guard de-dup).
        self._loaded: set[str] = set()
        # Realpaths currently being loaded (the DFS stack) — used to spot cycles.
        self._visiting: List[str] = []
        # Top-level declarations gathered across all files, in load order.
        self._declarations: List[Decl] = []

    def load(self, root_path: str) -> Program:
        """Load ``root_path`` and all its imports into a single Program."""
        self._load_file(os.path.realpath(root_path), via=None)
        return Program(imports=[], declarations=self._declarations)

    def _load_file(self, abspath: str, via: Optional[ImportDecl]) -> None:
        if abspath in self._loaded:
            # Already merged via another import path — include-guard: skip.
            return
        if abspath in self._visiting:
            # The file is still on the current DFS stack: a circular import.
            line, col = (via.line, via.col) if via is not None else (0, 0)
            raise ImportError(
                f"circular import: {self._cycle_str(abspath)}", line, col
            )

        self._visiting.append(abspath)

        try:
            src = self._read(abspath, via)
            program = Parser(Lexer(src).tokenize()).parse()

            base_dir = os.path.dirname(abspath)
            for imp in program.imports:
                target = os.path.realpath(os.path.join(base_dir, imp.path))
                self._load_file(target, via=imp)

            # Post-order: a file's imports are merged before the file itself.
            self._declarations.extend(program.declarations)
        finally:
            self._visiting.pop()

        self._loaded.add(abspath)

    def _read(self, abspath: str, via: Optional[ImportDecl]) -> str:
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            if via is not None:
                raise ImportError(
                    f"cannot find imported file '{via.path}'", via.line, via.col
                ) from None
            raise ImportError(f"cannot find source file '{abspath}'", 0, 0) from None

    def _cycle_str(self, abspath: str) -> str:
        """Render the import cycle as basenames, e.g. ``a.lang -> b.lang -> a.lang``."""
        try:
            start = self._visiting.index(abspath)
        except ValueError:
            start = 0
        chain = self._visiting[start:] + [abspath]
        return " -> ".join(os.path.basename(p) for p in chain)


def load(root_path: str) -> Program:
    """Convenience wrapper: load ``root_path`` into a merged Program."""
    return Loader().load(root_path)
