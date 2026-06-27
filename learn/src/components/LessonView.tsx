import { useEffect, useRef } from 'react'
import LessonBlocks from './LessonBlocks.tsx'
import LessonNav from './lesson/LessonNav.tsx'
import CompletionToggle from './lesson/CompletionToggle.tsx'
import type { LessonWithModule } from '../types.ts'
import type { Progress } from '../hooks/useProgress.ts'

export default function LessonView({
  lesson,
  prev,
  next,
  index,
  total,
  progress,
  onNavigate,
}: {
  lesson: LessonWithModule
  prev: LessonWithModule | null
  next: LessonWithModule | null
  index: number
  total: number
  progress: Progress
  onNavigate: (id: string) => void
}) {
  const topRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    topRef.current?.scrollIntoView({ behavior: 'auto' })
  }, [lesson.id])

  const done = progress.isLessonDone(lesson.id)

  return (
    <article className="mx-auto max-w-3xl px-5 py-8 lg:px-10 lg:py-12">
      <div ref={topRef} />
      <div className="rise-in">
        <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-emerald-500">
          <span>{lesson.moduleTitle}</span>
          <span className="text-slate-600">·</span>
          <span className="text-slate-500">Lesson {index + 1} of {total}</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-50">{lesson.title}</h1>
        {lesson.blurb && <p className="mt-2 text-lg text-slate-400">{lesson.blurb}</p>}

        <div className="mt-8">
          <LessonBlocks blocks={lesson.blocks} progress={progress} />
        </div>

        <CompletionToggle done={done} onComplete={() => progress.completeLesson(lesson.id)} />

        <LessonNav
          prev={prev}
          next={next}
          onPrev={() => prev && onNavigate(prev.id)}
          onNext={() => {
            if (!done) progress.completeLesson(lesson.id)
            if (next) onNavigate(next.id)
          }}
        />
      </div>
    </article>
  )
}
