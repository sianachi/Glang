from __future__ import annotations
from typing import List

from parser.ast_nodes import (
    Stmt, ReturnStmt, IfStmt, WhileStmt, DoWhileStmt, ForStmt, ForeachStmt,
    Block, UsingStmt, ThrowStmt, TryCatchStmt,
)


def always_returns(stmts: List[Stmt]) -> bool:
    for stmt in stmts:
        if _stmt_always_returns(stmt):
            return True
    return False


def _stmt_always_returns(stmt: Stmt) -> bool:
    if isinstance(stmt, ReturnStmt):
        return True

    if isinstance(stmt, ThrowStmt):
        return True

    if isinstance(stmt, TryCatchStmt):
        body_returns = always_returns(stmt.body.stmts)
        handlers_return = all(always_returns(c.body.stmts) for c in stmt.catches)
        return body_returns and handlers_return

    if isinstance(stmt, IfStmt):
        if stmt.else_branch is None:
            return False
        then_returns = always_returns(stmt.then_branch.stmts)
        else_returns = _stmt_always_returns(stmt.else_branch)
        return then_returns and else_returns

    if isinstance(stmt, Block):
        return always_returns(stmt.stmts)

    if isinstance(stmt, UsingStmt):
        # The resource is disposed before the return propagates, so a body
        # that always returns makes the using statement always return.
        return always_returns(stmt.body.stmts)

    if isinstance(stmt, (WhileStmt, DoWhileStmt, ForStmt, ForeachStmt)):
        return False

    return False
