// The content schema shared by every lesson data file and the components that
// render them. Lesson files are authored as `export default { ... } satisfies
// Lesson`, so a mismatch here is caught at compile time.

export type Difficulty = 'intro' | 'easy' | 'medium' | 'hard'
export type CalloutTone = 'tip' | 'warn' | 'note' | 'gotcha'

/** Run the learner's code and compare its stdout to `expected`. */
export interface OutputCheck {
  kind: 'output'
  expected: string
  /** Regex source strings the submission must contain. */
  mustInclude?: string[]
  /** Regex source strings the submission must NOT contain. */
  mustExclude?: string[]
}

/** Show code (not executed) and check the learner's predicted output. */
export interface PredictCheck {
  kind: 'predict'
  expected: string
}

export type Check = OutputCheck | PredictCheck

export interface Exercise {
  id: string
  difficulty?: Difficulty
  prompt: string
  /** Editable starter code for coding (`output`) exercises. */
  starter?: string
  /** Read-only code shown for predict exercises. */
  code?: string
  check: Check
  hints?: string[]
  solution?: string
}

export interface ProseBlock {
  type: 'prose'
  md: string
}

export interface RunBlock {
  type: 'run'
  code: string
  caption?: string
}

export interface StaticBlock {
  type: 'static'
  code: string
  caption?: string
  output?: string
}

export interface CalloutBlock {
  type: 'callout'
  tone: CalloutTone
  title?: string
  md: string
}

export interface ExerciseBlock {
  type: 'exercise'
  ex: Exercise
}

export type Block = ProseBlock | RunBlock | StaticBlock | CalloutBlock | ExerciseBlock

export interface Lesson {
  id: string
  title: string
  blurb?: string
  blocks: Block[]
}

export interface Module {
  id: string
  title: string
  icon: string
  lessons: Lesson[]
}

/** A lesson plus the module it belongs to (used for routing + headers). */
export interface LessonWithModule extends Lesson {
  moduleId: string
  moduleTitle: string
}
