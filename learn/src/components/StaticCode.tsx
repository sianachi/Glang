import CodeView from './CodeView.tsx'
import WindowChrome from './ui/WindowChrome.tsx'
import OutputPanel from './ui/OutputPanel.tsx'

// A non-editable, highlighted code sample with an optional expected-output
// panel. Used for concepts the in-browser runner doesn't execute (classes,
// generics, the std library) where we show the program and its known output.
export default function StaticCode({
  code,
  caption,
  output,
}: {
  code: string
  caption?: string
  output?: string
}) {
  return (
    <figure className="my-5 overflow-hidden rounded-xl border border-slate-700/60 bg-surface shadow-lg shadow-black/20">
      {caption && (
        <div className="border-b border-slate-700/60 bg-surface-2 px-4 py-1.5 font-mono text-xs text-slate-400">
          {caption}
        </div>
      )}
      <div className="overflow-auto p-4">
        <CodeView code={code} />
      </div>
      {output !== undefined && <OutputPanel stdout={output} />}
    </figure>
  )
}
