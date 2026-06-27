import ProgressMeter from './sidebar/ProgressMeter.tsx'
import ModuleNav from './sidebar/ModuleNav.tsx'
import { MODULES, TOTAL_LESSONS } from '../data/curriculum.ts'
import type { Progress } from '../hooks/useProgress.ts'

function BrandHeader() {
  return (
    <div className="flex items-center gap-2.5 border-b border-slate-800 px-5 py-4">
      <div>
        <div className="font-semibold leading-tight text-slate-100">Glang</div>
        <div className="text-xs text-slate-500">Learn GScript</div>
      </div>
    </div>
  )
}

export default function Sidebar({
  currentId,
  onNavigate,
  progress,
  open,
  onClose,
}: {
  currentId: string
  onNavigate: (id: string) => void
  progress: Progress
  open: boolean
  onClose: () => void
}) {
  const doneCount = Object.values(progress.lessons).filter(Boolean).length

  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-black/60 lg:hidden" onClick={onClose} />}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-800 bg-surface transition-transform lg:static lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <BrandHeader />
        <ProgressMeter done={doneCount} total={TOTAL_LESSONS} />
        <ModuleNav
          modules={MODULES}
          currentId={currentId}
          isLessonDone={progress.isLessonDone}
          onNavigate={onNavigate}
        />
        <button
          onClick={progress.reset}
          className="border-t border-slate-800 px-5 py-3 text-left text-xs text-slate-500 transition hover:text-slate-300"
        >
          Reset progress
        </button>
      </aside>
    </>
  )
}
