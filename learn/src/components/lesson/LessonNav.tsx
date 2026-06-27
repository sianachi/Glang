import { ArrowIcon } from '../ui/icons.tsx'
import type { LessonWithModule } from '../../types.ts'

function NavCard({ lesson, dir, onClick }: { lesson: LessonWithModule; dir: 'left' | 'right'; onClick: () => void }) {
  const right = dir === 'right'
  return (
    <button
      onClick={onClick}
      className={`group flex flex-1 items-center gap-3 rounded-xl border border-slate-800 bg-surface/60 px-4 py-3 transition hover:border-slate-700 ${
        right ? 'justify-end text-right' : 'text-left'
      }`}
    >
      {!right && <span className="text-slate-500 group-hover:text-emerald-400"><ArrowIcon dir="left" /></span>}
      <span>
        <span className="block text-[11px] uppercase tracking-wide text-slate-500">{right ? 'Next' : 'Previous'}</span>
        <span className="block text-sm font-medium text-slate-200">{lesson.title}</span>
      </span>
      {right && <span className="text-slate-500 group-hover:text-emerald-400"><ArrowIcon dir="right" /></span>}
    </button>
  )
}

// Previous / next lesson buttons. Advancing also marks the current lesson done.
export default function LessonNav({
  prev,
  next,
  onPrev,
  onNext,
}: {
  prev: LessonWithModule | null
  next: LessonWithModule | null
  onPrev: () => void
  onNext: () => void
}) {
  return (
    <nav className="mt-8 flex items-stretch justify-between gap-3">
      {prev ? <NavCard lesson={prev} dir="left" onClick={onPrev} /> : <span className="flex-1" />}
      {next ? <NavCard lesson={next} dir="right" onClick={onNext} /> : <span className="flex-1" />}
    </nav>
  )
}
