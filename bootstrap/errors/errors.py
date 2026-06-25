from __future__ import annotations


class GlangError(Exception):
    """Base class for all Glang language errors.

    Every error produced by the lexer, parser, analyser, or interpreter
    subclasses this, so callers can catch all Glang errors with a single
    `except GlangError` clause.

    Attributes:
      msg   — the human-readable error message (without position)
      line  — 1-based source line where the error occurred
      col   — 1-based column where the error occurred
    """

    def __init__(self, msg: str, line: int, col: int) -> None:
        super().__init__(f"{msg} at {line}:{col}")
        self.msg = msg
        self.line = line
        self.col = col

    def __str__(self) -> str:
        return f"{type(self).__name__}: {self.msg} at {self.line}:{self.col}"


class LexError(GlangError):
    """Raised by the lexer for invalid characters or malformed literals.

    Examples:
      Unexpected character '@'
      Unterminated string literal
      Empty hex literal (0x with no digits)
    """


class ParseError(GlangError):
    """Raised by the parser when the token stream violates the grammar.

    Examples:
      Expected '(' after 'if'
      Variable declaration requires an initialiser
      Only one variable per declaration statement
    """


class TypeError(GlangError):
    """Raised by the semantic analyser for type-level violations.

    Note: this shadows Python's built-in TypeError. Import carefully;
    use `errors.errors.TypeError` when both are needed in the same file.

    Examples:
      Condition must be bool, got int
      Dog has no method 'fly'
      Cannot assign void to int
      Interface method 'toString' not implemented
    """


class RuntimeError(GlangError):
    """Raised by the interpreter for violations detected at runtime.

    Note: this shadows Python's built-in RuntimeError.

    Examples:
      Null pointer dereference
      Use after free
      Double free
      Out-of-bounds array access
    """


class ImportError(GlangError):
    """Raised by the module loader for import-resolution failures.

    Note: this shadows Python's built-in ImportError (consistent with how
    TypeError and RuntimeError are shadowed in this module).

    Examples:
      Cannot find imported file 'stdlib/list.lang'
      Circular import: a.lang -> b.lang -> a.lang
    """
