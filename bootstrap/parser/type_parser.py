from __future__ import annotations

from .token_stream import TokenStream
from lexer.token_types import TokenType
from errors.errors import ParseError
from .ast_nodes import (
    TypeNode, NamedType, PointerType, ArrayType, FunctionPointerType,
    GenericType, NullableType,
)

_TYPE_KEYWORDS = {
    TokenType.KW_INT,
    TokenType.KW_FLOAT,
    TokenType.KW_BOOL,
    TokenType.KW_CHAR,
    TokenType.KW_BYTE,
    TokenType.KW_STRING,
    TokenType.KW_VOID,
}

_TYPE_KEYWORD_NAMES = {
    TokenType.KW_INT:    "int",
    TokenType.KW_FLOAT:  "float",
    TokenType.KW_BOOL:   "bool",
    TokenType.KW_CHAR:   "char",
    TokenType.KW_BYTE:   "byte",
    TokenType.KW_STRING: "string",
    TokenType.KW_VOID:   "void",
}


def is_type_start(stream: TokenStream) -> bool:
    """Return True if the current token can begin a type annotation."""
    return stream.check(*_TYPE_KEYWORDS, TokenType.IDENT, TokenType.KW_FN)


class TypeParser:
    def __init__(self, stream: TokenStream) -> None:
        self._s = stream
        # Count of pending '>' tokens "owed" after splitting a '>>' (RSHIFT)
        # encountered while closing nested generic argument lists.
        self._pending_gt = 0

    def parse_type(self) -> TypeNode:
        tok = self._s.peek()
        if tok.type == TokenType.KW_FN:
            node = self._parse_function_pointer_type()
        elif tok.type in _TYPE_KEYWORD_NAMES:
            self._s.advance()
            node: TypeNode = NamedType(
                name=_TYPE_KEYWORD_NAMES[tok.type], line=tok.line, col=tok.col
            )
        elif tok.type == TokenType.IDENT:
            self._s.advance()
            name = tok.value
            while self._s.match(TokenType.COLONCOLON):
                name += "::" + self._s.expect(TokenType.IDENT).value
            if self._s.check(TokenType.LT):
                node = GenericType(
                    name=name, type_args=self.parse_type_args(),
                    line=tok.line, col=tok.col,
                )
            else:
                node = NamedType(name=name, line=tok.line, col=tok.col)
        else:
            raise self._s.error(f"Expected type, got {tok.type.name!r}")

        while self._s.check(TokenType.STAR):
            star = self._s.advance()
            node = PointerType(base=node, line=star.line, col=star.col)

        if self._s.check(TokenType.QUESTION):
            q = self._s.advance()
            if isinstance(node, (PointerType, FunctionPointerType)):
                raise ParseError(
                    "pointer types are already nullable; use 'T*' without '?'",
                    q.line, q.col,
                )
            node = NullableType(base=node, line=q.line, col=q.col)

        if self._s.check(TokenType.LBRACKET):
            lbr = self._s.advance()
            size_tok = self._s.expect(TokenType.INT_LIT)
            self._s.expect(TokenType.RBRACKET)
            node = ArrayType(
                base=node, size=int(size_tok.value, 0), line=lbr.line, col=lbr.col
            )

        return node

    def parse_type_args(self) -> list:
        """Parse ``<T1, T2, ...>`` starting at the opening ``<``. Handles a
        ``>>`` closing two nested argument lists by splitting it."""
        self._s.expect(TokenType.LT)
        args = [self.parse_type()]
        while self._s.match(TokenType.COMMA):
            args.append(self.parse_type())
        self._expect_gt()
        return args

    def _expect_gt(self) -> None:
        """Consume one closing ``>``. A ``>>`` (RSHIFT) token closes two levels:
        the first call consumes it and leaves one ``>`` pending for the outer
        argument list."""
        if self._pending_gt > 0:
            self._pending_gt -= 1
            return
        tok = self._s.peek()
        if tok.type == TokenType.GT:
            self._s.advance()
            return
        if tok.type == TokenType.RSHIFT:
            self._s.advance()
            self._pending_gt += 1
            return
        raise self._s.error("Expected '>' to close type arguments")

    def _parse_function_pointer_type(self) -> FunctionPointerType:
        tok = self._s.expect(TokenType.KW_FN)
        self._s.expect(TokenType.LPAREN)
        param_types: list[TypeNode] = []
        if not self._s.check(TokenType.RPAREN):
            param_types.append(self.parse_type())
            while self._s.match(TokenType.COMMA):
                param_types.append(self.parse_type())
        self._s.expect(TokenType.RPAREN)
        self._s.expect(TokenType.ARROW)
        return_type = self.parse_type()
        return FunctionPointerType(
            param_types=param_types,
            return_type=return_type,
            line=tok.line,
            col=tok.col,
        )
