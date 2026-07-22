import { FLAG_META, WARNING_META } from '../lib/interpret'

const TONE = {
  warn: 'bg-amber-50 text-amber-800 border-amber-200',
  error: 'bg-red-50 text-sir-r border-red-200',
  info: 'bg-teal-50 text-teal-700 border-teal-100',
}

// Small badge for a single zone flag or plate warning.
export default function FlagBadge({ code, kind = 'flag' }) {
  const meta = (kind === 'warning' ? WARNING_META : FLAG_META)[code]
  if (!meta) return null
  return (
    <span
      title={meta.hint}
      className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-semibold leading-none ${
        TONE[meta.severity] || TONE.warn
      }`}
    >
      <span aria-hidden>{meta.severity === 'error' ? '⛔' : meta.severity === 'info' ? 'ℹ️' : '⚠️'}</span>
      {meta.label}
    </span>
  )
}
