import Markdown from './Markdown.tsx'
import type { CalloutTone } from '../types.ts'

// Coloured aside boxes for tips, warnings, gotchas, and side-notes.
const STYLES: Record<CalloutTone, { ring: string; label: string; dot: string; icon: string }> = {
  tip: { ring: 'border-emerald-600/40 bg-emerald-950/30', label: 'Tip', dot: 'text-emerald-400', icon: '✦' },
  warn: { ring: 'border-amber-600/40 bg-amber-950/25', label: 'Watch out', dot: 'text-amber-400', icon: '▲' },
  note: { ring: 'border-sky-600/40 bg-sky-950/25', label: 'Note', dot: 'text-sky-400', icon: 'ℹ' },
  gotcha: { ring: 'border-rose-600/40 bg-rose-950/25', label: 'Gotcha', dot: 'text-rose-400', icon: '✕' },
}

export default function Callout({ tone = 'note', title, md }: { tone?: CalloutTone; title?: string; md: string }) {
  const s = STYLES[tone] ?? STYLES.note
  return (
    <div className={`my-5 rounded-xl border ${s.ring} px-4 py-3`}>
      <div className={`mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider ${s.dot}`}>
        <span aria-hidden>{s.icon}</span>
        {title || s.label}
      </div>
      <div className="text-sm [&_p]:my-1.5">
        <Markdown md={md} />
      </div>
    </div>
  )
}
