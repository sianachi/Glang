// Runtime values, the mutable storage cell (Box), control-flow signals, and the
// error type shared across the Glang interpreter.

export interface Box {
  value: Value
}

export type Value =
  | { kind: 'int'; v: number }
  | { kind: 'float'; v: number }
  | { kind: 'bool'; v: boolean }
  | { kind: 'char'; v: number }
  | { kind: 'byte'; v: number }
  | { kind: 'string'; v: string }
  | { kind: 'null'; v: null }
  | { kind: 'ptr'; box: Box }
  | { kind: 'enum'; enumName: string; variant: string; v: number }
  | { kind: 'enumref'; name: string }
  | { kind: 'array'; cells: Box[] }
  | { kind: 'block'; cells: Box[] }

// We tag numbers as int vs float so `/` does integer division when both sides
// are ints, matching Glang semantics. Strings/bools/chars are plain JS values.
export const mkInt = (v: number): Value => ({ kind: 'int', v: Math.trunc(v) })
export const mkFloat = (v: number): Value => ({ kind: 'float', v })
export const mkBool = (v: unknown): Value => ({ kind: 'bool', v: !!v })
export const mkChar = (v: number): Value => ({ kind: 'char', v: ((v % 256) + 256) % 256 })
export const mkByte = (v: number): Value => ({ kind: 'byte', v: ((v % 256) + 256) % 256 })
export const mkStr = (v: string): Value => ({ kind: 'string', v })
export const NULL: Value = { kind: 'null', v: null }

export const box = (value: Value): Box => ({ value })

/** A thrown control-flow event: function return, loop break/continue, or exit. */
export class Signal {
  type: 'return' | 'break' | 'continue' | 'exit'
  value?: Value
  constructor(type: 'return' | 'break' | 'continue' | 'exit', value?: Value) {
    this.type = type
    this.value = value
  }
}

/** A user-facing Glang error (parse or runtime), surfaced in the output panel.
 *  `line` (1-based) is set for parse errors so the editor can mark the spot. */
export class GlangError extends Error {
  line?: number
  constructor(message: string, line?: number) {
    super(message)
    this.line = line
  }
}
