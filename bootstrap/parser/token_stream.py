from __future__ import annotations
from typing import List

from lexer.lexer import Token
from lexer.token_types import TokenType
from errors.errors import ParseError


class TokenStream:
    def __init__(self, tokens: List[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def peek(self, offset: int = 0) -> Token:
        idx = self._pos + offset
        if idx < len(self._tokens):
            return self._tokens[idx]
        return self._tokens[-1]  # EOF token

    def advance(self) -> Token:
        tok = self.peek()
        if tok.type != TokenType.EOF:
            self._pos += 1
        return tok

    def expect(self, type: TokenType) -> Token:
        tok = self.peek()
        if tok.type != type:
            raise self.error(f"Expected {type.name}, got {tok.type.name!r}")
        return self.advance()

    def match(self, *types: TokenType) -> bool:
        if self.peek().type in types:
            self.advance()
            return True
        return False

    def check(self, *types: TokenType) -> bool:
        return self.peek().type in types

    def mark(self) -> int:
        return self._pos

    def reset(self, pos: int) -> None:
        self._pos = pos

    def is_at_end(self) -> bool:
        return self.peek().type == TokenType.EOF

    def error(self, msg: str) -> ParseError:
        tok = self.peek()
        return ParseError(msg, tok.line, tok.col)
