import { highlight } from '../lib/highlighter.ts'

// Renders read-only, syntax-highlighted Glang source as styled <span>s.
export default function CodeView({ code }: { code: string }) {
  const segments = highlight(code.replace(/\s+$/, ''))
  return (
    <code className="block overflow-x-auto whitespace-pre font-mono text-[13.5px] leading-relaxed [tab-size:2]">
      {segments.map((seg, idx) =>
        seg.cls ? <span key={idx} className={seg.cls}>{seg.text}</span> : <span key={idx}>{seg.text}</span>,
      )}
    </code>
  )
}
