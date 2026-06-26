from __future__ import annotations
from dataclasses import dataclass
from typing import List

from .token_types import TokenType, KEYWORDS
from errors.errors import LexError


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"


class Lexer:
    def __init__(self, source: str) -> None:
        """Initialise the lexer with the full source string.

        State:
          _src   — the raw source text
          _pos   — index of the next character to consume
          _line  — current 1-based line number
          _col   — current 1-based column number
        """
        self._src = source
        self._pos = 0
        self._line = 1
        self._col = 1

    # ------------------------------------------------------------------
    # Low-level character utilities
    # ------------------------------------------------------------------

    def _peek(self, offset: int = 0) -> str:
        """Return the character at _pos + offset without consuming it.

        Returns "" if the position is past the end of the source, so
        callers never get an IndexError and can treat "" as a sentinel
        for end-of-file.
        """
        pos = self._pos + offset
        return self._src[pos] if pos < len(self._src) else ""

    def _advance(self) -> str:
        """Consume and return the current character, updating line/col.

        Increments _line and resets _col to 1 on newlines; otherwise
        increments _col. Must only be called when _pos < len(_src).
        """
        ch = self._src[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _match(self, expected: str) -> bool:
        """Consume the next character and return True if it equals `expected`.

        Leaves _pos unchanged and returns False otherwise. Useful for
        disambiguating two-character tokens without over-consuming.
        """
        if self._peek() == expected:
            self._advance()
            return True
        return False

    # ------------------------------------------------------------------
    # Whitespace and comments
    # ------------------------------------------------------------------

    def _skip_whitespace_and_comments(self) -> None:
        """Advance past all whitespace and comments, leaving _pos on the
        first character that belongs to a token.

        Handles:
          Whitespace     space, tab, carriage-return, newline
          Line comment   // … up to (but not including) the newline
          Block comment  /* … */  — non-nesting; raises LexError if
                         the closing */ is never found
        """
        while self._pos < len(self._src):
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance()
            elif ch == "/" and self._peek(1) == "/":
                end = self._src.find("\n", self._pos)
                self._pos = end if end != -1 else len(self._src)
            elif ch == "/" and self._peek(1) == "*":
                start_line, start_col = self._line, self._col
                self._advance()  # /
                self._advance()  # *
                end = self._src.find("*/", self._pos)
                if end == -1:
                    raise LexError("unterminated block comment", start_line, start_col)
                # count newlines skipped so line tracking stays accurate
                skipped = self._src[self._pos:end]
                self._line += skipped.count("\n")
                if "\n" in skipped:
                    self._col = len(skipped) - skipped.rfind("\n")
                else:
                    self._col += len(skipped)
                self._pos = end + 2  # skip past */
            else:
                break

    # ------------------------------------------------------------------
    # Identifiers and keywords
    # ------------------------------------------------------------------

    def _lex_ident_or_keyword(self, line: int, col: int) -> Token:
        """Consume an identifier or keyword starting at the current position.

        An identifier matches [a-zA-Z_][a-zA-Z0-9_]*. After collecting
        the full word, the KEYWORDS dict is consulted: if the word is a
        reserved keyword the corresponding KW_* token type is used;
        otherwise the token type is IDENT.

        Examples:
          foo        → IDENT("foo")
          while      → KW_WHILE("while")
          _count     → IDENT("_count")
        """
        start = self._pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        word = self._src[start:self._pos]
        tt = KEYWORDS.get(word, TokenType.IDENT)
        return Token(tt, word, line, col)

    # ------------------------------------------------------------------
    # Number literals
    # ------------------------------------------------------------------

    def _lex_number(self, line: int, col: int) -> Token:
        """Lex an integer or float literal starting at the current position.

        Formats to handle:
          Decimal int   42  0  1_000_000
          Hex int       0xFF  0xDEAD_BEEF  (prefix 0x or 0X)
          Binary int    0b1010  0b1111_0000  (prefix 0b or 0B)
          Float         3.14  0.5  1e10  1.5e-3  2.0E+4

        Rules:
          - After '0x'/'0X' consume [0-9a-fA-F_]+  → INT_LIT
          - After '0b'/'0B' consume [01_]+          → INT_LIT
          - Otherwise consume [0-9_]+
              · If '.' follows and the char after that is a digit,
                consume '.' then [0-9_]+             → will be FLOAT_LIT
              · If 'e'/'E' follows, consume it,
                optional '+'/'-', then [0-9]+        → FLOAT_LIT
              · Otherwise                            → INT_LIT
          - Underscores may appear between digits but not at start/end;
            strip them from the stored value string.
          - The stored value should be the clean literal (no underscores),
            e.g. "1000000", "255", "10", "3.14", "1500.0".

        Return Token(TokenType.INT_LIT, ...) or Token(TokenType.FLOAT_LIT, ...).
        """
        is_float = False
        parts: List[str] = []

        if self._peek() == "0" and self._peek(1) in ("x", "X"):
            self._advance()  # 0
            self._advance()  # x/X
            while (ch := self._peek()) and ch in "0123456789abcdefABCDEF_":
                self._advance()
                if ch != "_":
                    parts.append(ch)
            if not parts:
                raise LexError("empty hex literal", line, col)
            return Token(TokenType.INT_LIT, str(int("".join(parts), 16)), line, col)

        if self._peek() == "0" and self._peek(1) in ("b", "B"):
            self._advance()  # 0
            self._advance()  # b/B
            while (ch := self._peek()) and ch in "01_":
                self._advance()
                if ch != "_":
                    parts.append(ch)
            if not parts:
                raise LexError("empty binary literal", line, col)
            return Token(TokenType.INT_LIT, str(int("".join(parts), 2)), line, col)

        while (ch := self._peek()) and (ch.isdigit() or ch == "_"):
            self._advance()
            if ch != "_":
                parts.append(ch)

        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            parts.append(self._advance())  # .
            while (ch := self._peek()) and (ch.isdigit() or ch == "_"):
                self._advance()
                if ch != "_":
                    parts.append(ch)

        if self._peek() in ("e", "E"):
            is_float = True
            parts.append(self._advance())  # e/E
            if self._peek() in ("+", "-"):
                parts.append(self._advance())
            if not self._peek().isdigit():
                raise LexError("expected digits after exponent", line, col)
            while self._peek().isdigit():
                parts.append(self._advance())

        value = "".join(parts)
        if is_float:
            return Token(TokenType.FLOAT_LIT, value, line, col)

        return Token(TokenType.INT_LIT, value, line, col)

    # ------------------------------------------------------------------
    # Escape sequences (shared by string and char)
    # ------------------------------------------------------------------

    def _read_escape(self) -> str:
        """Decode one escape sequence; the leading backslash has already
        been consumed by the caller.

        Supported sequences:
          \\n  → newline        \\t  → tab           \\r  → carriage return
          \\\\  → backslash     \\"  → double quote   \\' → single quote
          \\0  → null byte      \\xHH → hex byte (two hex digits required)

        Raises LexError for any unrecognised sequence or malformed \\xHH.
        """
        if self._pos >= len(self._src):
            raise LexError("unterminated escape sequence", self._line, self._col)
        ch = self._advance()
        simple = {
            "n": "\n", "t": "\t", "r": "\r",
            "\\": "\\", '"': '"', "'": "'", "0": "\0",
        }
        if ch in simple:
            return simple[ch]
        if ch == "x":
            h1 = self._advance() if self._pos < len(self._src) else ""
            h2 = self._advance() if self._pos < len(self._src) else ""
            valid = "0123456789abcdefABCDEF"
            if h1 not in valid or h2 not in valid:
                raise LexError(
                    f"invalid hex escape \\x{h1}{h2}", self._line, self._col
                )
            return chr(int(h1 + h2, 16))
        raise LexError(f"unknown escape sequence \\{ch}", self._line, self._col)

    # ------------------------------------------------------------------
    # String literals
    # ------------------------------------------------------------------

    def _lex_string(self, line: int, col: int) -> Token:
        """Lex a double-quoted string literal starting at the current position.

        Consumes everything between the opening and closing double quotes,
        processing escape sequences via _read_escape. The stored value is
        the decoded string content — quotes are not included.

        Raises LexError for:
          - end-of-file before the closing quote
          - a raw newline inside the literal (use \\n instead)

        Examples:
          "hello"       → STRING_LIT("hello")
          "line\\n"     → STRING_LIT("line\\n")  (actual newline in value)
          "say \\"hi\\"" → STRING_LIT('say "hi"')
        """
        self._advance()  # opening "
        parts: List[str] = []
        while True:
            if self._pos >= len(self._src):
                raise LexError("unterminated string literal", line, col)
            ch = self._peek()
            if ch == '"':
                self._advance()
                break
            if ch == "\n":
                raise LexError("newline inside string literal", self._line, self._col)
            if ch == "\\":
                self._advance()
                parts.append(self._read_escape())
            else:
                parts.append(self._advance())
        return Token(TokenType.STRING_LIT, "".join(parts), line, col)

    # ------------------------------------------------------------------
    # Char literals
    # ------------------------------------------------------------------

    def _lex_char(self, line: int, col: int) -> Token:
        """Lex a single-quoted char literal starting at the current position.

        Consumes exactly one character (or one escape sequence) between
        the opening and closing single quotes. The stored value is the
        single decoded character — quotes are not included.

        Raises LexError for:
          - end-of-file before any content
          - empty literal ''
          - more than one character before the closing quote

        Examples:
          'a'    → CHAR_LIT("a")
          '\\n'  → CHAR_LIT("\\n")  (actual newline in value)
          '\\x41' → CHAR_LIT("A")
        """
        self._advance()  # opening '
        if self._pos >= len(self._src):
            raise LexError("unterminated char literal", line, col)
        ch = self._peek()
        if ch == "'":
            raise LexError("empty char literal", line, col)
        if ch == "\\":
            self._advance()
            value = self._read_escape()
        else:
            value = self._advance()
        if self._peek() != "'":
            raise LexError(
                "char literal must contain exactly one character", line, col
            )
        self._advance()  # closing '
        return Token(TokenType.CHAR_LIT, value, line, col)

    # ------------------------------------------------------------------
    # Operators and punctuation
    # ------------------------------------------------------------------

    def _lex_operator_or_punct(self, line: int, col: int) -> Token:
        """Lex a single operator or punctuation token starting at the
        current position.

        Consumes the leading character immediately, then uses _match to
        greedily check for a second (or third) character before deciding
        the final token type. Longer matches are always preferred:
          '<' → LT, but '<<' → LSHIFT, and '<<=' → LSHIFT_ASSIGN.

        Operators recognised:
          Arithmetic   + - * / %  (with = variants and ++ --)
          Bitwise      & | ^ ~ << >>  (with = variants)
          Logical      && || !
          Comparison   == != < <= > >=
          Assignment   = += -= *= /= %= &= |= ^= <<= >>=
          Arrow        ->

        Punctuation:
          { } ( ) [ ] ; , . : ->

        Raises LexError for any character not matching the above.
        """
        ch = self._advance()

        if ch == "+":
            if self._match("+"): return Token(TokenType.PLUS_PLUS,      "++", line, col)
            if self._match("="): return Token(TokenType.PLUS_ASSIGN,    "+=", line, col)
            return Token(TokenType.PLUS, "+", line, col)
        if ch == "-":
            if self._match("-"): return Token(TokenType.MINUS_MINUS,    "--", line, col)
            if self._match("="): return Token(TokenType.MINUS_ASSIGN,   "-=", line, col)
            if self._match(">"): return Token(TokenType.ARROW,          "->", line, col)
            return Token(TokenType.MINUS, "-", line, col)
        if ch == "*":
            if self._match("="): return Token(TokenType.STAR_ASSIGN,    "*=", line, col)
            return Token(TokenType.STAR, "*", line, col)
        if ch == "/":
            if self._match("="): return Token(TokenType.SLASH_ASSIGN,   "/=", line, col)
            return Token(TokenType.SLASH, "/", line, col)
        if ch == "%":
            if self._match("="): return Token(TokenType.PERCENT_ASSIGN, "%=", line, col)
            return Token(TokenType.PERCENT, "%", line, col)
        if ch == "&":
            if self._match("&"): return Token(TokenType.AND,            "&&", line, col)
            if self._match("="): return Token(TokenType.AMP_ASSIGN,     "&=", line, col)
            return Token(TokenType.AMP, "&", line, col)
        if ch == "|":
            if self._match("|"): return Token(TokenType.OR,             "||", line, col)
            if self._match("="): return Token(TokenType.PIPE_ASSIGN,    "|=", line, col)
            return Token(TokenType.PIPE, "|", line, col)
        if ch == "^":
            if self._match("="): return Token(TokenType.CARET_ASSIGN,   "^=", line, col)
            return Token(TokenType.CARET, "^", line, col)
        if ch == "<":
            if self._peek() == "<":
                self._advance()
                if self._match("="): return Token(TokenType.LSHIFT_ASSIGN, "<<=", line, col)
                return Token(TokenType.LSHIFT, "<<", line, col)
            if self._match("="): return Token(TokenType.LTE, "<=", line, col)
            return Token(TokenType.LT, "<", line, col)
        if ch == ">":
            if self._peek() == ">":
                self._advance()
                if self._match("="): return Token(TokenType.RSHIFT_ASSIGN, ">>=", line, col)
                return Token(TokenType.RSHIFT, ">>", line, col)
            if self._match("="): return Token(TokenType.GTE, ">=", line, col)
            return Token(TokenType.GT, ">", line, col)
        if ch == "=":
            if self._match("="): return Token(TokenType.EQ,     "==", line, col)
            return Token(TokenType.ASSIGN, "=", line, col)
        if ch == "!":
            if self._match("="): return Token(TokenType.NEQ,    "!=", line, col)
            return Token(TokenType.BANG, "!", line, col)
        if ch == "~": return Token(TokenType.TILDE,     "~",  line, col)
        if ch == "@": return Token(TokenType.AT,        "@",  line, col)
        if ch == "{": return Token(TokenType.LBRACE,    "{",  line, col)
        if ch == "}": return Token(TokenType.RBRACE,    "}",  line, col)
        if ch == "(": return Token(TokenType.LPAREN,    "(",  line, col)
        if ch == ")": return Token(TokenType.RPAREN,    ")",  line, col)
        if ch == "[": return Token(TokenType.LBRACKET,  "[",  line, col)
        if ch == "]": return Token(TokenType.RBRACKET,  "]",  line, col)
        if ch == ";": return Token(TokenType.SEMICOLON, ";",  line, col)
        if ch == ",": return Token(TokenType.COMMA,     ",",  line, col)
        if ch == ".": return Token(TokenType.DOT,       ".",  line, col)
        if ch == ":":
            if self._match(":"): return Token(TokenType.COLONCOLON, "::", line, col)
            return Token(TokenType.COLON, ":", line, col)
        if ch == "?":
            if self._match("?"): return Token(TokenType.QUESTION_QUESTION, "??", line, col)
            return Token(TokenType.QUESTION, "?", line, col)

        raise LexError(f"unexpected character {ch!r}", line, col)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self) -> List[Token]:
        """Lex the entire source string and return a flat list of tokens.

        Repeatedly skips whitespace/comments then dispatches to the
        appropriate _lex_* method based on the next character:

          Letter or _     → _lex_ident_or_keyword
          Digit           → _lex_number
          "               → _lex_string
          '               → _lex_char
          Anything else   → _lex_operator_or_punct

        The list is always terminated with a single EOF token. Any
        LexError raised by a sub-method propagates directly to the caller.
        """
        tokens: List[Token] = []
        while True:
            self._skip_whitespace_and_comments()
            if self._pos >= len(self._src):
                tokens.append(Token(TokenType.EOF, "", self._line, self._col))
                break
            line, col = self._line, self._col
            ch = self._peek()
            if ch.isalpha() or ch == "_":
                tokens.append(self._lex_ident_or_keyword(line, col))
            elif ch.isdigit():
                tokens.append(self._lex_number(line, col))
            elif ch == '"':
                tokens.append(self._lex_string(line, col))
            elif ch == "'":
                tokens.append(self._lex_char(line, col))
            else:
                tokens.append(self._lex_operator_or_punct(line, col))
        return tokens
