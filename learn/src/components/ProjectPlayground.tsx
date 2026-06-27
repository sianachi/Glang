import { useEffect, useRef, useState } from 'react'
import { monaco, ensureGlangMonaco } from '../lib/monaco/setup.ts'
import OutputPanel from './ui/OutputPanel.tsx'
import WindowChrome from './ui/WindowChrome.tsx'
import { PlayIcon } from './ui/icons.tsx'

// A multi-file GLang playground: file tabs, Monaco syntax highlighting, and
// sandboxed running of the whole project on the backend (the run service writes
// the files to a temp dir and the loader resolves cross-file `import`s). main.lang
// is the fixed entry point.
const API = ((import.meta.env.VITE_RUN_API as string | undefined) ?? '').replace(/\/$/, '')
const ENTRY = 'main.lang'

interface RunResult { ok: boolean; output: string[]; stderr: string | null; exit: number }

const DEFAULT_FILES = [
  {
    name: 'main.lang',
    content:
      'import "greet.lang";\n\nint main() {\n    print(greet("Glang"));\n    print("Add files with + and import them. Then Run.");\n    return 0;\n}\n',
  },
  {
    name: 'greet.lang',
    content: 'string greet(string who) {\n    return "Hello, " + who + "!";\n}\n',
  },
]

const validName = (name: string) => /^[A-Za-z0-9_-]+\.lang$/.test(name)

export default function ProjectPlayground({
  initialFiles,
}: {
  initialFiles?: { name: string; content: string }[]
}) {
  const seedRef = useRef(initialFiles && initialFiles.length ? initialFiles : DEFAULT_FILES)
  const [names, setNames] = useState<string[]>(seedRef.current.map((f) => f.name))
  const [activeName, setActiveName] = useState<string>(seedRef.current[0].name)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<RunResult | null>(null)

  const containerRef = useRef<HTMLDivElement>(null)
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null)
  const modelsRef = useRef<Map<string, monaco.editor.ITextModel>>(new Map())
  const projId = useRef(`proj${Date.now()}`)

  // Create the editor + a model per initial file, once.
  useEffect(() => {
    ensureGlangMonaco()
    const editor = monaco.editor.create(containerRef.current as HTMLElement, {
      theme: 'vs-dark',
      minimap: { enabled: false },
      fontSize: 13.5,
      lineNumbers: 'on',
      scrollBeyondLastLine: false,
      automaticLayout: true,
      padding: { top: 12, bottom: 12 },
    })
    editorRef.current = editor
    for (const f of seedRef.current) {
      const uri = monaco.Uri.parse(`inmemory://${projId.current}/${f.name}`)
      modelsRef.current.set(f.name, monaco.editor.createModel(f.content, 'glang', uri))
    }
    editor.setModel(modelsRef.current.get(seedRef.current[0].name) ?? null)
    return () => {
      for (const m of modelsRef.current.values()) m.dispose()
      modelsRef.current.clear()
      editor.dispose()
    }
  }, [])

  // Show the active tab's model.
  useEffect(() => {
    const m = modelsRef.current.get(activeName)
    if (m && editorRef.current) editorRef.current.setModel(m)
  }, [activeName])

  const addFile = () => {
    const raw = window.prompt('New file name (e.g. helper.lang):', 'helper.lang')
    const name = raw?.trim()
    if (!name) return
    if (!validName(name)) {
      window.alert('Use a name like helper.lang — letters, digits, _ or -, ending in .lang.')
      return
    }
    if (modelsRef.current.has(name)) {
      setActiveName(name)
      return
    }
    const uri = monaco.Uri.parse(`inmemory://${projId.current}/${name}`)
    modelsRef.current.set(name, monaco.editor.createModel('', 'glang', uri))
    setNames((n) => [...n, name])
    setActiveName(name)
  }

  const deleteFile = (name: string) => {
    if (name === ENTRY) return
    modelsRef.current.get(name)?.dispose()
    modelsRef.current.delete(name)
    setNames((n) => n.filter((x) => x !== name))
    if (activeName === name) setActiveName(ENTRY)
  }

  const run = async () => {
    setRunning(true)
    try {
      const files = names.map((name) => ({
        name,
        content: modelsRef.current.get(name)?.getValue() ?? '',
      }))
      const res = await fetch(`${API}/api/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files, entry: ENTRY }),
      })
      setResult(await res.json())
    } catch (e) {
      setResult({ ok: false, output: [], stderr: `Could not reach the run service: ${(e as Error).message}`, exit: 1 })
    } finally {
      setRunning(false)
    }
  }

  return (
    <figure className="my-5 overflow-hidden rounded-xl border border-slate-700/60 bg-surface shadow-lg shadow-black/20">
      <WindowChrome
        caption="Project playground"
        actions={
          <button
            onClick={run}
            disabled={running}
            className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-2.5 py-1 text-xs font-medium text-white transition hover:bg-emerald-500 disabled:opacity-60"
          >
            <PlayIcon /> {running ? 'Running…' : 'Run'}
          </button>
        }
      />
      <div className="flex items-center gap-1 overflow-x-auto border-b border-slate-700/60 bg-surface-2 px-2 py-1">
        {names.map((name) => (
          <div
            key={name}
            onClick={() => setActiveName(name)}
            className={`group flex items-center gap-1 rounded-md px-2.5 py-1 font-mono text-xs cursor-pointer ${
              name === activeName ? 'bg-slate-700 text-slate-100' : 'text-slate-400 hover:bg-slate-700/50'
            }`}
          >
            <span>{name}</span>
            {name === ENTRY ? (
              <span className="rounded bg-emerald-600/30 px-1 text-[9px] uppercase tracking-wide text-emerald-300">entry</span>
            ) : (
              <button
                onClick={(e) => { e.stopPropagation(); deleteFile(name) }}
                className="ml-0.5 hidden text-slate-500 hover:text-rose-400 group-hover:inline"
                title="Delete file"
              >
                ×
              </button>
            )}
          </div>
        ))}
        <button
          onClick={addFile}
          className="rounded-md px-2 py-1 text-xs text-slate-400 transition hover:bg-slate-700/50 hover:text-slate-200"
          title="Add file"
        >
          + file
        </button>
      </div>
      <div ref={containerRef} style={{ height: 340 }} className="w-full" />
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
