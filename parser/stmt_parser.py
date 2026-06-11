from __future__ import annotations

try:
    from .token_stream import TokenStream
    from .type_parser import TypeParser
    from .expr_parser import ExprParser, _ASSIGN_OPS
    from ..lexer.token_types import TokenType
    from ..errors.errors import ParseError
    from .ast_nodes import (
        Stmt, Block, VarDecl, AssignStmt, IfStmt, WhileStmt,
        ForStmt, BreakStmt, ContinueStmt, ReturnStmt, NamedType,
        UsingStmt,
    )
except ImportError:
    from parser.token_stream import TokenStream  # type: ignore
    from parser.type_parser import TypeParser  # type: ignore
    from parser.expr_parser import ExprParser, _ASSIGN_OPS  # type: ignore
    from lexer.token_types import TokenType  # type: ignore
    from errors.errors import ParseError  # type: ignore
    from parser.ast_nodes import (  # type: ignore
        Stmt, Block, VarDecl, AssignStmt, IfStmt, WhileStmt,
        ForStmt, BreakStmt, ContinueStmt, ReturnStmt, NamedType,
        UsingStmt,
    )

_TYPE_KWS = {
    TokenType.KW_INT, TokenType.KW_FLOAT, TokenType.KW_BOOL,
    TokenType.KW_CHAR, TokenType.KW_BYTE, TokenType.KW_STRING, TokenType.KW_VOID,
    TokenType.KW_FN,
}


class StmtParser:
    def __init__(
        self,
        stream: TokenStream,
        type_parser: TypeParser,
        expr_parser: ExprParser,
    ) -> None:
        self._s = stream
        self._tp = type_parser
        self._ep = expr_parser

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def parse_block(self) -> Block:
        tok = self._s.expect(TokenType.LBRACE)
        stmts = []
        while not self._s.check(TokenType.RBRACE) and not self._s.is_at_end():
            stmts.append(self.parse_statement())
        self._s.expect(TokenType.RBRACE)
        return Block(stmts=stmts, line=tok.line, col=tok.col)

    def parse_statement(self) -> Stmt:
        tok = self._s.peek()

        if tok.type == TokenType.LBRACE:
            return self.parse_block()
        if tok.type == TokenType.KW_IF:
            return self._parse_if()
        if tok.type == TokenType.KW_WHILE:
            return self._parse_while()
        if tok.type == TokenType.KW_FOR:
            return self._parse_for()
        if tok.type == TokenType.KW_RETURN:
            return self._parse_return()
        if tok.type == TokenType.KW_USING:
            return self._parse_using()
        if tok.type == TokenType.KW_BREAK:
            self._s.advance()
            self._s.expect(TokenType.SEMICOLON)
            return BreakStmt(line=tok.line, col=tok.col)
        if tok.type == TokenType.KW_CONTINUE:
            self._s.advance()
            self._s.expect(TokenType.SEMICOLON)
            return ContinueStmt(line=tok.line, col=tok.col)

        if self._is_var_decl_start():
            return self._parse_var_decl()

        return self._parse_assign_or_expr_stmt()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _is_var_decl_start(self) -> bool:
        tok = self._s.peek()
        if tok.type == TokenType.KW_CONST:
            return True
        if tok.type in _TYPE_KWS:
            return True
        if tok.type != TokenType.IDENT:
            return False
        # User-defined type name followed by a variable name: `Dog d`.
        if self._s.peek(1).type == TokenType.IDENT:
            return True
        # Generic type declaration: `List<int> xs = ...`, `Map<K,V>* p = ...`.
        # Trial-parse the type; require a trailing `name =` so a discarded
        # comparison statement (`a < b > c;`) is not mistaken for a declaration.
        if self._s.peek(1).type == TokenType.LT:
            return self._looks_like_generic_var_decl()
        # Qualified type declaration: `ns::Color c = ...`, `ns::List<int>* p = ...`.
        if self._s.peek(1).type == TokenType.COLONCOLON:
            return self._looks_like_qualified_var_decl()
        # User-defined pointer type: `Dog* d = ...`, `Dog** d = ...`.
        # We require the trailing `=` to disambiguate from a multiplication
        # expression statement (`a * b;`): `IDENT STAR+ IDENT =` is never a
        # valid expression, since `a * b` is not an assignable lvalue.
        i = 1
        while self._s.peek(i).type == TokenType.STAR:
            i += 1
        if (
            i > 1
            and self._s.peek(i).type == TokenType.IDENT
            and self._s.peek(i + 1).type == TokenType.ASSIGN
        ):
            return True
        return False

    def _looks_like_generic_var_decl(self) -> bool:
        mark = self._s.mark()
        saved_pending = self._tp._pending_gt
        try:
            self._tp.parse_type()
            return (
                self._s.check(TokenType.IDENT)
                and self._s.peek(1).type == TokenType.ASSIGN
            )
        except ParseError:
            return False
        finally:
            self._s.reset(mark)
            self._tp._pending_gt = saved_pending

    def _looks_like_qualified_var_decl(self) -> bool:
        """Disambiguate `ns::Type x = ...` from an expression statement that
        starts with a qualified name (`ns::fn();`, `ns::x * y;`). Trial-parse
        a type; it is a declaration only when a variable name follows — and,
        for non-plain types, an `=` too, since `ns::x * y;` is a discarded
        multiplication, never a declaration."""
        mark = self._s.mark()
        saved_pending = self._tp._pending_gt
        try:
            t = self._tp.parse_type()
            if not self._s.check(TokenType.IDENT):
                return False
            if isinstance(t, NamedType):
                return True
            return self._s.peek(1).type == TokenType.ASSIGN
        except ParseError:
            return False
        finally:
            self._s.reset(mark)
            self._tp._pending_gt = saved_pending

    def _parse_var_decl(self) -> VarDecl:
        is_const = bool(self._s.match(TokenType.KW_CONST))
        type_node = self._tp.parse_type()
        name_tok = self._s.expect(TokenType.IDENT)

        if not self._s.check(TokenType.ASSIGN):
            raise self._s.error("Variable declaration requires an initialiser")
        self._s.expect(TokenType.ASSIGN)
        init = self._ep.parse_expr()

        if self._s.check(TokenType.COMMA):
            raise self._s.error("Only one variable per declaration statement")

        self._s.expect(TokenType.SEMICOLON)
        return VarDecl(
            name=name_tok.value, type=type_node, initializer=init,
            is_const=is_const,
            line=name_tok.line, col=name_tok.col,
        )

    def _parse_assign_or_expr_stmt(self, *, consume_semi: bool = True) -> Stmt:
        expr = self._ep.parse_expr()

        if self._s.check(*_ASSIGN_OPS):
            op_tok = self._s.advance()
            rhs = self._ep.parse_expr()
            if consume_semi:
                self._s.expect(TokenType.SEMICOLON)
            return AssignStmt(
                target=expr, op=op_tok.value, value=rhs,
                line=op_tok.line, col=op_tok.col,
            )

        if consume_semi:
            self._s.expect(TokenType.SEMICOLON)
        return expr

    def _parse_if(self) -> IfStmt:
        tok = self._s.advance()  # consume 'if'
        self._s.expect(TokenType.LPAREN)
        cond = self._ep.parse_expr()
        self._s.expect(TokenType.RPAREN)
        then_branch = self.parse_block()

        else_branch = None
        if self._s.match(TokenType.KW_ELSE):
            if self._s.check(TokenType.KW_IF):
                else_branch = self._parse_if()
            else:
                else_branch = self.parse_block()

        return IfStmt(
            condition=cond, then_branch=then_branch, else_branch=else_branch,
            line=tok.line, col=tok.col,
        )

    def _parse_while(self) -> WhileStmt:
        tok = self._s.advance()  # consume 'while'
        self._s.expect(TokenType.LPAREN)
        cond = self._ep.parse_expr()
        self._s.expect(TokenType.RPAREN)
        body = self.parse_block()
        return WhileStmt(condition=cond, body=body, line=tok.line, col=tok.col)

    def _parse_for(self) -> ForStmt:
        tok = self._s.advance()  # consume 'for'
        self._s.expect(TokenType.LPAREN)
        init = self._parse_var_decl()         # consumes its trailing ';'
        cond = self._ep.parse_expr()
        self._s.expect(TokenType.SEMICOLON)
        post = self._parse_assign_or_expr_stmt(consume_semi=False)  # no ';' before ')'
        self._s.expect(TokenType.RPAREN)
        body = self.parse_block()
        return ForStmt(init=init, condition=cond, post=post, body=body,
                       line=tok.line, col=tok.col)

    def _parse_using(self) -> UsingStmt:
        tok = self._s.advance()  # consume 'using'
        if not self._s.check(TokenType.LPAREN):
            raise self._s.error(
                "expected '(' after 'using' "
                "(namespace imports belong at the top level of a file)"
            )
        self._s.expect(TokenType.LPAREN)
        type_node = self._tp.parse_type()
        name_tok = self._s.expect(TokenType.IDENT)
        if not self._s.check(TokenType.ASSIGN):
            raise self._s.error("'using' resource requires an initialiser")
        self._s.expect(TokenType.ASSIGN)
        init = self._ep.parse_expr()
        self._s.expect(TokenType.RPAREN)
        body = self.parse_block()
        # The resource variable is implicitly const, as in C#.
        decl = VarDecl(
            name=name_tok.value, type=type_node, initializer=init,
            is_const=True, line=name_tok.line, col=name_tok.col,
        )
        return UsingStmt(decl=decl, body=body, line=tok.line, col=tok.col)

    def _parse_return(self) -> ReturnStmt:
        tok = self._s.advance()  # consume 'return'
        if self._s.check(TokenType.SEMICOLON):
            self._s.advance()
            return ReturnStmt(value=None, line=tok.line, col=tok.col)
        value = self._ep.parse_expr()
        self._s.expect(TokenType.SEMICOLON)
        return ReturnStmt(value=value, line=tok.line, col=tok.col)
