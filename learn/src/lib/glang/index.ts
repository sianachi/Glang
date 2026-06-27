// Public API for running Glang from the learn platform.
//
// Code now runs on the GLang BACKEND (the run service in toolchain/services),
// reached over HTTP — so the playground executes the *full* language (classes,
// generics, exceptions, the std library), not the in-browser subset. The old
// in-browser interpreter is kept as `runGlangLocal` for an offline fallback and
// for `diagnose` (lightweight parse-time hints when no LSP is connected).
import { parse } from './parser.ts'
import { Interp } from './evaluator.ts'
import { GlangError, Signal } from './values.ts'

export interface GlangRunResult {
  ok: boolean
  output: string[]
  stderr: string | null
  exit: number
}

// Base URL for the run service. Empty string => same-origin (the nginx proxy
// forwards /api/run to the run container in production). In dev, vite's proxy
// (or VITE_RUN_API) points at the local run service.
const RUN_API = ((import.meta.env.VITE_RUN_API as string | undefined) ?? '').replace(/\/$/, '')

/** Run Glang source on the backend and return its output plus any error. */
export async function runGlang(source: string): Promise<GlangRunResult> {
  try {
    const res = await fetch(`${RUN_API}/api/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source }),
    })
    const data = await res.json()
    return {
      ok: !!data.ok,
      output: Array.isArray(data.output) ? data.output : [],
      stderr: data.stderr ?? null,
      exit: typeof data.exit === 'number' ? data.exit : data.ok ? 0 : 1,
    }
  } catch (e) {
    return {
      ok: false,
      output: [],
      stderr: `Could not reach the run service: ${(e as Error).message}`,
      exit: 1,
    }
  }
}

/** Convenience for exercise checking: the joined stdout alongside the result. */
export async function runForOutput(source: string): Promise<GlangRunResult & { text: string }> {
  const r = await runGlang(source)
  return { ...r, text: r.output.join('\n') }
}

/** In-browser fallback runner (subset of the language). Synchronous. */
export function runGlangLocal(source: string): GlangRunResult {
  let interp: Interp | null = null
  try {
    const program = parse(source)
    interp = new Interp(program)
    const { output, exit } = interp.run()
    return { ok: true, output, stderr: null, exit }
  } catch (e) {
    if (e instanceof Signal && e.type === 'exit') {
      return { ok: true, output: interp?.output ?? [], stderr: null, exit: e.value?.kind === 'int' ? e.value.v : 0 }
    }
    const msg = e instanceof GlangError ? e.message : `Error: ${(e as Error).message}`
    return { ok: false, output: interp?.output ?? [], stderr: msg, exit: 1 }
  }
}

/** A diagnostic to mark in the editor. `line` is 1-based. */
export interface Diagnostic {
  line: number
  message: string
}

const LINE_RE = /\(line (\d+)\)/

/**
 * Parse-time diagnostics from the in-browser parser — a lightweight fallback for
 * when the Monaco LSP connection isn't available. Side-effect free (no code is
 * executed) and fail-fast (at most one diagnostic). Reflects the in-browser
 * subset, not the full compiler.
 */
export function diagnose(source: string): Diagnostic[] {
  if (source.trim() === '') return []
  try {
    parse(source)
    return []
  } catch (e) {
    if (e instanceof GlangError) {
      const fromMsg = LINE_RE.exec(e.message)
      const line = e.line ?? (fromMsg ? Number(fromMsg[1]) : 1)
      return [{ line, message: e.message }]
    }
    return []
  }
}
