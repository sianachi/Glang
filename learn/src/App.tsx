import { useMemo, useState } from 'react'
import Sidebar from './components/Sidebar.tsx'
import LessonView from './components/LessonView.tsx'
import PlaygroundPage from './components/PlaygroundPage.tsx'
import MobileHeader from './components/layout/MobileHeader.tsx'
import { ALL_LESSONS, TOTAL_LESSONS, findLesson } from './data/curriculum.ts'
import { useProgress } from './hooks/useProgress.ts'
import { useHashRoute } from './hooks/useHashRoute.ts'

export default function App() {
  const progress = useProgress()
  const validIds = useMemo(() => new Set([...ALL_LESSONS.map((l) => l.id), 'playground']), [])
  const { currentId, navigate } = useHashRoute(validIds, ALL_LESSONS[0].id)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const go = (id: string) => {
    navigate(id)
    setSidebarOpen(false)
  }

  const isPlayground = currentId === 'playground'
  const { lesson, prev, next, index } = findLesson(currentId)

  return (
    <div className="flex min-h-screen bg-canvas text-slate-200">
      <Sidebar
        currentId={currentId}
        onNavigate={go}
        progress={progress}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <MobileHeader onOpenMenu={() => setSidebarOpen(true)} />

        <main className="flex-1 overflow-y-auto">
          {isPlayground ? (
            <PlaygroundPage />
          ) : lesson ? (
            <LessonView
              lesson={lesson}
              prev={prev}
              next={next}
              index={index}
              total={TOTAL_LESSONS}
              progress={progress}
              onNavigate={go}
            />
          ) : (
            <div className="p-10 text-slate-400">Lesson not found.</div>
          )}
        </main>
      </div>
    </div>
  )
}
