// Tokenizer for the Glang interpreter subset.
import { GlangError } from './values.ts'

export interface Token {
  t: string
  v: string | number | null
  line: number
  isFloat?: boolean
}

export const KEYWORDS = new Set([
  'if', 'else', 'while', 'for', 'break', 'continue', 'return', 'true', 'false',
  'null', 'enum', 'new', 'delete', 'alloc', 'free', 'this',
])

export const TYPE_WORDS = new Set(['int', 'float', 'bool', 'char', 'byte', 'string', 'void'])

const isIdStart = (c: string) => /[A-Za-z_]/.test(c)
const isId = (c: string) => /[A-Za-z0-9_]/.test(c)
const isDigit = (c: string) => c >= '0' && c <= '9'

const unescape = (raw: string): string =>
  raw.replace(/\\(.)/g, (_, c: string) => {
    switch (c) {
      case 'n': return '\n'
      case 't': return '\t'
      case 'r': return '\r'
      case '0': return '\0'
      case '\\': return '\\'
      case '"': return '"'
      case "'": return "'"
      default: return c
    }
  })

export function lex(src: string): Token[] {
  const toks: Token[] = []
  let i = 0
  let line = 1
  const n = src.length

  while (i < n) {
    const c = src[i]
    if (c === '\n') { line++; i++; continue }
    if (/\s/.test(c)) { i++; continue }

    // comments
    if (c === '/' && src[i + 1] === '/') {
      while (i < n && src[i] !== '\n') i++
      continue
    }
    if (c === '/' && src[i + 1] === '*') {
      i += 2
      while (i < n && !(src[i] === '*' && src[i + 1] === '/')) { if (src[i] === '\n') line++; i++ }
      i += 2
      continue
    }

    // string
    if (c === '"') {
      let j = i + 1
      let raw = ''
      while (j < n && src[j] !== '"') {
        if (src[j] === '\\') { raw += src[j] + (src[j + 1] ?? ''); j += 2 }
        else { raw += src[j]; j++ }
      }
      toks.push({ t: 'str', v: unescape(raw), line })
      i = j + 1
      continue
    }

    // char
    if (c === "'") {
      let j = i + 1
      let raw = ''
      while (j < n && src[j] !== "'") {
        if (src[j] === '\\') { raw += src[j] + (src[j + 1] ?? ''); j += 2 }
        else { raw += src[j]; j++ }
      }
      const ch = unescape(raw)
      toks.push({ t: 'char', v: ch.charCodeAt(0) || 0, line })
      i = j + 1
      continue
    }

    // number
    if (isDigit(c) || (c === '.' && isDigit(src[i + 1]))) {
      let j = i
      let isFloat = false
      if (src[i] === '0' && (src[i + 1] === 'x' || src[i + 1] === 'X')) {
        j = i + 2
        while (j < n && /[0-9a-fA-F_]/.test(src[j])) j++
        toks.push({ t: 'num', v: parseInt(src.slice(i + 2, j).replace(/_/g, ''), 16), isFloat: false, line })
        i = j
        continue
      }
      if (src[i] === '0' && (src[i + 1] === 'b' || src[i + 1] === 'B')) {
        j = i + 2
        while (j < n && /[01_]/.test(src[j])) j++
        toks.push({ t: 'num', v: parseInt(src.slice(i + 2, j).replace(/_/g, ''), 2), isFloat: false, line })
        i = j
        continue
      }
      while (j < n && /[0-9_]/.test(src[j])) j++
      if (src[j] === '.' && isDigit(src[j + 1])) {
        isFloat = true
        j++
        while (j < n && /[0-9_]/.test(src[j])) j++
      }
      if (src[j] === 'e' || src[j] === 'E') {
        isFloat = true
        j++
        if (src[j] === '+' || src[j] === '-') j++
        while (j < n && isDigit(src[j])) j++
      }
      const text = src.slice(i, j).replace(/_/g, '')
      toks.push({ t: 'num', v: isFloat ? parseFloat(text) : parseInt(text, 10), isFloat, line })
      i = j
      continue
    }

    // identifier / keyword / type word
    if (isIdStart(c)) {
      let j = i
      while (j < n && isId(src[j])) j++
      const word = src.slice(i, j)
      if (KEYWORDS.has(word)) toks.push({ t: word, v: word, line })
      else if (TYPE_WORDS.has(word)) toks.push({ t: word, v: word, line })
      else toks.push({ t: 'id', v: word, line })
      i = j
      continue
    }

    // multi-char operators (longest first)
    const three = src.slice(i, i + 3)
    if (three === '<<=' || three === '>>=') { toks.push({ t: three, v: three, line }); i += 3; continue }
    const two = src.slice(i, i + 2)
    const twos = ['==', '!=', '<=', '>=', '&&', '||', '++', '--', '->', '::', '??',
      '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<', '>>']
    if (twos.includes(two)) { toks.push({ t: two, v: two, line }); i += 2; continue }

    if (c === undefined) throw new GlangError('Unexpected end of input.')
    toks.push({ t: c, v: c, line })
    i++
  }
  toks.push({ t: 'eof', v: null, line })
  return toks
}
