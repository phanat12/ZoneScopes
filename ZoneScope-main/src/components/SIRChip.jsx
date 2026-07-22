import { SIR_META } from '../lib/interpret'

const STYLE = {
  S: 'bg-sir-s text-white',
  I: 'bg-sir-i text-white',
  R: 'bg-sir-r text-white',
  'N/A': 'bg-agar-200 text-ink-faint',
}

// Clinical S/I/R chip. Size 'sm' inline in rows, 'lg' in the results table.
export default function SIRChip({ value = 'N/A', size = 'sm', title }) {
  const meta = SIR_META[value] || SIR_META['N/A']
  const dims = size === 'lg' ? 'h-9 min-w-9 px-3 text-base' : 'h-7 min-w-7 px-2 text-sm'
  return (
    <span
      title={title || meta.full}
      className={`tnum inline-flex items-center justify-center rounded-lg font-bold ${dims} ${STYLE[value]}`}
    >
      {meta.label}
    </span>
  )
}
