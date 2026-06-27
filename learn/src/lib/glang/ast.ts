// The typed AST produced by the parser and consumed by the evaluator.

export interface TypeDesc {
  name: string
  isFloat: boolean
  ptr: number
  nullable: boolean
  arraySize: number | null
}

export type Expr =
  | { k: 'num'; v: number; isFloat: boolean }
  | { k: 'str'; v: string }
  | { k: 'char'; v: number }
  | { k: 'bool'; v: boolean }
  | { k: 'null' }
  | { k: 'var'; name: string }
  | { k: 'bin'; op: string; left: Expr; right: Expr }
  | { k: 'coalesce'; left: Expr; right: Expr }
  | { k: 'unary'; op: string; expr: Expr }
  | { k: 'preincdec'; op: string; expr: Expr }
  | { k: 'cast'; type: TypeDesc; expr: Expr }
  | { k: 'call'; callee: Expr; args: Expr[] }
  | { k: 'member'; obj: Expr; name: string }
  | { k: 'scope'; obj: Expr; name: string }
  | { k: 'arrow'; obj: Expr; name: string }
  | { k: 'index'; obj: Expr; index: Expr }

export interface BlockStmt {
  k: 'block'
  stmts: Stmt[]
}

export type Stmt =
  | BlockStmt
  | { k: 'decl'; type: TypeDesc; name: string; init: Expr | null }
  | { k: 'assign'; op: string; target: Expr; value: Expr }
  | { k: 'incdec'; op: string; target: Expr }
  | { k: 'if'; cond: Expr; then: Stmt; els: Stmt | null }
  | { k: 'while'; cond: Expr; body: Stmt }
  | { k: 'for'; init: Stmt | null; cond: Expr | null; post: Stmt | null; body: Stmt }
  | { k: 'return'; val: Expr | null }
  | { k: 'break' }
  | { k: 'continue' }
  | { k: 'exprstmt'; expr: Expr }

export interface Param {
  type: TypeDesc
  name: string
}

export interface FnDecl {
  k: 'fn'
  name: string
  retType: TypeDesc
  params: Param[]
  body: BlockStmt
}

export interface EnumVariant {
  name: string
  val: number
}

export interface EnumDecl {
  k: 'enum'
  name: string
  variants: EnumVariant[]
}

export type TopDecl = FnDecl | EnumDecl

export interface Program {
  k: 'program'
  decls: TopDecl[]
}
