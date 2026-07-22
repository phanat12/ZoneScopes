import { useNavigate } from 'react-router-dom'

// Compact top bar. The mark is a concentric ring — a disk with its inhibition
// zone, the one thing this whole tool measures.
export function ZoneMark({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
      <circle cx="12" cy="12" r="10.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeDasharray="2.2 2.2" />
      <circle cx="12" cy="12" r="6" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="2.6" fill="currentColor" />
    </svg>
  )
}

export default function AppBar({ title, back, right, sub }) {
  const nav = useNavigate()
  return (
    <header className="sticky top-0 z-30 bg-agar-50/85 backdrop-blur border-b border-agar-200">
      <div className="h-14 px-3 flex items-center gap-2 pt-[env(safe-area-inset-top)]">
        {back ? (
          <button onClick={() => nav(back)} aria-label="ย้อนกลับ" className="h-10 w-10 grid place-items-center rounded-lg text-ink-soft active:bg-agar-100">
            ‹
          </button>
        ) : (
          <span className="text-teal ml-1">
            <ZoneMark />
          </span>
        )}
        <div className="min-w-0 flex-1">
          <h1 className="text-[15px] font-semibold text-ink leading-tight truncate">{title}</h1>
          {sub && <p className="text-[11px] text-ink-faint leading-tight truncate">{sub}</p>}
        </div>
        {right}
      </div>
    </header>
  )
}
