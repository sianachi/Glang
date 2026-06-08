from __future__ import annotations

from parser.ast_nodes import Program
from analyser.symbol_table import GlobalEnv
from analyser.monomorphize import Monomorphizer
from analyser.pass1_collector import Pass1Collector
from analyser.pass2_checker import Pass2Checker


class Analyser:
    def __init__(self) -> None:
        self.global_env = GlobalEnv()

    def analyse(self, program: Program) -> GlobalEnv:
        # Resolve generics first: rewrites templates and uses into concrete,
        # mangled instantiations in place, so the rest of the pipeline never
        # sees a type parameter or a GenericType.
        Monomorphizer().run(program)
        Pass1Collector(self.global_env).collect(program)
        Pass2Checker(self.global_env).check_program(program)
        return self.global_env
