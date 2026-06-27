// A minimal LSP-over-WebSocket client (no external deps) that talks to the GLang
// LSP service (toolchain/services/lsp_ws_server). It speaks just enough of the
// protocol for the editor: initialize, document sync, and request/response for
// hover/completion/definition/documentSymbol, plus receiving publishDiagnostics.
//
// One client is shared across all editors on the page (a single WebSocket); each
// editor opens its own document URI.

type Pending = { resolve: (v: unknown) => void; reject: (e: unknown) => void }
type DiagHandler = (uri: string, diagnostics: LspDiagnostic[]) => void

export interface LspPosition { line: number; character: number }
export interface LspRange { start: LspPosition; end: LspPosition }
export interface LspDiagnostic { range: LspRange; message: string; severity?: number; source?: string }

export class LspWsClient {
  private ws: WebSocket
  private nextId = 1
  private pending = new Map<number, Pending>()
  private diagHandlers: DiagHandler[] = []
  private versions = new Map<string, number>()
  private ready: Promise<void>
  private closed = false

  constructor(url: string) {
    this.ws = new WebSocket(url)
    this.ready = new Promise<void>((resolve, reject) => {
      this.ws.onopen = () => {
        this.request('initialize', { processId: null, rootUri: null, capabilities: {} })
          .then(() => {
            this.notify('initialized', {})
            resolve()
          })
          .catch(reject)
      }
      this.ws.onerror = (e) => reject(e)
    })
    this.ws.onmessage = (ev) => this.onMessage(String(ev.data))
    this.ws.onclose = () => { this.closed = true }
  }

  private onMessage(data: string) {
    let msg: any
    try { msg = JSON.parse(data) } catch { return }
    if (msg.id !== undefined && (msg.result !== undefined || msg.error !== undefined)) {
      const p = this.pending.get(msg.id)
      if (p) {
        this.pending.delete(msg.id)
        if (msg.error) p.reject(msg.error)
        else p.resolve(msg.result)
      }
    } else if (msg.method === 'textDocument/publishDiagnostics') {
      const { uri, diagnostics } = msg.params
      for (const h of this.diagHandlers) h(uri, diagnostics ?? [])
    }
  }

  request<T = unknown>(method: string, params: unknown): Promise<T> {
    if (this.closed) return Promise.reject(new Error('lsp socket closed'))
    const id = this.nextId++
    this.ws.send(JSON.stringify({ jsonrpc: '2.0', id, method, params }))
    return new Promise<T>((resolve, reject) => {
      this.pending.set(id, { resolve: resolve as (v: unknown) => void, reject })
    })
  }

  notify(method: string, params: unknown) {
    if (this.closed) return
    this.ws.send(JSON.stringify({ jsonrpc: '2.0', method, params }))
  }

  onDiagnostics(h: DiagHandler) { this.diagHandlers.push(h) }

  async whenReady() { return this.ready }

  async didOpen(uri: string, text: string) {
    await this.ready
    this.versions.set(uri, 1)
    this.notify('textDocument/didOpen', {
      textDocument: { uri, languageId: 'glang', version: 1, text },
    })
  }

  async didChange(uri: string, text: string) {
    await this.ready
    if (!this.versions.has(uri)) { return this.didOpen(uri, text) }
    const v = (this.versions.get(uri) ?? 1) + 1
    this.versions.set(uri, v)
    this.notify('textDocument/didChange', {
      textDocument: { uri, version: v },
      contentChanges: [{ text }],
    })
  }

  didClose(uri: string) {
    if (!this.versions.has(uri)) return
    this.versions.delete(uri)
    this.notify('textDocument/didClose', { textDocument: { uri } })
  }
}

let shared: LspWsClient | null = null

function defaultLspUrl(): string {
  const env = import.meta.env.VITE_LSP_WS as string | undefined
  if (env && env.length > 0) return env
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/lsp`
}

/** The page-wide shared LSP client, created lazily on first use. */
export function getLspClient(): LspWsClient {
  if (!shared) shared = new LspWsClient(defaultLspUrl())
  return shared
}
