import CodeView from '../CodeView.tsx'

// The revealed reference solution for a coding exercise.
export default function SolutionPanel({ solution }: { solution: string }) {
  return (
    <div className="mt-3 overflow-auto rounded-lg border border-slate-700/60 bg-[#0a0f1d] p-4">
      <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Solution</div>
      <CodeView code={solution} />
    </div>
  )
}
