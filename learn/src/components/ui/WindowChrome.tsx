import type { ReactNode } from 'react'

// The "editor window" title bar: three traffic-light dots, an optional caption,
// and an optional actions slot on the right. Shared by Playground and StaticCode.
export default function WindowChrome({ caption, actions }: { caption?: string; actions?: ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-700/60 bg-surface-2 px-3 py-1.5">
      <div className="flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-rose-400/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-amber-400/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/70" />
        {caption && <span className="ml-2 font-mono text-xs text-slate-400">{caption}</span>}
      </div>
      {actions}
    </div>
  )
}
