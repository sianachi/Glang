from __future__ import annotations
from typing import List, Optional, Tuple

try:
    from .token_stream import TokenStream
    from .type_parser import TypeParser, _TYPE_KEYWORDS
    from ..lexer.token_types import TokenType
    from ..errors.errors import ParseError
    from .ast_nodes import (
        Expr, LiteralExpr, IdentifierExpr, NullExpr, ThisExpr, SuperExpr,
        UnaryExpr, AddressOfExpr, DerefExpr, CastExpr,
        NewExpr, DeleteExpr, AllocExpr, FreeExpr,
        BinaryExpr, CallExpr, MethodCallExpr, FieldAccessExpr,
        ArrowAccessExpr, IndexExpr,
    )
except ImportError:
    from parser.token_stream import TokenStream  # type: ignore
    from parser.type_parser import TypeParser, _TYPE_KEYWORDS  # type: ignore
    from lexer.token_types import TokenType  # type: ignore
    from errors.errors import ParseError  # type: ignore
    from parser.ast_nodes import (  # type: ignore
        Expr, LiteralExpr, IdentifierExpr, NullExpr, ThisExpr, SuperExpr,
        UnaryExpr, AddressOfExpr, DerefExpr, CastExpr,
        NewExpr, DeleteExpr, AllocExpr, FreeExpr,
        BinaryExpr, CallExpr, MethodCallExpr, FieldAccessExpr,
        ArrowAccessExpr, IndexExpr,
    )

_ASSIGN_OPS = {
    TokenType.ASSIGN,
    TokenType.PLUS_ASSIGN,
    TokenType.MINUS_ASSIGN,
    TokenType.STAR_ASSIGN,
    TokenType.SLASH_ASSIGN,
    TokenType.PERCENT_ASSIGN,
    TokenType.AMP_ASSIGN,
    TokenType.PIPE_ASSIGN,
    TokenType.CARET_ASSIGN,
    TokenType.LSHIFT_ASSIGN,
    TokenType.RSHIFT_ASSIGN,
}

_INFIX_BP: dict[TokenType, Tuple[int, int]] = {
    TokenType.OR:      (11, 12),
    TokenType.AND:     (21, 22),
    TokenType.PIPE:    (31, 32),
    TokenType.CARET:   (41, 42),
    TokenType.AMP:     (51, 52),
    TokenType.EQ:      (61, 62),
    TokenType.NEQ:     (61, 62),
    TokenType.LT:      (71, 72),
    TokenType.GT:      (71, 72),
    TokenType.LTE:     (71, 72),
    TokenType.GTE:     (71, 72),
    TokenType.LSHIFT:  (81, 82),
    TokenType.RSHIFT:  (81, 82),
    TokenType.PLUS:    (91, 92),
    TokenType.MINUS:   (91, 92),
    TokenType.STAR:    (101, 102),
    TokenType.SLASH:   (101, 102),
    TokenType.PERCENT: (101, 102),
    TokenType.DOT:     (141, 142),
    TokenType.ARROW:   (141, 142),
    TokenType.LBRACKET:(141, 0),
    TokenType.LPAREN:  (141, 0),
    # Assignment operators are handled at the statement level by StmtParser,
    # NOT consumed by the Pratt loop — they are absent from this table.
}


class ExprParser:
    def __init__(self, stream: TokenStream, type_parser: TypeParser) -> None:
        self._s = stream
        self._tp = type_parser

    def parse_expr(self, min_bp: int = 0) -> Expr:
        left = self._parse_prefix()

        while True:
            bp = self._infix_binding_power(self._s.peek())
            if bp is None:
                break
            left_bp, right_bp = bp
            if left_bp <= min_bp:
                break
            left = self._parse_postfix(left, right_bp)

        return left

    def parse_arg_list(self) -> List[Expr]:
        self._s.expect(TokenType.LPAREN)
        args: List[Expr] = []
        if not self._s.check(TokenType.RPAREN):
            args.append(self.parse_expr())
            while self._s.match(TokenType.COMMA):
                args.append(self.parse_expr())
        self._s.expect(TokenType.RPAREN)
        return args

    def _parse_prefix(self) -> Expr:
        tok = self._s.peek()

        if tok.type in (TokenType.BANG, TokenType.TILDE,
                        TokenType.PLUS_PLUS, TokenType.MINUS_MINUS):
            self._s.advance()
            operand = self._parse_prefix()
            return UnaryExpr(op=tok.value, operand=operand, line=tok.line, col=tok.col)

        if tok.type == TokenType.MINUS:
            self._s.advance()
            operand = self._parse_prefix()
            return UnaryExpr(op="-", operand=operand, line=tok.line, col=tok.col)

        if tok.type == TokenType.AMP:
            self._s.advance()
            operand = self._parse_prefix()
            return AddressOfExpr(operand=operand, line=tok.line, col=tok.col)

        if tok.type == TokenType.STAR:
            self._s.advance()
            operand = self._parse_prefix()
            return DerefExpr(operand=operand, line=tok.line, col=tok.col)

        if tok.type == TokenType.LPAREN:
            return self._parse_paren_or_cast()

        if tok.type == TokenType.KW_NEW:
            return self._parse_new()

        if tok.type == TokenType.KW_DELETE:
            self._s.advance()
            operand = self.parse_expr()
            return DeleteExpr(operand=operand, line=tok.line, col=tok.col)

        if tok.type == TokenType.KW_ALLOC:
            self._s.advance()
            self._s.expect(TokenType.LPAREN)
            t = self._tp.parse_type()
            self._s.expect(TokenType.RPAREN)
            return AllocExpr(type=t, line=tok.line, col=tok.col)

        if tok.type == TokenType.KW_FREE:
            self._s.advance()
            self._s.expect(TokenType.LPAREN)
            operand = self.parse_expr()
            self._s.expect(TokenType.RPAREN)
            return FreeExpr(operand=operand, line=tok.line, col=tok.col)

        if tok.type == TokenType.KW_THIS:
            self._s.advance()
            return ThisExpr(line=tok.line, col=tok.col)

        if tok.type == TokenType.KW_SUPER:
            self._s.advance()
            return SuperExpr(line=tok.line, col=tok.col)

        if tok.type == TokenType.KW_NULL:
            self._s.advance()
            return NullExpr(line=tok.line, col=tok.col)

        if tok.type == TokenType.KW_TRUE:
            self._s.advance()
            return LiteralExpr(kind="bool", value="true", line=tok.line, col=tok.col)

        if tok.type == TokenType.KW_FALSE:
            self._s.advance()
            return LiteralExpr(kind="bool", value="false", line=tok.line, col=tok.col)

        if tok.type == TokenType.INT_LIT:
            self._s.advance()
            return LiteralExpr(kind="int", value=tok.value, line=tok.line, col=tok.col)

        if tok.type == TokenType.FLOAT_LIT:
            self._s.advance()
            return LiteralExpr(kind="float", value=tok.value, line=tok.line, col=tok.col)

        if tok.type == TokenType.CHAR_LIT:
            self._s.advance()
            return LiteralExpr(kind="char", value=tok.value, line=tok.line, col=tok.col)

        if tok.type == TokenType.STRING_LIT:
            self._s.advance()
            return LiteralExpr(kind="string", value=tok.value, line=tok.line, col=tok.col)

        if tok.type == TokenType.IDENT:
            self._s.advance()
            return IdentifierExpr(name=tok.value, line=tok.line, col=tok.col)

        raise self._s.error(f"Unexpected token {tok.type.name!r} in expression")

    def _parse_paren_or_cast(self) -> Expr:
        lparen = self._s.advance()  # consume '('
        next_tok = self._s.peek()
        is_cast = False
        if next_tok.type in _TYPE_KEYWORDS:
            is_cast = True
        elif next_tok.type == TokenType.IDENT and self._s.peek(1).type == TokenType.RPAREN:
            is_cast = True

        if is_cast:
            t = self._tp.parse_type()
            self._s.expect(TokenType.RPAREN)
            operand = self._parse_prefix()
            return CastExpr(target_type=t, expr=operand, line=lparen.line, col=lparen.col)

        inner = self.parse_expr()
        self._s.expect(TokenType.RPAREN)
        return inner

    def _parse_new(self) -> Expr:
        tok = self._s.advance()  # consume 'new'
        name_tok = self._s.expect(TokenType.IDENT)
        args = self.parse_arg_list()
        return NewExpr(class_name=name_tok.value, args=args, line=tok.line, col=tok.col)

    def _parse_postfix(self, left: Expr, right_bp: int) -> Expr:
        tok = self._s.advance()  # consume the operator

        if tok.type == TokenType.DOT:
            name_tok = self._s.expect(TokenType.IDENT)
            if self._s.check(TokenType.LPAREN):
                args = self.parse_arg_list()
                return MethodCallExpr(
                    object=left, method=name_tok.value, args=args,
                    is_arrow=False, line=tok.line, col=tok.col,
                )
            return FieldAccessExpr(
                object=left, field_name=name_tok.value, line=tok.line, col=tok.col
            )

        if tok.type == TokenType.ARROW:
            name_tok = self._s.expect(TokenType.IDENT)
            if self._s.check(TokenType.LPAREN):
                args = self.parse_arg_list()
                return MethodCallExpr(
                    object=left, method=name_tok.value, args=args,
                    is_arrow=True, line=tok.line, col=tok.col,
                )
            return ArrowAccessExpr(
                pointer=left, field_name=name_tok.value, line=tok.line, col=tok.col
            )

        if tok.type == TokenType.LBRACKET:
            index = self.parse_expr()
            self._s.expect(TokenType.RBRACKET)
            return IndexExpr(array=left, index=index, line=tok.line, col=tok.col)

        if tok.type == TokenType.LPAREN:
            if not isinstance(left, IdentifierExpr):
                raise ParseError(
                    "Call target must be an identifier", tok.line, tok.col
                )
            args = []
            if not self._s.check(TokenType.RPAREN):
                args.append(self.parse_expr())
                while self._s.match(TokenType.COMMA):
                    args.append(self.parse_expr())
            self._s.expect(TokenType.RPAREN)
            return CallExpr(name=left.name, args=args, line=tok.line, col=tok.col)

        op = tok.value
        right = self.parse_expr(right_bp)
        return BinaryExpr(left=left, op=op, right=right, line=tok.line, col=tok.col)

    def _infix_binding_power(self, tok) -> Optional[Tuple[int, int]]:
        return _INFIX_BP.get(tok.type)
