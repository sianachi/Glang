// The "X/Y complete" progress bar at the top of the sidebar.
export default function ProgressMeter({ done, total }: { done: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((done / total) * 100)
  return (
    <div className="border-b border-slate-800 px-5 py-3">
      <div className="mb-1.5 flex items-center justify-between text-xs text-slate-400">
        <span>Progress</span>
        <span className="font-medium text-emerald-400">{done}/{total}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
