import ProjectPlayground from './ProjectPlayground.tsx'

// The standalone, free-form playground page (route #/playground). A scratch
// space with multiple files that runs the whole project on the backend.
export default function PlaygroundPage() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-8 sm:px-8">
      <header className="mb-4">
        <h1 className="text-2xl font-bold text-slate-100">Playground</h1>
        <p className="mt-1 text-sm text-slate-400">
          A scratch space to experiment with GLang. Add files with <span className="font-mono">+ file</span>,
          <span className="font-mono"> import</span> across them, and run the whole project — it executes
          sandboxed on the server with the full language, including the standard library.
          <span className="font-mono"> main.lang</span> is the entry point.
        </p>
      </header>
      <ProjectPlayground />
    </div>
  )
}
