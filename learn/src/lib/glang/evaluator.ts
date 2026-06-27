// The tree-walking evaluator. Consumes the typed AST and produces printed
// output plus an exit code.
import {
  box, GlangError, mkBool, mkByte, mkChar, mkFloat, mkInt, mkStr, NULL, Signal,
  type Box, type Value,
} from './values.ts'
import type { EnumDecl, Expr, FnDecl, Program, Stmt } from './ast.ts'

type Env = Map<string, Box>[]

// Narrow accessors: most Value variants carry a numeric or string `v`; these
// read it at the spots where the surrounding logic already guarantees the kind.
const numOf = (v: Value): number => (v as { v: number }).v
const strOf = (v: Value): string => (v as { v: string }).v

export interface RunResult {
  output: string[]
  exit: number
}

export class Interp {
  private fns = new Map<string, FnDecl>()
  private enums = new Map<string, EnumDecl>()
  output: string[] = []
  private steps = 0
  private readonly maxSteps = 2_000_000

  constructor(program: Program) {
    for (const d of program.decls) {
      if (d.k === 'fn') this.fns.set(d.name, d)
      else this.enums.set(d.name, d)
    }
  }

  private tick(): void {
    if (++this.steps > this.maxSteps) {
      throw new GlangError('Execution stopped: too many steps (possible infinite loop).')
    }
  }

  run(): RunResult {
    const main = this.fns.get('main')
    if (!main) throw new GlangError("No 'main' function found.")
    const result = this.callFn(main, [])
    return { output: this.output, exit: result.kind === 'int' ? result.v : 0 }
  }

  private callFn(fn: FnDecl, args: Value[]): Value {
    const scope = new Map<string, Box>()
    fn.params.forEach((param, idx) => scope.set(param.name, box(args[idx] ?? NULL)))
    const sig = this.execBlock(fn.body, [scope])
    if (sig instanceof Signal && sig.type === 'return') return sig.value ?? NULL
    return NULL
  }

  private lookup(env: Env, name: string): Box | null {
    for (let i = env.length - 1; i >= 0; i--) {
      const box = env[i].get(name)
      if (box) return box
    }
    return null
  }

  private execBlock(block: { stmts: Stmt[] }, env: Env): Signal | null {
    env.push(new Map())
    try {
      for (const s of block.stmts) {
        const sig = this.execStmt(s, env)
        if (sig instanceof Signal) return sig
      }
    } finally {
      env.pop()
    }
    return null
  }

  private execStmt(s: Stmt, env: Env): Signal | null {
    this.tick()
    switch (s.k) {
      case 'block': return this.execBlock(s, env)
      case 'decl': {
        const val = s.init ? this.coerce(this.eval(s.init, env), s.type) : this.zeroOf(s.type)
        env[env.length - 1].set(s.name, box(val))
        return null
      }
      case 'assign': return this.execAssign(s, env)
      case 'incdec': {
        const target = this.lvalue(s.target, env)
        target.value = this.numOp(target.value, mkInt(s.op === '++' ? 1 : -1), '+')
        return null
      }
      case 'if': {
        if (this.truthy(this.eval(s.cond, env))) return this.execStmt(s.then, env)
        if (s.els) return this.execStmt(s.els, env)
        return null
      }
      case 'while': {
        while (this.truthy(this.eval(s.cond, env))) {
          this.tick()
          const sig = this.execStmt(s.body, env)
          if (sig instanceof Signal) {
            if (sig.type === 'break') break
            if (sig.type === 'continue') continue
            return sig
          }
        }
        return null
      }
      case 'for': {
        env.push(new Map())
        try {
          if (s.init) this.execStmt(s.init, env)
          while (s.cond === null || this.truthy(this.eval(s.cond, env))) {
            this.tick()
            const sig = this.execStmt(s.body, env)
            if (sig instanceof Signal) {
              if (sig.type === 'break') break
              if (sig.type === 'return') return sig
              // continue falls through to post
            }
            if (s.post) this.execStmt(s.post, env)
          }
        } finally {
          env.pop()
        }
        return null
      }
      case 'return': return new Signal('return', s.val ? this.eval(s.val, env) : NULL)
      case 'break': return new Signal('break')
      case 'continue': return new Signal('continue')
      case 'exprstmt': this.eval(s.expr, env); return null
    }
  }

  private execAssign(s: { op: string; target: Expr; value: Expr }, env: Env): null {
    const target = this.lvalue(s.target, env)
    const rhs = this.eval(s.value, env)
    if (s.op === '=') target.value = rhs
    else target.value = this.numOp(target.value, rhs, s.op.slice(0, -1))
    return null
  }

  // Resolve an expression to an assignable Box (for =, ++, &x out-params).
  private lvalue(node: Expr, env: Env): Box {
    if (node.k === 'var') {
      const box = this.lookup(env, node.name)
      if (!box) throw new GlangError(`Undefined variable '${node.name}'.`)
      return box
    }
    if (node.k === 'unary' && node.op === '*') {
      const ptr = this.eval(node.expr, env)
      if (ptr.kind !== 'ptr') throw new GlangError('Dereference of a non-pointer.')
      return ptr.box
    }
    if (node.k === 'index') {
      const arr = this.eval(node.obj, env)
      const idx = numOf(this.eval(node.index, env))
      if (arr.kind === 'array' || arr.kind === 'block') {
        if (idx < 0 || idx >= arr.cells.length) {
          throw new GlangError(`Index ${idx} out of bounds (length ${arr.cells.length}).`)
        }
        return arr.cells[idx]
      }
      throw new GlangError('Indexing a non-array value.')
    }
    throw new GlangError('Invalid assignment target.')
  }

  private eval(node: Expr, env: Env): Value {
    this.tick()
    switch (node.k) {
      case 'num': return node.isFloat ? mkFloat(node.v) : mkInt(node.v)
      case 'str': return mkStr(node.v)
      case 'char': return mkChar(node.v)
      case 'bool': return mkBool(node.v)
      case 'null': return NULL
      case 'var': {
        const box = this.lookup(env, node.name)
        if (box) return box.value
        if (this.enums.has(node.name)) return { kind: 'enumref', name: node.name }
        throw new GlangError(`Undefined name '${node.name}'.`)
      }
      case 'bin': return this.evalBin(node, env)
      case 'coalesce': {
        const l = this.eval(node.left, env)
        return l.kind === 'null' ? this.eval(node.right, env) : l
      }
      case 'unary': return this.evalUnary(node, env)
      case 'preincdec': {
        const box = this.lvalue(node.expr, env)
        box.value = this.numOp(box.value, mkInt(node.op === '++' ? 1 : -1), '+')
        return box.value
      }
      case 'cast': return this.evalCast(node, env)
      case 'call': return this.evalCall(node, env)
      case 'member': return this.evalMember(node)
      case 'index': return this.lvalue(node, env).value
      case 'scope':
        throw new GlangError('Namespaced/scoped calls are not supported by the in-browser runner.')
      case 'arrow':
        throw new GlangError(`Pointer member access '->${node.name}' is not supported by the in-browser runner.`)
    }
  }

  private evalMember(node: Extract<Expr, { k: 'member' }>): Value {
    if (node.obj.k === 'var' && this.enums.has(node.obj.name)) {
      const en = this.enums.get(node.obj.name)!
      const variant = en.variants.find((v) => v.name === node.name)
      if (!variant) throw new GlangError(`Enum '${en.name}' has no variant '${node.name}'.`)
      return { kind: 'enum', enumName: en.name, variant: variant.name, v: variant.val }
    }
    throw new GlangError(
      `Member access '.${node.name}' on this value is not supported by the in-browser runner.`,
    )
  }

  private evalUnary(node: Extract<Expr, { k: 'unary' }>, env: Env): Value {
    if (node.op === '&') return { kind: 'ptr', box: this.lvalue(node.expr, env) }
    if (node.op === '*') {
      const ptr = this.eval(node.expr, env)
      if (ptr.kind !== 'ptr') throw new GlangError('Dereference of a non-pointer.')
      return ptr.box.value
    }
    const v = this.eval(node.expr, env)
    if (node.op === '!') return mkBool(!this.truthy(v))
    if (node.op === '-') {
      if (v.kind === 'float') return mkFloat(-v.v)
      if (v.kind === 'byte') return mkByte(-v.v)
      return mkInt(-numOf(v))
    }
    if (node.op === '~') return v.kind === 'byte' ? mkByte(~v.v) : mkInt(~numOf(v))
    throw new GlangError(`Unknown unary operator '${node.op}'.`)
  }

  private evalBin(node: Extract<Expr, { k: 'bin' }>, env: Env): Value {
    const op = node.op
    if (op === '&&') return mkBool(this.truthy(this.eval(node.left, env)) && this.truthy(this.eval(node.right, env)))
    if (op === '||') return mkBool(this.truthy(this.eval(node.left, env)) || this.truthy(this.eval(node.right, env)))

    const l = this.eval(node.left, env)
    const r = this.eval(node.right, env)

    if (op === '+' && (l.kind === 'string' || r.kind === 'string')) {
      return mkStr(this.asStr(l) + this.asStr(r))
    }
    if (['==', '!=', '<', '>', '<=', '>='].includes(op)) return this.compare(l, r, op)
    return this.numOp(l, r, op)
  }

  private compare(l: Value, r: Value, op: string): Value {
    if (l.kind === 'null' || r.kind === 'null') {
      const eq = l.kind === r.kind
      if (op === '==') return mkBool(eq)
      if (op === '!=') return mkBool(!eq)
    }
    const a = numOf(l), b = numOf(r)
    switch (op) {
      case '==': return mkBool(a === b)
      case '!=': return mkBool(a !== b)
      case '<': return mkBool(a < b)
      case '>': return mkBool(a > b)
      case '<=': return mkBool(a <= b)
      case '>=': return mkBool(a >= b)
      default: throw new GlangError(`Unknown comparison '${op}'.`)
    }
  }

  private numOp(l: Value, r: Value, op: string): Value {
    const bothInt = (l.kind === 'int' || l.kind === 'char' || l.kind === 'byte') &&
      (r.kind === 'int' || r.kind === 'char' || r.kind === 'byte')
    const a = numOf(l), b = numOf(r)
    let res: number
    switch (op) {
      case '+': res = a + b; break
      case '-': res = a - b; break
      case '*': res = a * b; break
      case '/':
        if (b === 0) throw new GlangError('Division by zero.')
        res = bothInt ? Math.trunc(a / b) : a / b
        break
      case '%':
        if (b === 0) throw new GlangError('Modulo by zero.')
        res = a % b
        break
      case '&': res = a & b; break
      case '|': res = a | b; break
      case '^': res = a ^ b; break
      case '<<': res = a << b; break
      case '>>': res = a >> b; break
      default: throw new GlangError(`Unknown operator '${op}'.`)
    }
    if (l.kind === 'byte' || r.kind === 'byte') return mkByte(res)
    if (l.kind === 'float' || r.kind === 'float') return mkFloat(res)
    return mkInt(res)
  }

  private evalCast(node: Extract<Expr, { k: 'cast' }>, env: Env): Value {
    const v = this.eval(node.expr, env)
    const t = node.type.name
    if (t === 'int') return mkInt(numOf(v))
    if (t === 'float') return mkFloat(typeof numOf(v) === 'number' ? numOf(v) : 0)
    if (t === 'char') return mkChar(numOf(v))
    if (t === 'byte') return mkByte(numOf(v))
    if (t === 'bool') return mkBool(this.truthy(v))
    if (t === 'string') return mkStr(this.asStr(v))
    if (this.enums.has(t)) {
      const en = this.enums.get(t)!
      const variant = en.variants.find((x) => x.val === numOf(v))
      return { kind: 'enum', enumName: t, variant: variant ? variant.name : '?', v: numOf(v) }
    }
    return v
  }

  private evalCall(node: Extract<Expr, { k: 'call' }>, env: Env): Value {
    if (node.callee.k !== 'var') {
      throw new GlangError('Only direct function calls are supported by the in-browser runner.')
    }
    const name = node.callee.name
    const args = node.args.map((a) => this.eval(a, env))

    switch (name) {
      case 'print': this.output.push(this.printStr(args[0])); return NULL
      case 'len': return mkInt(strOf(args[0]).length)
      case 'substr': {
        const s = strOf(args[0])
        const start = numOf(args[1])
        const length = args[2] !== undefined ? numOf(args[2]) : s.length - start
        return mkStr(s.substr(start, length))
      }
      case 'toString': return mkStr(this.asStr(args[0]))
      case 'parseInt': return mkInt(parseInt(strOf(args[0]), 10) || 0)
      case 'parseFloat': return mkFloat(parseFloat(strOf(args[0])) || 0)
      case 'startsWith': return mkBool(strOf(args[0]).startsWith(strOf(args[1])))
      case 'endsWith': return mkBool(strOf(args[0]).endsWith(strOf(args[1])))
      case 'contains': return mkBool(strOf(args[0]).includes(strOf(args[1])))
      case 'indexOf': return mkInt(strOf(args[0]).indexOf(strOf(args[1])))
      case 'exit': throw new Signal('exit', mkInt(args[0] ? numOf(args[0]) : 0))
    }

    const fn = this.fns.get(name)
    if (!fn) throw new GlangError(`Unknown function '${name}'.`)
    return this.callFn(fn, args)
  }

  private truthy(v: Value): boolean {
    if (v.kind === 'bool') return v.v
    if (v.kind === 'null') return false
    throw new GlangError(`Condition must be a bool, got '${v.kind}'.`)
  }

  private asStr(v: Value): string {
    switch (v.kind) {
      case 'string': return v.v
      case 'int': case 'byte': return String(v.v)
      case 'char': return String.fromCharCode(v.v)
      case 'float': return this.floatStr(v.v)
      case 'bool': return v.v ? 'true' : 'false'
      case 'null': return 'null'
      case 'enum': return v.variant
      default: return String((v as { v?: unknown }).v)
    }
  }

  private floatStr(n: number): string {
    return Number.isInteger(n) ? n.toFixed(1) : String(n)
  }

  // print() formats per the spec: byte prints its numeric value, char as text.
  private printStr(v: Value): string {
    if (v.kind === 'char') return String.fromCharCode(v.v)
    if (v.kind === 'byte') return String(v.v)
    if (v.kind === 'float') return this.floatStr(v.v)
    return this.asStr(v)
  }

  private coerce(v: Value, type: { name: string }): Value {
    if (type.name === 'float' && v.kind === 'int') return mkFloat(v.v)
    if (type.name === 'byte' && v.kind === 'int') return mkByte(v.v)
    if (type.name === 'char' && v.kind === 'int') return mkChar(v.v)
    return v
  }

  private zeroOf(type: { name: string }): Value {
    switch (type.name) {
      case 'int': return mkInt(0)
      case 'float': return mkFloat(0)
      case 'bool': return mkBool(false)
      case 'char': return mkChar(0)
      case 'byte': return mkByte(0)
      case 'string': return mkStr('')
      default: return NULL
    }
  }
}
