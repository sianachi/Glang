// Recursive-descent parser with Pratt precedence for expressions. Produces the
// typed AST in ./ast.ts.
import { GlangError } from './values.ts'
import { lex, TYPE_WORDS, type Token } from './lexer.ts'
import type {
  BlockStmt, EnumDecl, Expr, FnDecl, Param, Program, Stmt, TopDecl, TypeDesc,
} from './ast.ts'

// Expression precedence levels, low to high (mirrors the spec's table).
const BIN: string[][] = [
  ['||'], ['&&'], ['|'], ['^'], ['&'],
  ['==', '!='], ['<', '>', '<=', '>='], ['<<', '>>'],
  ['+', '-'], ['*', '/', '%'],
]

export function parse(src: string): Program {
  const toks = lex(src)
  let p = 0
  const peek = (k = 0): Token => toks[p + k]
  const at = (t: string) => toks[p].t === t
  const next = (): Token => toks[p++]
  const expect = (t: string): Token => {
    if (toks[p].t !== t) {
      throw new GlangError(`Expected '${t}' but found '${toks[p].v ?? toks[p].t}' (line ${toks[p].line})`, toks[p].line)
    }
    return toks[p++]
  }

  const isTypeStart = (): boolean => {
    const tk = peek()
    if (TYPE_WORDS.has(tk.t)) return true
    // Class/enum-style type: Uppercase identifier followed by id, '*', '<', or '['
    if (tk.t === 'id' && /^[A-Z]/.test(String(tk.v))) {
      const nx = peek(1)
      return !!nx && (nx.t === 'id' || nx.t === '*' || nx.t === '<' || nx.t === '[')
    }
    return false
  }

  const parseType = (): TypeDesc => {
    let name: string
    if (TYPE_WORDS.has(peek().t)) name = next().t
    else name = String(expect('id').v)
    const isFloat = name === 'float'
    if (at('<')) {
      let depth = 0
      do {
        if (at('<')) depth++
        if (at('>')) depth--
        next()
      } while (depth > 0 && !at('eof'))
    }
    let ptr = 0
    while (at('*')) { next(); ptr++ }
    let nullable = false
    if (at('?')) { next(); nullable = true }
    let arraySize: number | null = null
    if (at('[')) {
      next()
      if (!at(']')) arraySize = Number(next().v)
      expect(']')
    }
    return { name, isFloat, ptr, nullable, arraySize }
  }

  const parseEnum = (): EnumDecl => {
    expect('enum')
    const name = String(expect('id').v)
    expect('{')
    const variants = []
    let nextVal = 0
    while (!at('}')) {
      const vn = String(expect('id').v)
      let val = nextVal
      if (at('=')) {
        next()
        const sign = at('-') ? (next(), -1) : 1
        val = sign * Number(next().v)
      }
      variants.push({ name: vn, val })
      nextVal = val + 1
      if (at(',')) next()
    }
    expect('}')
    return { k: 'enum', name, variants }
  }

  const parseFunction = (): FnDecl => {
    const retType = parseType()
    const name = String(expect('id').v)
    expect('(')
    const params: Param[] = []
    while (!at(')')) {
      const pt = parseType()
      const pn = String(expect('id').v)
      params.push({ type: pt, name: pn })
      if (at(',')) next()
    }
    expect(')')
    const body = parseBlock()
    return { k: 'fn', name, retType, params, body }
  }

  const parseTopLevel = (): TopDecl => {
    if (at('enum')) return parseEnum()
    const save = p
    if (isTypeStart() || TYPE_WORDS.has(peek().t)) {
      parseType()
      if (at('id') && peek(1).t === '(') {
        p = save
        return parseFunction()
      }
    }
    p = save
    throw new GlangError(
      `The in-browser runner only executes functions and enums at the top level. ` +
      `Found '${peek().v ?? peek().t}' (line ${peek().line}).`,
      peek().line,
    )
  }

  const parseBlock = (): BlockStmt => {
    expect('{')
    const stmts: Stmt[] = []
    while (!at('}') && !at('eof')) stmts.push(parseStmt())
    expect('}')
    return { k: 'block', stmts }
  }

  const parseStmt = (): Stmt => {
    const tk = peek()
    if (tk.t === '{') return parseBlock()
    if (tk.t === 'if') return parseIf()
    if (tk.t === 'while') return parseWhile()
    if (tk.t === 'for') return parseFor()
    if (tk.t === 'return') {
      next()
      let val: Expr | null = null
      if (!at(';')) val = parseExpr()
      expect(';')
      return { k: 'return', val }
    }
    if (tk.t === 'break') { next(); expect(';'); return { k: 'break' } }
    if (tk.t === 'continue') { next(); expect(';'); return { k: 'continue' } }
    if (tk.t === '++' || tk.t === '--') {
      const op = next().t
      const target = parseUnary()
      expect(';')
      return { k: 'incdec', op, target }
    }

    // declaration?  Type name = ... ;
    if (isTypeStart()) {
      const save = p
      const type = parseType()
      if (at('id')) {
        const name = String(next().v)
        let init: Expr | null = null
        if (at('=')) { next(); init = parseExpr() }
        expect(';')
        return { k: 'decl', type, name, init }
      }
      p = save
    }

    // expression / assignment statement
    const expr = parseExpr()
    const assignOps = ['=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=']
    if (assignOps.includes(peek().t)) {
      const op = next().t
      const value = parseExpr()
      expect(';')
      return { k: 'assign', op, target: expr, value }
    }
    expect(';')
    return { k: 'exprstmt', expr }
  }

  const parseIf = (): Stmt => {
    expect('if')
    expect('(')
    const cond = parseExpr()
    expect(')')
    const then = parseBlock()
    let els: Stmt | null = null
    if (at('else')) {
      next()
      els = at('if') ? parseIf() : parseBlock()
    }
    return { k: 'if', cond, then, els }
  }

  const parseWhile = (): Stmt => {
    expect('while')
    expect('(')
    const cond = parseExpr()
    expect(')')
    return { k: 'while', cond, body: parseBlock() }
  }

  const parseFor = (): Stmt => {
    expect('for')
    expect('(')
    let init: Stmt | null = null
    if (!at(';')) {
      if (isTypeStart()) {
        const type = parseType()
        const name = String(expect('id').v)
        let iv: Expr | null = null
        if (at('=')) { next(); iv = parseExpr() }
        init = { k: 'decl', type, name, init: iv }
      } else {
        const target = parseExpr()
        const op = next().t
        const value = parseExpr()
        init = { k: 'assign', op, target, value }
      }
    }
    expect(';')
    const cond = at(';') ? null : parseExpr()
    expect(';')
    let post: Stmt | null = null
    if (!at(')')) {
      if (at('++') || at('--')) {
        const op = next().t
        post = { k: 'incdec', op, target: parseUnary() }
      } else {
        const target = parseExpr()
        const op = next().t
        const value = parseExpr()
        post = { k: 'assign', op, target, value }
      }
    }
    expect(')')
    return { k: 'for', init, cond, post, body: parseBlock() }
  }

  const parseExpr = (): Expr => parseCoalesce()

  const parseCoalesce = (): Expr => {
    let left = parseBinLevel(0)
    while (at('??')) {
      next()
      left = { k: 'coalesce', left, right: parseBinLevel(0) }
    }
    return left
  }

  const parseBinLevel = (level: number): Expr => {
    if (level >= BIN.length) return parseUnary()
    let left = parseBinLevel(level + 1)
    while (BIN[level].includes(peek().t)) {
      const op = next().t
      left = { k: 'bin', op, left, right: parseBinLevel(level + 1) }
    }
    return left
  }

  const parseUnary = (): Expr => {
    const tk = peek()
    if (tk.t === '!' || tk.t === '-' || tk.t === '~' || tk.t === '*' || tk.t === '&') {
      next()
      return { k: 'unary', op: tk.t, expr: parseUnary() }
    }
    if (tk.t === '++' || tk.t === '--') {
      next()
      return { k: 'preincdec', op: tk.t, expr: parseUnary() }
    }
    // cast:  (type) expr
    if (tk.t === '(') {
      const save = p
      next()
      if (TYPE_WORDS.has(peek().t) || (peek().t === 'id' && /^[A-Z]/.test(String(peek().v)))) {
        try {
          const ty = parseType()
          if (at(')')) {
            next()
            return { k: 'cast', type: ty, expr: parseUnary() }
          }
        } catch { /* fall through to grouped expr */ }
      }
      p = save
    }
    return parsePostfix()
  }

  const parsePostfix = (): Expr => {
    let e = parsePrimary()
    while (true) {
      if (at('(')) {
        next()
        const args: Expr[] = []
        while (!at(')')) {
          args.push(parseExpr())
          if (at(',')) next()
        }
        expect(')')
        e = { k: 'call', callee: e, args }
      } else if (at('.')) {
        next()
        e = { k: 'member', obj: e, name: String(expect('id').v) }
      } else if (at('::')) {
        next()
        e = { k: 'scope', obj: e, name: String(expect('id').v) }
      } else if (at('->')) {
        next()
        e = { k: 'arrow', obj: e, name: String(expect('id').v) }
      } else if (at('[')) {
        next()
        const index = parseExpr()
        expect(']')
        e = { k: 'index', obj: e, index }
      } else {
        break
      }
    }
    return e
  }

  const parsePrimary = (): Expr => {
    const tk = peek()
    if (tk.t === 'num') { next(); return { k: 'num', v: Number(tk.v), isFloat: !!tk.isFloat } }
    if (tk.t === 'str') { next(); return { k: 'str', v: String(tk.v) } }
    if (tk.t === 'char') { next(); return { k: 'char', v: Number(tk.v) } }
    if (tk.t === 'true') { next(); return { k: 'bool', v: true } }
    if (tk.t === 'false') { next(); return { k: 'bool', v: false } }
    if (tk.t === 'null') { next(); return { k: 'null' } }
    if (tk.t === 'id') { next(); return { k: 'var', name: String(tk.v) } }
    if (tk.t === '(') {
      next()
      const e = parseExpr()
      expect(')')
      return e
    }
    throw new GlangError(`Unexpected '${tk.v ?? tk.t}' (line ${tk.line})`, tk.line)
  }

  const decls: TopDecl[] = []
  while (!at('eof')) decls.push(parseTopLevel())
  return { k: 'program', decls }
}
