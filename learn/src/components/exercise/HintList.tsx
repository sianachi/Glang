import Markdown from '../Markdown.tsx'

// The progressively-revealed hints under an exercise.
export default function HintList({ hints, revealed }: { hints: string[]; revealed: number }) {
  if (revealed <= 0) return null
  return (
    <div className="mt-3 space-y-2">
      {hints.slice(0, revealed).map((h, idx) => (
        <div key={idx} className="rounded-lg border border-sky-700/40 bg-sky-950/20 px-3 py-2 text-sm text-sky-200">
          <span className="font-semibold">Hint {idx + 1}:</span> <Markdown md={h} />
        </div>
      ))}
    </div>
  )
}
