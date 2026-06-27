import { CheckIcon } from '../ui/icons.tsx'
import type { CheckResult } from '../../lib/checkExercise.ts'

// Pass/fail banner shown after the learner checks their answer, with their
// program's output echoed when a coding exercise ran.
export default function ResultBanner({ result }: { result: CheckResult }) {
  return (
    <div
      className={`mt-3 rounded-lg border px-4 py-3 text-sm ${
        result.pass
          ? 'border-emerald-600/50 bg-emerald-950/30 text-emerald-200'
          : 'border-rose-600/50 bg-rose-950/25 text-rose-200'
      }`}
    >
      <div className="flex items-center gap-2 font-medium">
        {result.pass ? <CheckIcon /> : <span aria-hidden>✕</span>}
        {result.message}
      </div>
      {result.output !== undefined && result.output !== '' && (
        <div className="mt-2 rounded bg-black/30 p-2 font-mono text-xs text-slate-300">
          <div className="mb-1 text-[10px] uppercase tracking-wide text-slate-500">Your output</div>
          <pre className="whitespace-pre-wrap">{result.output}</pre>
        </div>
      )}
    </div>
  )
}
