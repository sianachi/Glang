from __future__ import annotations

try:
    from .token_stream import TokenStream
    from ..lexer.token_types import TokenType
    from .ast_nodes import TypeNode, NamedType, PointerType, ArrayType
except ImportError:
    from parser.token_stream import TokenStream  # type: ignore
    from lexer.token_types import TokenType  # type: ignore
    from parser.ast_nodes import TypeNode, NamedType, PointerType, ArrayType  # type: ignore

_TYPE_KEYWORDS = {
    TokenType.KW_INT,
    TokenType.KW_FLOAT,
    TokenType.KW_BOOL,
    TokenType.KW_CHAR,
    TokenType.KW_STRING,
    TokenType.KW_VOID,
}

_TYPE_KEYWORD_NAMES = {
    TokenType.KW_INT:    "int",
    TokenType.KW_FLOAT:  "float",
    TokenType.KW_BOOL:   "bool",
    TokenType.KW_CHAR:   "char",
    TokenType.KW_STRING: "string",
    TokenType.KW_VOID:   "void",
}


def is_type_start(stream: TokenStream) -> bool:
    """Return True if the current token can begin a type annotation."""
    return stream.check(*_TYPE_KEYWORDS, TokenType.IDENT)


class TypeParser:
    def __init__(self, stream: TokenStream) -> None:
        self._s = stream

    def parse_type(self) -> TypeNode:
        tok = self._s.peek()
        if tok.type in _TYPE_KEYWORD_NAMES:
            self._s.advance()
            node: TypeNode = NamedType(
                name=_TYPE_KEYWORD_NAMES[tok.type], line=tok.line, col=tok.col
            )
        elif tok.type == TokenType.IDENT:
            self._s.advance()
            node = NamedType(name=tok.value, line=tok.line, col=tok.col)
        else:
            raise self._s.error(f"Expected type, got {tok.type.name!r}")

        while self._s.check(TokenType.STAR):
            star = self._s.advance()
            node = PointerType(base=node, line=star.line, col=star.col)

        if self._s.check(TokenType.LBRACKET):
            lbr = self._s.advance()
            size_tok = self._s.expect(TokenType.INT_LIT)
            self._s.expect(TokenType.RBRACKET)
            node = ArrayType(
                base=node, size=int(size_tok.value, 0), line=lbr.line, col=lbr.col
            )

        return node
