import Markdown from './Markdown.tsx'
import Playground from './Playground.tsx'
import StaticCode from './StaticCode.tsx'
import Callout from './Callout.tsx'
import Exercise from './Exercise.tsx'
import type { Block } from '../types.ts'
import type { Progress } from '../hooks/useProgress.ts'

// Renders an ordered list of lesson "blocks" into the right component. The
// block schema lives in ../types.ts; the lesson data files (../data/lessons/*)
// are authored against it.
export default function LessonBlocks({ blocks, progress }: { blocks: Block[]; progress: Progress }) {
  let exerciseNum = 0
  return (
    <div>
      {blocks.map((b, i) => {
        switch (b.type) {
          case 'prose':
            return <Markdown key={i} md={b.md} />
          case 'run':
            return <Playground key={i} initialCode={b.code} caption={b.caption} />
          case 'static':
            return <StaticCode key={i} code={b.code} caption={b.caption} output={b.output} />
          case 'callout':
            return <Callout key={i} tone={b.tone} title={b.title} md={b.md} />
          case 'exercise': {
            exerciseNum += 1
            return (
              <Exercise
                key={i}
                ex={b.ex}
                index={exerciseNum}
                done={progress.isExerciseDone(b.ex.id)}
                onComplete={progress.completeExercise}
              />
            )
          }
        }
      })}
    </div>
  )
}
