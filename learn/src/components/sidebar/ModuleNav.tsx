import type { Module } from '../../types.ts'

const CheckDot = ({ done }: { done: boolean }) =>
  done ? (
    <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-[9px] text-white">✓</span>
  ) : (
    <span className="h-4 w-4 shrink-0 rounded-full border border-slate-600" />
  )

// The grouped lesson list: one section per module, each lesson a nav button
// with a completion dot.
export default function ModuleNav({
  modules,
  currentId,
  isLessonDone,
  onNavigate,
}: {
  modules: Module[]
  currentId: string
  isLessonDone: (id: string) => boolean
  onNavigate: (id: string) => void
}) {
  return (
    <nav className="flex-1 overflow-y-auto px-3 py-4">
      {modules.map((m) => (
        <div key={m.id} className="mb-4">
          <div className="mb-1 flex items-center gap-2 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            <span className="text-slate-600">{m.icon}</span>
            {m.title}
          </div>
          <ul>
            {m.lessons.map((l) => {
              const active = l.id === currentId
              return (
                <li key={l.id}>
                  <button
                    onClick={() => onNavigate(l.id)}
                    className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-sm transition ${
                      active ? 'bg-emerald-600/15 text-emerald-300' : 'text-slate-300 hover:bg-slate-800/70 hover:text-slate-100'
                    }`}
                  >
                    <CheckDot done={isLessonDone(l.id)} />
                    <span className="truncate">{l.title}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </nav>
  )
}
