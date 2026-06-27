import { MenuIcon } from '../ui/icons.tsx'

// The compact top bar shown on narrow screens; opens the sidebar drawer.
export default function MobileHeader({ onOpenMenu }: { onOpenMenu: () => void }) {
  return (
    <header className="flex items-center justify-between border-b border-slate-800 px-4 py-3 lg:hidden">
      <button onClick={onOpenMenu} className="rounded-lg border border-slate-700 p-2 text-slate-300" aria-label="Open menu">
        <MenuIcon />
      </button>
      <span className="font-mono text-sm font-semibold text-emerald-400">Glang</span>
      <span className="w-9" />
    </header>
  )
}
