import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer, Token
from lexer.token_types import TokenType
from errors.errors import LexError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tokenize(src: str) -> list[Token]:
    """Lex src and strip the trailing EOF token."""
    tokens = Lexer(src).tokenize()
    assert tokens[-1].type == TokenType.EOF
    return tokens[:-1]


def types(src: str) -> list[TokenType]:
    return [t.type for t in tokenize(src)]


def values(src: str) -> list[str]:
    return [t.value for t in tokenize(src)]


# ---------------------------------------------------------------------------
# Integer literals
# ---------------------------------------------------------------------------

class TestIntLiterals:
    def test_zero(self):
        assert values("0") == ["0"]

    def test_decimal(self):
        assert values("42") == ["42"]

    def test_multidigit(self):
        assert values("1234567890") == ["1234567890"]

    def test_underscore_separator(self):
        assert values("1_000_000") == ["1000000"]

    def test_hex_lowercase(self):
        assert values("0xff") == ["255"]

    def test_hex_uppercase_prefix(self):
        assert values("0XFF") == ["255"]

    def test_hex_mixed_case_digits(self):
        assert values("0xDeAdBeEf") == [str(0xDeAdBeEf)]

    def test_hex_with_underscores(self):
        assert values("0xDEAD_BEEF") == [str(0xDEADBEEF)]

    def test_binary(self):
        assert values("0b1010") == ["10"]

    def test_binary_uppercase_prefix(self):
        assert values("0B1111") == ["15"]

    def test_binary_with_underscores(self):
        assert values("0b1111_0000") == ["240"]

    def test_token_type_is_int_lit(self):
        assert types("0 42 0xFF 0b101") == [TokenType.INT_LIT] * 4


# ---------------------------------------------------------------------------
# Float literals
# ---------------------------------------------------------------------------

class TestFloatLiterals:
    def test_simple(self):
        assert values("3.14") == ["3.14"]

    def test_zero_point(self):
        assert values("0.5") == ["0.5"]

    def test_exponent_lowercase(self):
        assert values("1e10") == ["1e10"]

    def test_exponent_uppercase(self):
        assert values("1E10") == ["1E10"]

    def test_negative_exponent(self):
        assert values("1.5e-3") == ["1.5e-3"]

    def test_positive_exponent(self):
        assert values("2.0E+4") == ["2.0E+4"]

    def test_no_dot_with_exponent(self):
        assert values("1e5") == ["1e5"]

    def test_token_type_is_float_lit(self):
        assert types("3.14 1e10 1.5e-3") == [TokenType.FLOAT_LIT] * 3

    def test_int_followed_by_dot_method(self):
        # "42.foo" — the dot belongs to a member access, not the number
        toks = tokenize("42.foo")
        assert toks[0] == Token(TokenType.INT_LIT, "42", 1, 1)
        assert toks[1].type == TokenType.DOT
        assert toks[2] == Token(TokenType.IDENT, "foo", 1, 4)


# ---------------------------------------------------------------------------
# String literals
# ---------------------------------------------------------------------------

class TestStringLiterals:
    def test_simple(self):
        assert values('"hello"') == ["hello"]

    def test_empty(self):
        assert values('""') == [""]

    def test_escape_newline(self):
        assert values(r'"line\n"') == ["line\n"]

    def test_escape_tab(self):
        assert values(r'"col\t1"') == ["col\t1"]

    def test_escape_backslash(self):
        assert values(r'"\\"') == ["\\"]

    def test_escape_double_quote(self):
        assert values(r'"say \"hi\""') == ['say "hi"']

    def test_escape_hex(self):
        assert values(r'"\x41"') == ["A"]

    def test_escape_null_byte(self):
        assert values(r'"\0"') == ["\0"]

    def test_token_type(self):
        assert types('"foo"') == [TokenType.STRING_LIT]

    def test_unterminated_raises(self):
        with pytest.raises(LexError, match="unterminated string"):
            Lexer('"hello').tokenize()

    def test_newline_in_literal_raises(self):
        with pytest.raises(LexError, match="newline"):
            Lexer('"hel\nlo"').tokenize()


# ---------------------------------------------------------------------------
# Char literals
# ---------------------------------------------------------------------------

class TestCharLiterals:
    def test_simple(self):
        assert values("'a'") == ["a"]

    def test_escape_newline(self):
        assert values(r"'\n'") == ["\n"]

    def test_escape_tab(self):
        assert values(r"'\t'") == ["\t"]

    def test_escape_backslash(self):
        assert values(r"'\\'") == ["\\"]

    def test_escape_single_quote(self):
        assert values(r"'\''") == ["'"]

    def test_escape_hex(self):
        assert values(r"'\x41'") == ["A"]

    def test_token_type(self):
        assert types("'z'") == [TokenType.CHAR_LIT]

    def test_empty_raises(self):
        with pytest.raises(LexError, match="empty char"):
            Lexer("''").tokenize()

    def test_multi_char_raises(self):
        with pytest.raises(LexError, match="exactly one"):
            Lexer("'ab'").tokenize()

    def test_unterminated_raises(self):
        with pytest.raises(LexError, match="unterminated char"):
            Lexer("'").tokenize()


# ---------------------------------------------------------------------------
# Identifiers and keywords
# ---------------------------------------------------------------------------

class TestIdentsAndKeywords:
    def test_simple_ident(self):
        assert tokenize("foo")[0] == Token(TokenType.IDENT, "foo", 1, 1)

    def test_underscore_prefix(self):
        assert types("_count") == [TokenType.IDENT]

    def test_ident_with_digits(self):
        assert types("x1y2") == [TokenType.IDENT]

    def test_all_keywords(self):
        keywords = [
            ("int",        TokenType.KW_INT),
            ("float",      TokenType.KW_FLOAT),
            ("bool",       TokenType.KW_BOOL),
            ("char",       TokenType.KW_CHAR),
            ("byte",       TokenType.KW_BYTE),
            ("string",     TokenType.KW_STRING),
            ("void",       TokenType.KW_VOID),
            ("true",       TokenType.KW_TRUE),
            ("false",      TokenType.KW_FALSE),
            ("null",       TokenType.KW_NULL),
            ("class",      TokenType.KW_CLASS),
            ("interface",  TokenType.KW_INTERFACE),
            ("extends",    TokenType.KW_EXTENDS),
            ("implements", TokenType.KW_IMPLEMENTS),
            ("this",       TokenType.KW_THIS),
            ("super",      TokenType.KW_SUPER),
            ("new",        TokenType.KW_NEW),
            ("delete",     TokenType.KW_DELETE),
            ("static",     TokenType.KW_STATIC),
            ("alloc",      TokenType.KW_ALLOC),
            ("free",       TokenType.KW_FREE),
            ("if",         TokenType.KW_IF),
            ("else",       TokenType.KW_ELSE),
            ("while",      TokenType.KW_WHILE),
            ("for",        TokenType.KW_FOR),
            ("break",      TokenType.KW_BREAK),
            ("continue",   TokenType.KW_CONTINUE),
            ("return",     TokenType.KW_RETURN),
            ("import",     TokenType.KW_IMPORT),
        ]
        for word, expected_type in keywords:
            toks = tokenize(word)
            assert toks[0].type == expected_type, f"{word!r} should be {expected_type}"

    def test_keyword_prefix_is_ident(self):
        # "integer" starts with "int" but is not a keyword
        assert types("integer") == [TokenType.IDENT]


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class TestOperators:
    # Single-char
    def test_plus(self):         assert types("+")  == [TokenType.PLUS]
    def test_minus(self):        assert types("-")  == [TokenType.MINUS]
    def test_star(self):         assert types("*")  == [TokenType.STAR]
    def test_slash(self):        assert types("/")  == [TokenType.SLASH]
    def test_percent(self):      assert types("%")  == [TokenType.PERCENT]
    def test_amp(self):          assert types("&")  == [TokenType.AMP]
    def test_pipe(self):         assert types("|")  == [TokenType.PIPE]
    def test_caret(self):        assert types("^")  == [TokenType.CARET]
    def test_tilde(self):        assert types("~")  == [TokenType.TILDE]
    def test_bang(self):         assert types("!")  == [TokenType.BANG]
    def test_lt(self):           assert types("<")  == [TokenType.LT]
    def test_gt(self):           assert types(">")  == [TokenType.GT]
    def test_assign(self):       assert types("=")  == [TokenType.ASSIGN]

    # Two-char
    def test_plus_plus(self):    assert types("++") == [TokenType.PLUS_PLUS]
    def test_minus_minus(self):  assert types("--") == [TokenType.MINUS_MINUS]
    def test_arrow(self):        assert types("->") == [TokenType.ARROW]
    def test_and(self):          assert types("&&") == [TokenType.AND]
    def test_or(self):           assert types("||") == [TokenType.OR]
    def test_eq(self):           assert types("==") == [TokenType.EQ]
    def test_neq(self):          assert types("!=") == [TokenType.NEQ]
    def test_lte(self):          assert types("<=") == [TokenType.LTE]
    def test_gte(self):          assert types(">=") == [TokenType.GTE]
    def test_lshift(self):       assert types("<<") == [TokenType.LSHIFT]
    def test_rshift(self):       assert types(">>") == [TokenType.RSHIFT]
    def test_plus_assign(self):  assert types("+=") == [TokenType.PLUS_ASSIGN]
    def test_minus_assign(self): assert types("-=") == [TokenType.MINUS_ASSIGN]
    def test_star_assign(self):  assert types("*=") == [TokenType.STAR_ASSIGN]
    def test_slash_assign(self): assert types("/=") == [TokenType.SLASH_ASSIGN]
    def test_pct_assign(self):   assert types("%=") == [TokenType.PERCENT_ASSIGN]
    def test_amp_assign(self):   assert types("&=") == [TokenType.AMP_ASSIGN]
    def test_pipe_assign(self):  assert types("|=") == [TokenType.PIPE_ASSIGN]
    def test_caret_assign(self): assert types("^=") == [TokenType.CARET_ASSIGN]

    # Three-char
    def test_lshift_assign(self): assert types("<<=") == [TokenType.LSHIFT_ASSIGN]
    def test_rshift_assign(self): assert types(">>=") == [TokenType.RSHIFT_ASSIGN]

    def test_lt_not_consumed_by_lshift(self):
        # "< =" should be LT then ASSIGN, not LTE
        assert types("< =") == [TokenType.LT, TokenType.ASSIGN]


# ---------------------------------------------------------------------------
# Punctuation
# ---------------------------------------------------------------------------

class TestPunctuation:
    def test_all_punct(self):
        src = "{ } ( ) [ ] ; , . -> :"
        expected = [
            TokenType.LBRACE, TokenType.RBRACE,
            TokenType.LPAREN, TokenType.RPAREN,
            TokenType.LBRACKET, TokenType.RBRACKET,
            TokenType.SEMICOLON, TokenType.COMMA,
            TokenType.DOT, TokenType.ARROW, TokenType.COLON,
        ]
        assert types(src) == expected


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

class TestComments:
    def test_line_comment_stripped(self):
        assert tokenize("// nothing here") == []

    def test_line_comment_does_not_eat_next_line(self):
        assert types("// comment\n42") == [TokenType.INT_LIT]

    def test_block_comment_stripped(self):
        assert tokenize("/* hello */") == []

    def test_block_comment_inline(self):
        assert types("1 /* mid */ 2") == [TokenType.INT_LIT, TokenType.INT_LIT]

    def test_block_comment_multiline(self):
        assert tokenize("/* line1\nline2\nline3 */") == []

    def test_unterminated_block_comment_raises(self):
        with pytest.raises(LexError, match="unterminated block comment"):
            Lexer("/* oops").tokenize()


# ---------------------------------------------------------------------------
# Whitespace
# ---------------------------------------------------------------------------

class TestWhitespace:
    def test_spaces_ignored(self):
        assert types("1 2 3") == [TokenType.INT_LIT] * 3

    def test_tabs_ignored(self):
        assert types("1\t2") == [TokenType.INT_LIT] * 2

    def test_newlines_ignored(self):
        assert types("1\n2\n3") == [TokenType.INT_LIT] * 3


# ---------------------------------------------------------------------------
# Line and column tracking
# ---------------------------------------------------------------------------

class TestLineCol:
    def test_single_token_position(self):
        tok = tokenize("foo")[0]
        assert tok.line == 1 and tok.col == 1

    def test_col_advances(self):
        toks = tokenize("a b")
        assert toks[0].col == 1
        assert toks[1].col == 3

    def test_line_advances_on_newline(self):
        toks = tokenize("a\nb")
        assert toks[0].line == 1
        assert toks[1].line == 2

    def test_col_resets_after_newline(self):
        toks = tokenize("a\nb")
        assert toks[1].col == 1

    def test_eof_position(self):
        eof = Lexer("a").tokenize()[-1]
        assert eof.type == TokenType.EOF
        assert eof.line == 1


# ---------------------------------------------------------------------------
# EOF token
# ---------------------------------------------------------------------------

class TestEOF:
    def test_empty_source_gives_eof(self):
        toks = Lexer("").tokenize()
        assert len(toks) == 1
        assert toks[0].type == TokenType.EOF

    def test_eof_always_last(self):
        toks = Lexer("1 + 2").tokenize()
        assert toks[-1].type == TokenType.EOF


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestErrors:
    def test_unexpected_character(self):
        with pytest.raises(LexError, match="unexpected character"):
            Lexer("@").tokenize()

    def test_invalid_escape_in_string(self):
        with pytest.raises(LexError, match="unknown escape"):
            Lexer(r'"\q"').tokenize()

    def test_bad_hex_escape(self):
        with pytest.raises(LexError, match="invalid hex escape"):
            Lexer(r'"\xGG"').tokenize()

    def test_empty_hex_literal(self):
        with pytest.raises(LexError, match="empty hex literal"):
            Lexer("0x").tokenize()

    def test_empty_binary_literal(self):
        with pytest.raises(LexError, match="empty binary literal"):
            Lexer("0b").tokenize()

    def test_bad_exponent(self):
        with pytest.raises(LexError, match="expected digits after exponent"):
            Lexer("1e+x").tokenize()

    def test_lexerror_carries_position(self):
        try:
            Lexer("  @").tokenize()
        except LexError as e:
            assert e.line == 1
            assert e.col == 3


# ---------------------------------------------------------------------------
# Integration — realistic snippets
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_variable_declaration(self):
        toks = tokenize("int x = 42;")
        assert [t.type for t in toks] == [
            TokenType.KW_INT, TokenType.IDENT, TokenType.ASSIGN,
            TokenType.INT_LIT, TokenType.SEMICOLON,
        ]
        assert toks[1].value == "x"
        assert toks[3].value == "42"

    def test_function_signature(self):
        toks = tokenize("int add(int a, int b)")
        assert toks[0].type == TokenType.KW_INT
        assert toks[1].value == "add"
        assert toks[2].type == TokenType.LPAREN
        assert toks[-1].type == TokenType.RPAREN

    def test_arrow_access(self):
        assert types("p->field") == [
            TokenType.IDENT, TokenType.ARROW, TokenType.IDENT,
        ]

    def test_pointer_declaration(self):
        assert types("Dog* d") == [
            TokenType.IDENT, TokenType.STAR, TokenType.IDENT,
        ]

    def test_class_header(self):
        src = "class Dog extends Animal implements Printable {"
        tt = types(src)
        assert tt[0] == TokenType.KW_CLASS
        assert tt[2] == TokenType.KW_EXTENDS
        assert tt[4] == TokenType.KW_IMPLEMENTS
        assert tt[-1] == TokenType.LBRACE
