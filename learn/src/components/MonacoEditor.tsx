import { useEffect, useRef } from 'react'
// Core editor API only — excludes Monaco's built-in language modes (we register
// our own `glang` language), which keeps the bundle far smaller.
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api'
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import { getLspClient, type LspDiagnostic } from '../lib/lsp/client.ts'

// Monaco worker setup for Vite. Only the base editor worker is needed (we don't
// use Monaco's built-in TS/JSON language services).
;(self as unknown as { MonacoEnvironment: monaco.Environment }).MonacoEnvironment = {
  getWorker: () => new editorWorker(),
}

let glangRegistered = false
let providersRegistered = false
let docCounter = 0

function registerGlang() {
  if (glangRegistered) return
  glangRegistered = true
  monaco.languages.register({ id: 'glang', extensions: ['.lang', '.glang'] })
  monaco.languages.setMonarchTokensProvider('glang', {
    keywords: [
      'if', 'else', 'while', 'for', 'do', 'foreach', 'in', 'break', 'continue',
      'return', 'import', 'fn', 'enum', 'namespace', 'using', 'const', 'private',
      'protected', 'public', 'modifier', 'managed', 'class', 'interface', 'extends',
      'implements', 'this', 'super', 'new', 'delete', 'static', 'alloc', 'free',
      'try', 'catch', 'throw', 'match', 'true', 'false', 'null', 'var',
    ],
    typeKeywords: ['int', 'float', 'bool', 'char', 'byte', 'string', 'void'],
    tokenizer: {
      root: [
        [/\/\/.*$/, 'comment'],
        [/\/\*/, 'comment', '@comment'],
        [/"/, 'string', '@string'],
        [/'(\\.|[^'\\])*'/, 'string'],
        [/\b\d+\.\d+\b/, 'number.float'],
        [/\b0[xX][0-9a-fA-F]+\b/, 'number.hex'],
        [/\b\d+\b/, 'number'],
        [/[A-Za-z_]\w*/, {
          cases: { '@keywords': 'keyword', '@typeKeywords': 'type', '@default': 'identifier' },
        }],
      ],
      comment: [
        [/[^/*]+/, 'comment'],
        [/\*\//, 'comment', '@pop'],
        [/./, 'comment'],
      ],
      string: [
        [/[^"\\]+/, 'string'],
        [/\\./, 'string.escape'],
        [/"/, 'string', '@pop'],
      ],
    },
  })
  monaco.languages.setLanguageConfiguration('glang', {
    comments: { lineComment: '//', blockComment: ['/*', '*/'] },
    brackets: [['{', '}'], ['[', ']'], ['(', ')']],
    autoClosingPairs: [
      { open: '{', close: '}' }, { open: '[', close: ']' },
      { open: '(', close: ')' }, { open: '"', close: '"' },
    ],
  })
}

function diagToMarker(d: LspDiagnostic): monaco.editor.IMarkerData {
  return {
    severity: d.severity === 2 ? monaco.MarkerSeverity.Warning : monaco.MarkerSeverity.Error,
    message: d.message,
    startLineNumber: d.range.start.line + 1,
    startColumn: d.range.start.character + 1,
    endLineNumber: d.range.end.line + 1,
    endColumn: d.range.end.character + 1,
  }
}

// LSP CompletionItemKind -> Monaco CompletionItemKind.
function completionKind(k: number): monaco.languages.CompletionItemKind {
  const K = monaco.languages.CompletionItemKind
  switch (k) {
    case 3: return K.Function
    case 7: return K.Class
    case 8: return K.Interface
    case 13: return K.Enum
    case 14: return K.Keyword
    case 22: return K.Struct
    default: return K.Text
  }
}

// LSP SymbolKind -> Monaco SymbolKind.
function symbolKind(k: number): monaco.languages.SymbolKind {
  const S = monaco.languages.SymbolKind
  switch (k) {
    case 5: return S.Class
    case 10: return S.Enum
    case 11: return S.Interface
    case 12: return S.Function
    case 3: return S.Namespace
    case 23: return S.Struct
    default: return S.Variable
  }
}

function lspToMonacoRange(r: LspDiagnostic['range']): monaco.IRange {
  return {
    startLineNumber: r.start.line + 1,
    startColumn: r.start.character + 1,
    endLineNumber: r.end.line + 1,
    endColumn: r.end.character + 1,
  }
}

function registerProviders() {
  if (providersRegistered) return
  providersRegistered = true
  const client = getLspClient()

  client.onDiagnostics((uri, diags) => {
    const model = monaco.editor.getModels().find((m) => m.uri.toString() === uri)
    if (model) monaco.editor.setModelMarkers(model, 'glang', diags.map(diagToMarker))
  })

  const posParams = (model: monaco.editor.ITextModel, position: monaco.Position) => ({
    textDocument: { uri: model.uri.toString() },
    position: { line: position.lineNumber - 1, character: position.column - 1 },
  })

  monaco.languages.registerHoverProvider('glang', {
    async provideHover(model, position) {
      const r = await client.request<{ contents?: { value: string }; range?: LspDiagnostic['range'] } | null>(
        'textDocument/hover', posParams(model, position),
      )
      if (!r || !r.contents) return null
      return {
        contents: [{ value: r.contents.value }],
        range: r.range ? lspToMonacoRange(r.range) : undefined,
      }
    },
  })

  monaco.languages.registerCompletionItemProvider('glang', {
    triggerCharacters: ['.'],
    async provideCompletionItems(model, position) {
      const items = await client.request<Array<{ label: string; kind: number; detail?: string }>>(
        'textDocument/completion', posParams(model, position),
      )
      const word = model.getWordUntilPosition(position)
      const range: monaco.IRange = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      }
      return {
        suggestions: (items ?? []).map((it) => ({
          label: it.label,
          kind: completionKind(it.kind),
          detail: it.detail,
          insertText: it.label,
          range,
        })),
      }
    },
  })

  monaco.languages.registerDefinitionProvider('glang', {
    async provideDefinition(model, position) {
      const loc = await client.request<{ uri: string; range: LspDiagnostic['range'] } | null>(
        'textDocument/definition', posParams(model, position),
      )
      if (!loc) return null
      const targetUri = loc.uri === '' ? model.uri : monaco.Uri.parse(loc.uri)
      return { uri: targetUri, range: lspToMonacoRange(loc.range) }
    },
  })

  monaco.languages.registerDocumentSymbolProvider('glang', {
    async provideDocumentSymbols(model) {
      const syms = await client.request<Array<{ name: string; kind: number; range: LspDiagnostic['range']; selectionRange: LspDiagnostic['range'] }>>(
        'textDocument/documentSymbol', { textDocument: { uri: model.uri.toString() } },
      )
      return (syms ?? []).map((s) => ({
        name: s.name,
        detail: '',
        kind: symbolKind(s.kind),
        tags: [],
        range: lspToMonacoRange(s.range),
        selectionRange: lspToMonacoRange(s.selectionRange),
      }))
    },
  })
}

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
    registerGlang()
    registerProviders()
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
