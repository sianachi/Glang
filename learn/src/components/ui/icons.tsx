// Small inline SVG icons shared across the UI. Kept as components so they take
// className/size via props and stay tree-shakeable.

type IconProps = { className?: string }

export const PlayIcon = ({ className = 'h-3.5 w-3.5' }: IconProps) => (
  <svg viewBox="0 0 16 16" className={className} fill="currentColor"><path d="M4 2.5v11l9-5.5z" /></svg>
)

export const ResetIcon = ({ className = 'h-3.5 w-3.5' }: IconProps) => (
  <svg viewBox="0 0 16 16" className={className} fill="none" stroke="currentColor" strokeWidth="1.6">
    <path d="M13 8a5 5 0 1 1-1.5-3.5M13 2v3h-3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

export const CheckIcon = ({ className = 'h-4 w-4' }: IconProps) => (
  <svg viewBox="0 0 20 20" className={className} fill="currentColor">
    <path d="M16.7 5.3a1 1 0 0 1 0 1.4l-7 7a1 1 0 0 1-1.4 0l-3-3a1 1 0 1 1 1.4-1.4l2.3 2.3 6.3-6.3a1 1 0 0 1 1.4 0z" />
  </svg>
)

export const ArrowIcon = ({ dir, className = 'h-4 w-4' }: IconProps & { dir: 'left' | 'right' }) => (
  <svg viewBox="0 0 16 16" className={className} fill="none" stroke="currentColor" strokeWidth="1.8">
    <path d={dir === 'left' ? 'M10 3 5 8l5 5' : 'M6 3l5 5-5 5'} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

export const MenuIcon = ({ className = 'h-5 w-5' }: IconProps) => (
  <svg viewBox="0 0 20 20" className={className} fill="none" stroke="currentColor" strokeWidth="1.8">
    <path d="M3 5h14M3 10h14M3 15h14" strokeLinecap="round" />
  </svg>
)
