import { useState } from 'react'
import MonacoEditor from './MonacoEditor.tsx'
import Markdown from './Markdown.tsx'
import PredictInput from './exercise/PredictInput.tsx'
import HintList from './exercise/HintList.tsx'
import ResultBanner from './exercise/ResultBanner.tsx'
import SolutionPanel from './exercise/SolutionPanel.tsx'
import { CheckIcon } from './ui/icons.tsx'
import { checkExercise, type CheckResult } from '../lib/checkExercise.ts'
import type { Exercise as ExerciseData } from '../types.ts'

// Orchestrates one exercise: prompt, the predict/coding input, hints, the
// pass/fail banner, and the solution reveal. The grading itself lives in
// ../lib/checkExercise.ts; the sub-views live in ./exercise/*.
export default function Exercise({
  ex,
  index,
  done,
  onComplete,
}: {
  ex: ExerciseData
  index: number
  done: boolean
  onComplete?: (id: string) => void
}) {
  const [code, setCode] = useState(ex.starter ?? '')
  const [predict, setPredict] = useState('')
  const [result, setResult] = useState<CheckResult | null>(null)
  const [hintLevel, setHintLevel] = useState(0)
  const [showSolution, setShowSolution] = useState(false)
  const [checking, setChecking] = useState(false)

  const isPredict = ex.check.kind === 'predict'
  const hints = ex.hints ?? []

  const check = async () => {
    setChecking(true)
    try {
      const r = await checkExercise(ex.check, code, predict)
      setResult(r)
      if (r.pass && !done) onComplete?.(ex.id)
    } finally {
      setChecking(false)
    }
  }

  return (
    <section className="my-7 rounded-2xl border border-slate-700/60 bg-surface/70 p-5">
      <div className="mb-3 flex items-center gap-2.5">
        <span className={`flex h-7 w-7 items-center justify-center rounded-lg text-sm font-bold ${done ? 'bg-emerald-600 text-white' : 'bg-slate-700 text-slate-200'}`}>
          {done ? <CheckIcon /> : index}
        </span>
        <h4 className="text-base font-semibold text-slate-100">Exercise</h4>
        {ex.difficulty && (
          <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-400">
            {ex.difficulty}
          </span>
        )}
      </div>

      <div className="text-sm text-slate-300">
        <Markdown md={ex.prompt} />
      </div>

      {isPredict ? (
        <PredictInput
          code={ex.code}
          value={predict}
          rows={Math.max(2, ex.check.expected.split('\n').length)}
          onChange={setPredict}
        />
      ) : (
        <div className="mt-3">
          <MonacoEditor value={code} onChange={setCode} minRows={5} />
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          onClick={check}
          disabled={checking}
          className="rounded-lg bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:opacity-60"
        >
          {checking ? 'Checking…' : 'Check answer'}
        </button>
        {hints.length > 0 && (
          <button
            onClick={() => setHintLevel((h) => Math.min(h + 1, hints.length))}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
            disabled={hintLevel >= hints.length}
          >
            {hintLevel === 0 ? 'Show a hint' : hintLevel >= hints.length ? 'No more hints' : 'Next hint'}
          </button>
        )}
        {ex.solution && (
          <button
            onClick={() => setShowSolution((s) => !s)}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition hover:bg-slate-800"
          >
            {showSolution ? 'Hide solution' : 'Reveal solution'}
          </button>
        )}
      </div>

      <HintList hints={hints} revealed={hintLevel} />
      {result && <ResultBanner result={result} />}
      {showSolution && ex.solution && <SolutionPanel solution={ex.solution} />}
    </section>
  )
}
