import { useRef, type KeyboardEvent } from 'react'
import { highlight } from '../lib/highlighter.ts'
import type { Diagnostic } from '../lib/glang/index.ts'

// Font metrics shared by the textarea and the <pre> backdrop. Must match the
// `shared` class below: text-[13.5px] leading-relaxed (1.625) with p-4 (16px).
const FONT_PX = 13.5
const LINE_HEIGHT = FONT_PX * 1.625
const PAD_PX = 16

// An editable code field with a syntax-highlighted backdrop. A transparent
// <textarea> sits over a <pre> that mirrors its content; both share identical
// font metrics and padding so the colored text lines up under the caret.
// Diagnostics (if any) underline the offending line.
export default function Editor({
  value,
  onChange,
  minRows = 4,
  diagnostics = [],
}: {
  value: string
  onChange: (next: string) => void
  minRows?: number
  diagnostics?: Diagnostic[]
}) {
  const taRef = useRef<HTMLTextAreaElement>(null)
  const preRef = useRef<HTMLPreElement>(null)

  const syncScroll = () => {
    if (preRef.current && taRef.current) {
      preRef.current.scrollTop = taRef.current.scrollTop
      preRef.current.scrollLeft = taRef.current.scrollLeft
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Tab inserts two spaces instead of moving focus.
    if (e.key === 'Tab') {
      e.preventDefault()
      const ta = e.currentTarget
      const start = ta.selectionStart
      const end = ta.selectionEnd
      onChange(value.slice(0, start) + '  ' + value.slice(end))
      requestAnimationFrame(() => {
        ta.selectionStart = ta.selectionEnd = start + 2
      })
    }
  }

  const segments = highlight(value.endsWith('\n') ? value + ' ' : value)
  const rows = Math.max(minRows, value.split('\n').length)
  const shared = 'm-0 w-full whitespace-pre font-mono text-[13.5px] leading-relaxed p-4 tracking-normal'

  return (
    <div className="relative overflow-hidden rounded-lg border border-slate-700/70 bg-[#0a0f1d]">
      <pre ref={preRef} aria-hidden className={`${shared} pointer-events-none overflow-auto`}>
        <code>
          {segments.map((seg, idx) =>
            seg.cls ? <span key={idx} className={seg.cls}>{seg.text}</span> : <span key={idx}>{seg.text}</span>,
          )}
        </code>
      </pre>
      {diagnostics.map((d, idx) => (
        <div
          key={`diag-${idx}`}
          aria-hidden
          className="pointer-events-none absolute left-0 right-0 border-b-2 border-rose-500/70 bg-rose-500/10"
          style={{ top: PAD_PX + (d.line - 1) * LINE_HEIGHT, height: LINE_HEIGHT }}
          title={d.message}
        />
      ))}
      <textarea
        ref={taRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onScroll={syncScroll}
        onKeyDown={handleKeyDown}
        spellCheck={false}
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        rows={rows}
        className={`${shared} absolute inset-0 resize-none overflow-auto bg-transparent text-transparent caret-emerald-400 outline-none`}
      />
    </div>
  )
}
