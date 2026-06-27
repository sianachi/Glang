import { useCallback, useEffect, useState } from 'react'

const KEY = 'glang-learn-progress-v1'

interface ProgressState {
  lessons: Record<string, boolean>
  exercises: Record<string, boolean>
}

export interface Progress {
  lessons: Record<string, boolean>
  exercises: Record<string, boolean>
  isLessonDone: (id: string) => boolean
  isExerciseDone: (id: string) => boolean
  completeLesson: (id: string) => void
  completeExercise: (id: string) => void
  reset: () => void
}

function load(): ProgressState {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '') ?? { lessons: {}, exercises: {} }
  } catch {
    return { lessons: {}, exercises: {} }
  }
}

// Tracks completed lessons and exercises in localStorage so progress survives
// reloads. Exposes helpers the UI uses to render checkmarks and the progress bar.
export function useProgress(): Progress {
  const [state, setState] = useState<ProgressState>(load)

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(state))
    } catch {
      /* storage may be unavailable (private mode) — progress is best-effort */
    }
  }, [state])

  const completeLesson = useCallback((id: string) => {
    setState((s) => (s.lessons[id] ? s : { ...s, lessons: { ...s.lessons, [id]: true } }))
  }, [])

  const completeExercise = useCallback((id: string) => {
    setState((s) => ({ ...s, exercises: { ...s.exercises, [id]: true } }))
  }, [])

  const reset = useCallback(() => setState({ lessons: {}, exercises: {} }), [])

  return {
    lessons: state.lessons,
    exercises: state.exercises,
    isLessonDone: (id) => !!state.lessons[id],
    isExerciseDone: (id) => !!state.exercises[id],
    completeLesson,
    completeExercise,
    reset,
  }
}
