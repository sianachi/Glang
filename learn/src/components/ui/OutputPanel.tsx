// A consistent "Output" panel for printed stdout, error text, or a known
// expected output. Used by Playground, StaticCode, and exercise results.
export default function OutputPanel({
  stdout,
  stderr,
  emptyNote,
}: {
  stdout?: string
  stderr?: string | null
  emptyNote?: string
}) {
  const hasOut = stdout !== undefined && stdout !== ''
  return (
    <div className="border-t border-slate-700/60 bg-[#070b15] px-4 py-3 font-mono text-[13px]">
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Output</div>
      {hasOut && <pre className="whitespace-pre-wrap text-slate-200">{stdout}</pre>}
      {stderr && <pre className="mt-1 whitespace-pre-wrap text-rose-400">{stderr}</pre>}
      {!hasOut && !stderr && emptyNote && <span className="text-slate-500">{emptyNote}</span>}
    </div>
  )
}
