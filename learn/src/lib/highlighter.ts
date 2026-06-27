// A lightweight, dependency-free syntax highlighter for Glang (GScript).
// Returns a flat array of segments so React can render <span>s without
// dangerouslySetInnerHTML. The class names map to .tok-* in index.css.

export interface Segment {
  text: string
  cls: string | null
}

const KEYWORDS = new Set([
  'alloc', 'break', 'catch', 'class', 'const', 'continue', 'delete', 'else',
  'enum', 'extends', 'fn', 'for', 'free', 'if', 'implements', 'import',
  'interface', 'modifier', 'namespace', 'new', 'private', 'protected', 'public',
  'return', 'static', 'super', 'this', 'throw', 'try', 'using', 'while', 'in',
  'match',
])

const TYPES = new Set([
  'int', 'float', 'bool', 'char', 'byte', 'string', 'void',
  'List', 'Map', 'Stack', 'Queue', 'Set', 'Option', 'Span', 'MemoryOwner',
  'Arena', 'Rc', 'Bytes', 'Slice', 'Exception',
])

const LITERALS = new Set(['true', 'false', 'null'])

const BUILTINS = new Set([
  'print', 'len', 'substr', 'parseInt', 'parseFloat', 'toString', 'startsWith',
  'endsWith', 'contains', 'indexOf', 'writeFile', 'readFile', 'fileExists',
  'bytesFromString', 'stringFromBytes', 'getArg', 'getArgCount', 'exit',
])

const isIdentStart = (c: string) => /[A-Za-z_]/.test(c)
const isIdentPart = (c: string) => /[A-Za-z0-9_]/.test(c)
const isDigit = (c: string) => /[0-9]/.test(c)

export function highlight(source: string): Segment[] {
  const out: Segment[] = []
  let i = 0
  const n = source.length
  const push = (text: string, cls: string | null) => {
    if (text) out.push({ text, cls })
  }

  while (i < n) {
    const c = source[i]

    if (c === ' ' || c === '\t' || c === '\n' || c === '\r') {
      let j = i
      while (j < n && /\s/.test(source[j])) j++
      push(source.slice(i, j), null)
      i = j
      continue
    }

    if (c === '/' && source[i + 1] === '/') {
      let j = i
      while (j < n && source[j] !== '\n') j++
      push(source.slice(i, j), 'tok-com')
      i = j
      continue
    }

    if (c === '/' && source[i + 1] === '*') {
      let j = i + 2
      while (j < n && !(source[j] === '*' && source[j + 1] === '/')) j++
      j = Math.min(n, j + 2)
      push(source.slice(i, j), 'tok-com')
      i = j
      continue
    }

    if (c === '"') {
      let j = i + 1
      while (j < n && source[j] !== '"') {
        if (source[j] === '\\') j++
        j++
      }
      j = Math.min(n, j + 1)
      push(source.slice(i, j), 'tok-str')
      i = j
      continue
    }

    if (c === "'") {
      let j = i + 1
      while (j < n && source[j] !== "'") {
        if (source[j] === '\\') j++
        j++
      }
      j = Math.min(n, j + 1)
      push(source.slice(i, j), 'tok-str')
      i = j
      continue
    }

    if (isDigit(c) || (c === '.' && isDigit(source[i + 1]))) {
      let j = i
      while (j < n && /[0-9a-fA-FxXbB._eE+-]/.test(source[j])) {
        if ((source[j] === '+' || source[j] === '-') && !/[eE]/.test(source[j - 1])) break
        j++
      }
      push(source.slice(i, j), 'tok-num')
      i = j
      continue
    }

    if (isIdentStart(c)) {
      let j = i
      while (j < n && isIdentPart(source[j])) j++
      const word = source.slice(i, j)
      let k = j
      while (k < n && /\s/.test(source[k])) k++
      const isCall = source[k] === '('

      let cls = 'tok-ident'
      if (KEYWORDS.has(word)) cls = 'tok-kw'
      else if (LITERALS.has(word)) cls = 'tok-num'
      else if (BUILTINS.has(word)) cls = 'tok-builtin'
      else if (TYPES.has(word)) cls = 'tok-type'
      else if (isCall) cls = 'tok-fn'
      else if (/^[A-Z]/.test(word)) cls = 'tok-type'

      push(word, cls)
      i = j
      continue
    }

    push(c, 'tok-punct')
    i++
  }

  return out
}
