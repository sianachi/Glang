from __future__ import annotations
from typing import List

try:
    from .token_stream import TokenStream
    from .type_parser import TypeParser
    from .expr_parser import ExprParser
    from .stmt_parser import StmtParser
    from .decl_parser import DeclParser
    from ..lexer.lexer import Token
    from ..lexer.token_types import TokenType
    from .ast_nodes import Program
except ImportError:
    from parser.token_stream import TokenStream  # type: ignore
    from parser.type_parser import TypeParser  # type: ignore
    from parser.expr_parser import ExprParser  # type: ignore
    from parser.stmt_parser import StmtParser  # type: ignore
    from parser.decl_parser import DeclParser  # type: ignore
    from lexer.lexer import Token  # type: ignore
    from lexer.token_types import TokenType  # type: ignore
    from parser.ast_nodes import Program  # type: ignore


class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        stream = TokenStream(tokens)
        type_parser = TypeParser(stream)
        expr_parser = ExprParser(stream, type_parser)
        stmt_parser = StmtParser(stream, type_parser, expr_parser)
        expr_parser.set_stmt_parser(stmt_parser)
        decl_parser = DeclParser(stream, type_parser, expr_parser, stmt_parser)
        self._stream = stream
        self._decl_parser = decl_parser

    def parse(self) -> Program:
        imports = []
        declarations = []

        while not self._stream.is_at_end():
            if self._stream.check(TokenType.KW_IMPORT):
                imports.append(self._decl_parser.parse_import())
            else:
                declarations.append(self._decl_parser.parse_top_level_decl())

        return Program(imports=imports, declarations=declarations)
