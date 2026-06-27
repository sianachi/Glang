import { useEffect, useRef } from 'react'
import { monaco, ensureGlangMonaco } from '../lib/monaco/setup.ts'
import { getLspClient } from '../lib/lsp/client.ts'

let docCounter = 0

// A Monaco-backed editor wired to the GLang LSP service over WebSocket: live
// diagnostics, hover, completion, go-to-definition, and document symbols. Drop-in
// for the old textarea Editor (same value/onChange/minRows props).
export default function MonacoEditor({
  value,
  onChange,
  minRows = 4,
}: {
  value: string
  onChange: (next: string) => void
  minRows?: number
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null)

  useEffect(() => {
    ensureGlangMonaco()
    const client = getLspClient()

    const uri = monaco.Uri.parse(`inmemory://glang/doc${++docCounter}.glang`)
    const model = monaco.editor.createModel(value, 'glang', uri)
    const editor = monaco.editor.create(containerRef.current as HTMLElement, {
      model,
      theme: 'vs-dark',
      minimap: { enabled: false },
      fontSize: 13.5,
      lineNumbers: 'on',
      scrollBeyondLastLine: false,
      automaticLayout: true,
      padding: { top: 12, bottom: 12 },
    })
    editorRef.current = editor

    void client.didOpen(uri.toString(), value)

    let timer: ReturnType<typeof setTimeout> | undefined
    const sub = model.onDidChangeContent(() => {
      const text = model.getValue()
      onChange(text)
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => void client.didChange(uri.toString(), text), 250)
    })

    return () => {
      if (timer) clearTimeout(timer)
      sub.dispose()
      client.didClose(uri.toString())
      model.dispose()
      editor.dispose()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Reflect external value changes (e.g. Reset) without feedback loops.
  useEffect(() => {
    const editor = editorRef.current
    if (editor && editor.getValue() !== value) editor.setValue(value)
  }, [value])

  const height = Math.max(minRows + 1, value.split('\n').length + 1) * 20 + 24
  return (
    <div
      ref={containerRef}
      style={{ height }}
      className="w-full overflow-hidden rounded-lg border border-slate-700/70"
    />
  )
}
