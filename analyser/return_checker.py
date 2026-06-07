from __future__ import annotations
from typing import List

from parser.ast_nodes import (
    Stmt, ReturnStmt, IfStmt, WhileStmt, ForStmt, Block,
)


def always_returns(stmts: List[Stmt]) -> bool:
    for stmt in stmts:
        if _stmt_always_returns(stmt):
            return True
    return False


def _stmt_always_returns(stmt: Stmt) -> bool:
    if isinstance(stmt, ReturnStmt):
        return True

    if isinstance(stmt, IfStmt):
        if stmt.else_branch is None:
            return False
        then_returns = always_returns(stmt.then_branch.stmts)
        else_returns = _stmt_always_returns(stmt.else_branch)
        return then_returns and else_returns

    if isinstance(stmt, Block):
        return always_returns(stmt.stmts)

    if isinstance(stmt, (WhileStmt, ForStmt)):
        return False

    return False
