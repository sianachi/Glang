from __future__ import annotations
from typing import List, Optional, Tuple

try:
    from .token_stream import TokenStream
    from .type_parser import TypeParser
    from .expr_parser import ExprParser
    from .stmt_parser import StmtParser
    from ..lexer.token_types import TokenType
    from ..errors.errors import ParseError
    from .ast_nodes import (
        Decl, Param, ImportDecl, FunctionDecl, ClassDecl, InterfaceDecl,
        FieldDecl, StaticFieldDecl, ConstructorDecl, DestructorDecl, MethodDecl,
        EnumDecl, EnumVariant,
    )
except ImportError:
    from parser.token_stream import TokenStream  # type: ignore
    from parser.type_parser import TypeParser  # type: ignore
    from parser.expr_parser import ExprParser  # type: ignore
    from parser.stmt_parser import StmtParser  # type: ignore
    from lexer.token_types import TokenType  # type: ignore
    from errors.errors import ParseError  # type: ignore
    from parser.ast_nodes import (  # type: ignore
        Decl, Param, ImportDecl, FunctionDecl, ClassDecl, InterfaceDecl,
        FieldDecl, StaticFieldDecl, ConstructorDecl, DestructorDecl, MethodDecl,
        EnumDecl, EnumVariant,
    )


_OVERLOADABLE_OPERATOR_TOKENS = {
    TokenType.PLUS,
    TokenType.MINUS,
    TokenType.STAR,
    TokenType.SLASH,
    TokenType.PERCENT,
    TokenType.EQ,
    TokenType.NEQ,
    TokenType.LT,
    TokenType.LTE,
    TokenType.GT,
    TokenType.GTE,
}


class DeclParser:
    def __init__(
        self,
        stream: TokenStream,
        type_parser: TypeParser,
        expr_parser: ExprParser,
        stmt_parser: StmtParser,
    ) -> None:
        self._s = stream
        self._tp = type_parser
        self._ep = expr_parser
        self._sp = stmt_parser

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def parse_import(self) -> ImportDecl:
        tok = self._s.expect(TokenType.KW_IMPORT)
        path_tok = self._s.expect(TokenType.STRING_LIT)
        self._s.expect(TokenType.SEMICOLON)
        return ImportDecl(path=path_tok.value, line=tok.line, col=tok.col)

    def parse_top_level_decl(self) -> Decl:
        access = "public"
        if self._s.check(TokenType.KW_PRIVATE, TokenType.KW_PROTECTED, TokenType.KW_PUBLIC):
            access = self._s.advance().value
        if self._s.check(TokenType.KW_CLASS):
            return self._parse_class(access=access)
        if self._s.check(TokenType.KW_INTERFACE):
            return self._parse_interface()
        if self._s.check(TokenType.KW_ENUM):
            return self._parse_enum()
        return self._parse_function()

    # ------------------------------------------------------------------
    # Enums
    # ------------------------------------------------------------------

    def _parse_enum(self) -> EnumDecl:
        tok = self._s.advance()  # consume 'enum'
        name_tok = self._s.expect(TokenType.IDENT)
        self._s.expect(TokenType.LBRACE)
        variants: List[EnumVariant] = []
        while not self._s.check(TokenType.RBRACE) and not self._s.is_at_end():
            v_tok = self._s.expect(TokenType.IDENT)
            explicit_val = None
            if self._s.match(TokenType.ASSIGN):
                val_tok = self._s.expect(TokenType.INT_LIT)
                explicit_val = int(val_tok.value, 0)
            variants.append(EnumVariant(
                name=v_tok.value, value=explicit_val,
                line=v_tok.line, col=v_tok.col,
            ))
            if not self._s.match(TokenType.COMMA):
                break
        self._s.expect(TokenType.RBRACE)
        return EnumDecl(name=name_tok.value, variants=variants,
                        line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------

    def _parse_function(self) -> FunctionDecl:
        ret_type = self._tp.parse_type()
        name_tok = self._s.expect(TokenType.IDENT)
        type_params = self._parse_type_params()
        params = self._parse_param_list()
        body = self._sp.parse_block()
        return FunctionDecl(
            name=name_tok.value, params=params, return_type=ret_type, body=body,
            type_params=type_params, line=name_tok.line, col=name_tok.col,
        )

    def _parse_type_params(self) -> List[str]:
        """Parse an optional ``<T, U, ...>`` type-parameter list. Returns the
        list of parameter names, or an empty list when absent."""
        if not self._s.match(TokenType.LT):
            return []
        params = [self._s.expect(TokenType.IDENT).value]
        while self._s.match(TokenType.COMMA):
            params.append(self._s.expect(TokenType.IDENT).value)
        self._s.expect(TokenType.GT)
        return params

    # ------------------------------------------------------------------
    # Classes
    # ------------------------------------------------------------------

    def _parse_class(self, access: str = "public") -> ClassDecl:
        tok = self._s.advance()  # consume 'class'
        name_tok = self._s.expect(TokenType.IDENT)
        type_params = self._parse_type_params()

        superclass: Optional[str] = None
        if self._s.match(TokenType.KW_EXTENDS):
            superclass = self._s.expect(TokenType.IDENT).value

        interfaces: List[str] = []
        if self._s.match(TokenType.KW_IMPLEMENTS):
            interfaces.append(self._s.expect(TokenType.IDENT).value)
            while self._s.match(TokenType.COMMA):
                interfaces.append(self._s.expect(TokenType.IDENT).value)

        static_fields, fields, constructor, destructor, methods = \
            self._parse_class_body(name_tok.value)

        return ClassDecl(
            name=name_tok.value,
            fields=fields,
            static_fields=static_fields,
            methods=methods,
            superclass=superclass,
            interfaces=interfaces,
            constructor=constructor,
            destructor=destructor,
            access=access,
            type_params=type_params,
            line=tok.line,
            col=tok.col,
        )

    def _parse_class_body(
        self, class_name: str
    ) -> Tuple[
        List[StaticFieldDecl],
        List[FieldDecl],
        Optional[ConstructorDecl],
        Optional[DestructorDecl],
        List[MethodDecl],
    ]:
        self._s.expect(TokenType.LBRACE)

        static_fields: List[StaticFieldDecl] = []
        fields: List[FieldDecl] = []
        constructor: Optional[ConstructorDecl] = None
        destructor: Optional[DestructorDecl] = None
        methods: List[MethodDecl] = []

        # phase: 0=static_fields, 1=instance_fields, 2=ctor/dtor, 3=methods
        phase = 0

        while not self._s.check(TokenType.RBRACE) and not self._s.is_at_end():
            # Consume optional access modifier
            access = "public"
            if self._s.check(TokenType.KW_PRIVATE, TokenType.KW_PROTECTED, TokenType.KW_PUBLIC):
                access = self._s.advance().value
            tok = self._s.peek()

            # Static member
            if tok.type == TokenType.KW_STATIC:
                self._s.advance()  # consume 'static'
                is_const = bool(self._s.match(TokenType.KW_CONST))
                ret_type = self._tp.parse_type()
                member_name, member_line, member_col = self._parse_member_name()
                if self._s.check(TokenType.LPAREN):
                    # Static method — belongs in the methods section
                    phase = 3
                    params = self._parse_param_list()
                    body = self._sp.parse_block()
                    methods.append(MethodDecl(
                        name=member_name, params=params, return_type=ret_type,
                        body=body, is_static=True, access=access,
                        line=member_line, col=member_col,
                    ))
                else:
                    if member_name.startswith("operator"):
                        raise self._s.error("operator overload must be a method")
                    # Static field
                    if phase > 0:
                        raise self._s.error(
                            "Static fields must appear before instance fields"
                        )
                    self._s.expect(TokenType.ASSIGN)
                    init = self._ep.parse_expr()
                    self._s.expect(TokenType.SEMICOLON)
                    static_fields.append(StaticFieldDecl(
                        name=member_name, type=ret_type, initializer=init,
                        is_const=is_const, access=access,
                        line=member_line, col=member_col,
                    ))
                continue

            # Destructor
            if tok.type == TokenType.TILDE:
                if phase > 2:
                    raise self._s.error("Destructor must appear before methods")
                phase = max(phase, 2)
                self._s.advance()  # consume '~'
                dtor_name = self._s.expect(TokenType.IDENT)
                if dtor_name.value != class_name:
                    raise ParseError(
                        f"Destructor name '{dtor_name.value}' must match "
                        f"class name '{class_name}'",
                        dtor_name.line, dtor_name.col,
                    )
                self._s.expect(TokenType.LPAREN)
                self._s.expect(TokenType.RPAREN)
                body = self._sp.parse_block()
                destructor = DestructorDecl(body=body, line=tok.line, col=tok.col)
                continue

            # Constructor: class name followed by '('
            if (tok.type == TokenType.IDENT and tok.value == class_name
                    and self._s.peek(1).type == TokenType.LPAREN):
                if phase > 2:
                    raise self._s.error("Constructor must appear before methods")
                phase = max(phase, 2)
                self._s.advance()  # consume class name
                params = self._parse_param_list()
                super_args = None
                if self._s.match(TokenType.COLON):
                    self._s.expect(TokenType.KW_SUPER)
                    super_args = self._ep.parse_arg_list()
                body = self._sp.parse_block()
                constructor = ConstructorDecl(
                    params=params, body=body, super_args=super_args,
                    line=tok.line, col=tok.col,
                )
                continue

            # Type-led member: instance field or instance method
            is_const = bool(self._s.match(TokenType.KW_CONST))
            ret_type = self._tp.parse_type()
            member_name, member_line, member_col = self._parse_member_name()

            if self._s.check(TokenType.LPAREN):
                phase = 3
                params = self._parse_param_list()
                body = self._sp.parse_block()
                methods.append(MethodDecl(
                    name=member_name, params=params, return_type=ret_type,
                    body=body, is_static=False, access=access,
                    line=member_line, col=member_col,
                ))
            else:
                if member_name.startswith("operator"):
                    raise self._s.error("operator overload must be a method")
                if phase > 1:
                    raise self._s.error(
                        "Instance fields must appear before constructor/destructor/methods"
                    )
                phase = max(phase, 1)
                self._s.expect(TokenType.SEMICOLON)
                fields.append(FieldDecl(
                    name=member_name, type=ret_type,
                    is_const=is_const, access=access,
                    line=member_line, col=member_col,
                ))

        self._s.expect(TokenType.RBRACE)
        return static_fields, fields, constructor, destructor, methods

    # ------------------------------------------------------------------
    # Interfaces
    # ------------------------------------------------------------------

    def _parse_interface(self) -> InterfaceDecl:
        tok = self._s.advance()  # consume 'interface'
        name_tok = self._s.expect(TokenType.IDENT)
        self._s.expect(TokenType.LBRACE)

        methods: List[MethodDecl] = []
        while not self._s.check(TokenType.RBRACE) and not self._s.is_at_end():
            ret_type = self._tp.parse_type()
            m_name, m_line, m_col = self._parse_member_name()
            params = self._parse_param_list()
            self._s.expect(TokenType.SEMICOLON)
            methods.append(MethodDecl(
                name=m_name, params=params, return_type=ret_type,
                body=None, is_static=False,  # type: ignore[arg-type]
                line=m_line, col=m_col,
            ))

        self._s.expect(TokenType.RBRACE)
        return InterfaceDecl(name=name_tok.value, methods=methods,
                             line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_member_name(self) -> Tuple[str, int, int]:
        name_tok = self._s.expect(TokenType.IDENT)
        if name_tok.value != "operator":
            return name_tok.value, name_tok.line, name_tok.col

        op_tok = self._s.peek()
        if op_tok.type == TokenType.LBRACKET:
            self._s.advance()
            self._s.expect(TokenType.RBRACKET)
            return "operator[]", name_tok.line, name_tok.col

        if op_tok.type not in _OVERLOADABLE_OPERATOR_TOKENS:
            raise ParseError(
                "Expected overloadable operator after 'operator'",
                op_tok.line, op_tok.col,
            )
        self._s.advance()
        return f"operator{op_tok.value}", name_tok.line, name_tok.col

    def _parse_param_list(self) -> List[Param]:
        self._s.expect(TokenType.LPAREN)
        params: List[Param] = []
        if not self._s.check(TokenType.RPAREN):
            is_const = bool(self._s.match(TokenType.KW_CONST))
            t = self._tp.parse_type()
            n = self._s.expect(TokenType.IDENT)
            params.append(Param(name=n.value, type=t, is_const=is_const, line=n.line, col=n.col))
            while self._s.match(TokenType.COMMA):
                is_const = bool(self._s.match(TokenType.KW_CONST))
                t = self._tp.parse_type()
                n = self._s.expect(TokenType.IDENT)
                params.append(Param(name=n.value, type=t, is_const=is_const, line=n.line, col=n.col))
        self._s.expect(TokenType.RPAREN)
        return params
