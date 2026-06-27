import { highlight } from '../lib/highlighter.ts'

// Renders read-only, syntax-highlighted Glang source as styled <span>s.
export default function CodeView({ code }: { code: string }) {
  const segments = highlight(code.replace(/\s+$/, ''))
  return (
    <code className="block font-mono text-[13.5px] leading-relaxed">
      {segments.map((seg, idx) =>
        seg.cls ? <span key={idx} className={seg.cls}>{seg.text}</span> : <span key={idx}>{seg.text}</span>,
      )}
    </code>
  )
}
