// The "mark this lesson complete" checkbox at the foot of a lesson.
export default function CompletionToggle({ done, onComplete }: { done: boolean; onComplete: () => void }) {
  return (
    <div className="mt-10 rounded-xl border border-slate-800 bg-surface/60 p-4">
      <label className="flex cursor-pointer items-center gap-3">
        <input
          type="checkbox"
          checked={done}
          onChange={() => { if (!done) onComplete() }}
          className="h-5 w-5 rounded border-slate-600 bg-slate-800 text-emerald-500 accent-emerald-500"
        />
        <span className="text-sm font-medium text-slate-200">
          {done ? 'Lesson completed' : 'Mark this lesson as complete'}
        </span>
      </label>
    </div>
  )
}
