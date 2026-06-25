from __future__ import annotations

from parser.ast_nodes import (
    Program, ClassDecl, FieldDecl, ConstructorDecl, Param,
    Block, AssignStmt, FieldAccessExpr, ThisExpr, IdentifierExpr, NamedType,
)
from analyser.symbol_table import GlobalEnv
from analyser.monomorphize import Monomorphizer
from analyser.namespace_resolver import NamespaceResolver
from analyser.pass1_collector import Pass1Collector
from analyser.pass2_checker import Pass2Checker


def _make_exception_decl() -> ClassDecl:
    """Synthesise the built-in Exception base class:

        class Exception {
            string message;
            Exception(string msg) { this.message = msg; }
        }
    """
    message_field = FieldDecl(
        name="message", type=NamedType("string"), access="public", is_const=False,
    )
    assign = AssignStmt(
        target=FieldAccessExpr(object=ThisExpr(), field_name="message"),
        op="=",
        value=IdentifierExpr(name="msg"),
    )
    constructor = ConstructorDecl(
        params=[Param(name="msg", type=NamedType("string"))],
        body=Block(stmts=[assign]),
        super_args=None,
    )
    return ClassDecl(
        name="Exception",
        fields=[message_field],
        static_fields=[],
        methods=[],
        superclass=None,
        interfaces=[],
        constructor=constructor,
        destructor=None,
        access="public",
        type_params=[],
        type_param_bounds={},
    )


class Analyser:
    def __init__(self) -> None:
        self.global_env = GlobalEnv()

    def analyse(self, program: Program) -> GlobalEnv:
        # Prepend the built-in Exception class so every pass sees it as a
        # normal declaration — no special-casing needed downstream.
        program.declarations.insert(0, _make_exception_decl())
        # Flatten namespaces first: members become ordinary top-level
        # declarations with qualified names ("math::abs"), so generics and
        # everything after run completely unaware of namespaces.
        NamespaceResolver().run(program)
        # Resolve generics next: rewrites templates and uses into concrete,
        # mangled instantiations in place, so the rest of the pipeline never
        # sees a type parameter or a GenericType.
        Monomorphizer().run(program)
        Pass1Collector(self.global_env).collect(program)
        Pass2Checker(self.global_env).check_program(program)
        return self.global_env
