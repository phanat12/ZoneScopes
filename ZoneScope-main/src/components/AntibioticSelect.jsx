import { useMemo, useRef, useState, useEffect } from 'react'
import Sheet from './Sheet'

// Type-to-filter antibiotic picker (web_spec.md §3, ตัวช่วยอันดับ 2).
// Type "CIP" -> CIP5 surfaces immediately. Codes already used on this plate are
// shown disabled to enforce "no duplicate antibiotic per plate" (§4.3, §9.5).
export default function AntibioticSelect({ value, options, usedCodes, onChange, onClear, invalid }) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const inputRef = useRef(null)

  const selected = options.find((o) => o.code === value) || null

  useEffect(() => {
    if (open) {
      setQ('')
      // focus after the sheet mounts
      const t = setTimeout(() => inputRef.current?.focus(), 60)
      return () => clearTimeout(t)
    }
  }, [open])

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    if (!needle) return options
    return options.filter(
      (o) => o.code.toLowerCase().includes(needle) || o.label.toLowerCase().includes(needle)
    )
  }, [q, options])

  const pick = (code) => {
    onChange(code)
    setOpen(false)
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`w-full h-11 px-3 rounded-xl border text-left flex items-center justify-between gap-2 bg-white transition-colors ${
          invalid ? 'border-sir-r' : selected ? 'border-teal/40' : 'border-agar-300'
        } active:bg-agar-50`}
      >
        {selected ? (
          <span className="min-w-0">
            <span className="tnum font-semibold text-ink">{selected.code}</span>
            <span className="text-ink-faint text-xs ml-2 truncate">{selected.label}</span>
          </span>
        ) : (
          <span className="text-ink-faint">เลือกยา…</span>
        )}
        <span aria-hidden className="text-ink-faint">▾</span>
      </button>

      <Sheet open={open} onClose={() => setOpen(false)} title="เลือกยาปฏิชีวนะ">
        <div className="sticky top-0 bg-agar-50 pt-1 pb-2 z-10">
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            inputMode="text"
            placeholder="พิมพ์รหัสหรือชื่อยา เช่น CIP…"
            className="w-full h-12 px-4 rounded-xl border border-agar-300 bg-white text-base tnum focus:border-teal"
          />
        </div>

        {value && (
          <button
            onClick={() => {
              onClear?.()
              setOpen(false)
            }}
            className="w-full text-left px-4 py-2.5 text-sm text-sir-r font-medium"
          >
            ล้างการเลือก
          </button>
        )}

        <ul className="pb-2">
          {filtered.map((o) => {
            const used = usedCodes?.has(o.code) && o.code !== value
            const isSel = o.code === value
            return (
              <li key={o.code}>
                <button
                  disabled={used}
                  onClick={() => pick(o.code)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left ${
                    isSel ? 'bg-teal-50' : 'active:bg-agar-100'
                  } disabled:opacity-40`}
                >
                  <span className="tnum font-bold text-ink w-16 shrink-0">{o.code}</span>
                  <span className="text-ink-soft text-sm min-w-0 truncate">{o.label}</span>
                  {used && <span className="ml-auto text-[11px] text-ink-faint shrink-0">ใช้แล้ว</span>}
                  {isSel && <span className="ml-auto text-teal shrink-0" aria-hidden>✓</span>}
                </button>
              </li>
            )
          })}
          {filtered.length === 0 && (
            <li className="px-4 py-6 text-center text-ink-faint text-sm">ไม่พบยาที่ตรงกับ “{q}”</li>
          )}
        </ul>
      </Sheet>
    </>
  )
}
