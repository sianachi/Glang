from __future__ import annotations
from typing import List, Optional, Tuple

from .token_stream import TokenStream
from .type_parser import TypeParser
from .expr_parser import ExprParser
from .stmt_parser import StmtParser
from lexer.token_types import TokenType
from errors.errors import ParseError
from .ast_nodes import (
    Decl, Param, ImportDecl, FunctionDecl, ClassDecl, InterfaceDecl,
    FieldDecl, StaticFieldDecl, ConstructorDecl, DestructorDecl, MethodDecl,
    EnumDecl, EnumVariant, NamespaceDecl, UsingDecl, ModifierDecl,
    UnionDecl, UnionVariant, LiteralExpr, NullExpr, UnaryExpr,
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
        if self._s.check(TokenType.KW_NAMESPACE):
            return self._parse_namespace()
        if self._s.check(TokenType.KW_USING):
            return self._parse_using()
        if self._s.check(TokenType.KW_MODIFIER):
            return self._parse_modifier()
        access = "public"
        if self._s.check(TokenType.KW_PRIVATE, TokenType.KW_PROTECTED, TokenType.KW_PUBLIC):
            access = self._s.advance().value
        is_managed = bool(self._s.match(TokenType.KW_MANAGED))
        if self._s.check(TokenType.KW_CLASS):
            return self._parse_class(access=access, is_managed=is_managed)
        if is_managed:
            raise self._s.error("'managed' may only modify a class declaration")
        if self._s.check(TokenType.KW_INTERFACE):
            return self._parse_interface()
        if self._s.check(TokenType.KW_ENUM):
            return self._parse_enum()
        # 'union' is context-sensitive (not a keyword) to avoid breaking method names.
        tok2 = self._s.peek()
        if tok2.type == TokenType.IDENT and tok2.value == "union":
            return self._parse_union()
        return self._parse_function()

    # ------------------------------------------------------------------
    # Namespaces
    # ------------------------------------------------------------------

    def _parse_namespace(self) -> NamespaceDecl:
        tok = self._s.advance()  # consume 'namespace'
        name = self._parse_qualified_name()
        self._s.expect(TokenType.LBRACE)
        declarations: List[Decl] = []
        while not self._s.check(TokenType.RBRACE) and not self._s.is_at_end():
            if self._s.check(TokenType.KW_IMPORT):
                raise self._s.error("imports are not allowed inside a namespace")
            if self._s.check(TokenType.KW_USING):
                raise self._s.error(
                    "using declarations are not allowed inside a namespace"
                )
            declarations.append(self.parse_top_level_decl())
        self._s.expect(TokenType.RBRACE)
        return NamespaceDecl(name=name, declarations=declarations,
                             line=tok.line, col=tok.col)

    def _parse_using(self) -> UsingDecl:
        tok = self._s.advance()  # consume 'using'
        if self._s.check(TokenType.LPAREN):
            raise self._s.error(
                "'using (...)' is a statement; it must appear inside a function body"
            )
        if self._s.match(TokenType.KW_NAMESPACE):
            name = self._parse_qualified_name()
            self._s.expect(TokenType.SEMICOLON)
            return UsingDecl(name=name, is_namespace=True,
                             line=tok.line, col=tok.col)
        name = self._parse_qualified_name()
        if "::" not in name:
            raise ParseError(
                f"using declaration needs a qualified name like 'ns::{name}' "
                f"(or 'using namespace {name};')",
                tok.line, tok.col,
            )
        self._s.expect(TokenType.SEMICOLON)
        return UsingDecl(name=name, is_namespace=False,
                         line=tok.line, col=tok.col)

    def _parse_qualified_name(self) -> str:
        name = self._s.expect(TokenType.IDENT).value
        while self._s.match(TokenType.COLONCOLON):
            name += "::" + self._s.expect(TokenType.IDENT).value
        return name

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

    def _parse_union(self) -> UnionDecl:
        tok = self._s.advance()  # consume IDENT 'union'
        name_tok = self._s.expect(TokenType.IDENT)
        type_params: List[str] = []
        if self._s.match(TokenType.LT):
            while True:
                tp_tok = self._s.expect(TokenType.IDENT)
                type_params.append(tp_tok.value)
                if not self._s.match(TokenType.COMMA):
                    break
            self._s.expect(TokenType.GT)
        self._s.expect(TokenType.LBRACE)
        variants: List[UnionVariant] = []
        while not self._s.check(TokenType.RBRACE) and not self._s.is_at_end():
            v_tok = self._s.expect(TokenType.IDENT)
            self._s.expect(TokenType.LBRACE)
            fields: List[FieldDecl] = []
            while not self._s.check(TokenType.RBRACE) and not self._s.is_at_end():
                f_type = self._tp.parse_type()
                f_name = self._s.expect(TokenType.IDENT)
                self._s.expect(TokenType.SEMICOLON)
                fields.append(FieldDecl(
                    name=f_name.value, type=f_type,
                    line=f_name.line, col=f_name.col,
                ))
            self._s.expect(TokenType.RBRACE)
            variants.append(UnionVariant(
                name=v_tok.value, fields=fields,
                line=v_tok.line, col=v_tok.col,
            ))
        self._s.expect(TokenType.RBRACE)
        return UnionDecl(
            name=name_tok.value, type_params=type_params, variants=variants,
            line=tok.line, col=tok.col,
        )

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------

    def _parse_function(self) -> FunctionDecl:
        ret_type = self._tp.parse_type()
        name_tok = self._s.expect(TokenType.IDENT)
        type_params, type_param_bounds = self._parse_type_params()
        params = self._parse_param_list()
        body = self._sp.parse_block()
        return FunctionDecl(
            name=name_tok.value, params=params, return_type=ret_type, body=body,
            type_params=type_params, type_param_bounds=type_param_bounds,
            line=name_tok.line, col=name_tok.col,
        )

    def _parse_type_params(self) -> Tuple[List[str], dict]:
        """Parse an optional ``<T, U, ...>`` type-parameter list.

        Bounds use ``T extends Bound``. The returned names list intentionally
        stays plain strings for compatibility with older tests and passes.
        """
        if not self._s.match(TokenType.LT):
            return [], {}
        params: List[str] = []
        bounds = {}
        self._parse_one_type_param(params, bounds)
        while self._s.match(TokenType.COMMA):
            self._parse_one_type_param(params, bounds)
        self._s.expect(TokenType.GT)
        return params, bounds

    def _parse_one_type_param(self, params: List[str], bounds: dict) -> None:
        name_tok = self._s.expect(TokenType.IDENT)
        params.append(name_tok.value)
        if self._s.match(TokenType.KW_EXTENDS):
            # `T extends A & B & ...` — a type parameter may carry several bounds.
            bs = [self._tp.parse_type()]
            while self._s.match(TokenType.AMP):
                bs.append(self._tp.parse_type())
            bounds[name_tok.value] = bs

    # ------------------------------------------------------------------
    # Classes
    # ------------------------------------------------------------------

    def _parse_class(self, access: str = "public", is_managed: bool = False) -> ClassDecl:
        tok = self._s.advance()  # consume 'class'
        name_tok = self._s.expect(TokenType.IDENT)
        type_params, type_param_bounds = self._parse_type_params()

        superclass: Optional[str] = None
        if self._s.match(TokenType.KW_EXTENDS):
            superclass = self._parse_qualified_name()

        interfaces: List[str] = []
        if self._s.match(TokenType.KW_IMPLEMENTS):
            interfaces.append(self._parse_qualified_name())
            while self._s.match(TokenType.COMMA):
                interfaces.append(self._parse_qualified_name())

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
            is_managed=is_managed,
            type_params=type_params,
            type_param_bounds=type_param_bounds,
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
    # Modifiers
    # ------------------------------------------------------------------

    def _parse_modifier(self) -> ModifierDecl:
        tok = self._s.advance()  # consume 'modifier'
        type_params: List[str] = []
        if self._s.match(TokenType.LT):
            while True:
                tp_tok = self._s.expect(TokenType.IDENT)
                type_params.append(tp_tok.value)
                if not self._s.match(TokenType.COMMA):
                    break
            self._s.expect(TokenType.GT)
        self._s.expect(TokenType.KW_FOR)
        target = self._tp.parse_type()
        self._s.expect(TokenType.LBRACE)
        methods: List[MethodDecl] = []
        while not self._s.check(TokenType.RBRACE) and not self._s.is_at_end():
            access = "public"
            if self._s.check(TokenType.KW_PRIVATE, TokenType.KW_PROTECTED, TokenType.KW_PUBLIC):
                access = self._s.advance().value
            ret_type = self._tp.parse_type()
            name, m_line, m_col = self._parse_member_name()
            params = self._parse_param_list()
            body = self._sp.parse_block()
            methods.append(MethodDecl(
                name=name, params=params, return_type=ret_type,
                body=body, is_static=False, access=access,
                line=m_line, col=m_col,
            ))
        self._s.expect(TokenType.RBRACE)
        return ModifierDecl(
            type_params=type_params, target=target, methods=methods,
            line=tok.line, col=tok.col,
        )

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

    @staticmethod
    def _is_const_default(e) -> bool:
        # Defaults are restricted to constant expressions so they need no
        # namespace/monomorphization processing when spliced into call sites.
        if isinstance(e, (LiteralExpr, NullExpr)):
            return True
        if isinstance(e, UnaryExpr) and e.op in ("-", "+"):
            return DeclParser._is_const_default(e.operand)
        return False

    def _parse_one_param(self) -> Param:
        is_const = bool(self._s.match(TokenType.KW_CONST))
        t = self._tp.parse_type()
        n = self._s.expect(TokenType.IDENT)
        default = None
        if self._s.match(TokenType.ASSIGN):
            default = self._ep.parse_expr()
            if not self._is_const_default(default):
                raise ParseError(
                    f"default value for '{n.value}' must be a constant expression",
                    n.line, n.col,
                )
        return Param(name=n.value, type=t, is_const=is_const, default=default,
                     line=n.line, col=n.col)

    def _parse_param_list(self) -> List[Param]:
        self._s.expect(TokenType.LPAREN)
        params: List[Param] = []
        if not self._s.check(TokenType.RPAREN):
            params.append(self._parse_one_param())
            while self._s.match(TokenType.COMMA):
                params.append(self._parse_one_param())
        self._s.expect(TokenType.RPAREN)
        # A parameter with a default may not be followed by one without.
        seen_default = False
        for p in params:
            if p.default is not None:
                seen_default = True
            elif seen_default:
                raise ParseError(
                    f"non-default parameter '{p.name}' follows a default parameter",
                    p.line, p.col,
                )
        return params
