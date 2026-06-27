import CodeView from '../CodeView.tsx'

// The read-the-code + type-the-output input used by predict exercises.
export default function PredictInput({
  code,
  value,
  rows,
  onChange,
}: {
  code?: string
  value: string
  rows: number
  onChange: (next: string) => void
}) {
  return (
    <>
      {code && (
        <div className="my-3 overflow-auto rounded-lg border border-slate-700/60 bg-[#0a0f1d] p-4">
          <CodeView code={code} />
        </div>
      )}
      <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
        What does it print?
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        rows={rows}
        placeholder="Type the exact output…"
        className="w-full resize-none rounded-lg border border-slate-700/70 bg-[#0a0f1d] p-3 font-mono text-[13px] text-slate-200 outline-none focus:border-emerald-600"
      />
    </>
  )
}
