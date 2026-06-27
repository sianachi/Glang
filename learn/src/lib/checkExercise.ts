// Pure logic for grading an exercise attempt, kept out of the component so it
// can be unit-tested and reused.
import { runGlang } from './glang/index.ts'
import type { Check } from '../types.ts'

export interface CheckResult {
  pass: boolean
  message: string
  /** The program's stdout, when the check ran code. */
  output?: string
}

const norm = (s: string) => s.replace(/\r/g, '').replace(/[ \t]+$/gm, '').trim()

/**
 * Evaluate a learner's attempt against an exercise's `check` descriptor.
 * `predictText` is used for predict exercises; `userCode` for coding exercises.
 */
export async function checkExercise(check: Check, userCode: string, predictText: string): Promise<CheckResult> {
  if (check.kind === 'predict') {
    const pass = norm(predictText) === norm(check.expected)
    return {
      pass,
      message: pass
        ? 'Correct — that is exactly what it prints.'
        : 'Not quite. Re-trace the program line by line.',
    }
  }

  const r = await runGlang(userCode)
  const output = r.output.join('\n')
  if (!r.ok) return { pass: false, message: r.stderr ?? 'The program did not run.', output }

  if (check.mustInclude) {
    for (const pat of check.mustInclude) {
      if (!new RegExp(pat).test(userCode)) {
        return { pass: false, message: `Your solution should use \`${pat}\`.`, output }
      }
    }
  }
  if (check.mustExclude) {
    for (const pat of check.mustExclude) {
      if (new RegExp(pat).test(userCode)) {
        return { pass: false, message: `Try solving it without \`${pat}\`.`, output }
      }
    }
  }

  const pass = norm(output) === norm(check.expected)
  return {
    pass,
    message: pass ? 'Output matches — well done!' : 'The output does not match what was expected yet.',
    output,
  }
}
