import type { ReactNode } from 'react'

// A deliberately tiny markdown renderer — enough for lesson prose without
// pulling in a dependency. Supports: ## / ### headings, - and 1. lists,
// blockquotes, paragraphs, and inline **bold**, *italic*, `code`, and [links].
// All text is rendered as React nodes (never raw HTML), so content is safe.

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let remaining = text
  let key = 0
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/
  while (remaining.length) {
    const m = remaining.match(re)
    if (!m || m.index === undefined) {
      nodes.push(remaining)
      break
    }
    if (m.index > 0) nodes.push(remaining.slice(0, m.index))
    const tok = m[0]
    if (tok.startsWith('**')) {
      nodes.push(<strong key={`${keyPrefix}-b${key++}`} className="font-semibold text-slate-100">{tok.slice(2, -2)}</strong>)
    } else if (tok.startsWith('`')) {
      nodes.push(
        <code key={`${keyPrefix}-c${key++}`} className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[0.85em] text-emerald-300">
          {tok.slice(1, -1)}
        </code>,
      )
    } else if (tok.startsWith('[')) {
      const lm = tok.match(/\[([^\]]+)\]\(([^)]+)\)/)!
      nodes.push(
        <a key={`${keyPrefix}-l${key++}`} href={lm[2]} target="_blank" rel="noreferrer" className="text-emerald-400 underline decoration-emerald-700 underline-offset-2 hover:text-emerald-300">
          {lm[1]}
        </a>,
      )
    } else {
      nodes.push(<em key={`${keyPrefix}-i${key++}`} className="italic text-slate-200">{tok.slice(1, -1)}</em>)
    }
    remaining = remaining.slice(m.index + tok.length)
  }
  return nodes
}

export default function Markdown({ md }: { md?: string }) {
  if (!md) return null
  const lines = md.replace(/\t/g, '  ').split('\n')
  const out: ReactNode[] = []
  let i = 0
  let key = 0

  while (i < lines.length) {
    const line = lines[i]
    if (line.trim() === '') { i++; continue }

    if (line.startsWith('### ')) {
      out.push(<h4 key={key++} className="mt-6 mb-2 text-lg font-semibold text-slate-100">{renderInline(line.slice(4), `h${key}`)}</h4>)
      i++
      continue
    }
    if (line.startsWith('## ')) {
      out.push(<h3 key={key++} className="mt-7 mb-3 text-xl font-bold text-slate-100">{renderInline(line.slice(3), `h${key}`)}</h3>)
      i++
      continue
    }

    if (/^\s*-\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\s*-\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*-\s+/, ''))
        i++
      }
      out.push(
        <ul key={key++} className="my-3 ml-1 space-y-1.5">
          {items.map((it, idx) => (
            <li key={idx} className="flex gap-2.5 text-slate-300">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500/70" />
              <span>{renderInline(it, `li${key}-${idx}`)}</span>
            </li>
          ))}
        </ul>,
      )
      continue
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ''))
        i++
      }
      out.push(
        <ol key={key++} className="my-3 ml-1 list-inside list-decimal space-y-1.5 text-slate-300 marker:text-emerald-500/70">
          {items.map((it, idx) => <li key={idx}>{renderInline(it, `ol${key}-${idx}`)}</li>)}
        </ol>,
      )
      continue
    }

    if (line.startsWith('> ')) {
      const buf: string[] = []
      while (i < lines.length && lines[i].startsWith('> ')) {
        buf.push(lines[i].slice(2))
        i++
      }
      out.push(
        <blockquote key={key++} className="my-4 border-l-2 border-emerald-600/60 pl-4 text-slate-400 italic">
          {renderInline(buf.join(' '), `bq${key}`)}
        </blockquote>,
      )
      continue
    }

    const buf = [line]
    i++
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !/^\s*-\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i]) &&
      !lines[i].startsWith('#') &&
      !lines[i].startsWith('> ')
    ) {
      buf.push(lines[i])
      i++
    }
    out.push(<p key={key++} className="my-3 text-slate-300">{renderInline(buf.join(' '), `p${key}`)}</p>)
  }

  return <div className="prose-glang">{out}</div>
}
