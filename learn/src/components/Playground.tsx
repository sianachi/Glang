import { useState } from 'react'
import MonacoEditor from './MonacoEditor.tsx'
import WindowChrome from './ui/WindowChrome.tsx'
import OutputPanel from './ui/OutputPanel.tsx'
import { PlayIcon, ResetIcon } from './ui/icons.tsx'
import { runGlang, type GlangRunResult } from '../lib/glang/index.ts'

// A runnable, editable Glang snippet. Used for lesson examples that invite the
// learner to tweak and re-run. Code runs on the GLang backend (full language);
// live diagnostics/hover/completion come from the LSP via the Monaco editor.
export default function Playground({ initialCode, caption }: { initialCode: string; caption?: string }) {
  const [code, setCode] = useState(initialCode)
  const [result, setResult] = useState<GlangRunResult | null>(null)
  const [running, setRunning] = useState(false)

  const run = async () => {
    setRunning(true)
    try {
      setResult(await runGlang(code))
    } finally {
      setRunning(false)
    }
  }
  const reset = () => {
    setCode(initialCode)
    setResult(null)
  }

  const actions = (
    <div className="flex items-center gap-1.5">
      <button
        onClick={reset}
        className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-400 transition hover:bg-slate-700/50 hover:text-slate-200"
      >
        <ResetIcon /> Reset
      </button>
      <button
        onClick={run}
        disabled={running}
        className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-2.5 py-1 text-xs font-medium text-white transition hover:bg-emerald-500 disabled:opacity-60"
      >
        <PlayIcon /> {running ? 'Running…' : 'Run'}
      </button>
    </div>
  )

  return (
    <figure className="my-5 overflow-hidden rounded-xl border border-slate-700/60 bg-surface shadow-lg shadow-black/20">
      <WindowChrome caption={caption} actions={actions} />
      <MonacoEditor value={code} onChange={setCode} />
      {result && (
        <OutputPanel
          stdout={result.output.join('\n')}
          stderr={result.stderr}
          emptyNote={result.ok ? `(no output) — exited with code ${result.exit}` : undefined}
        />
      )}
    </figure>
  )
}
