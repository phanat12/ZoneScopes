import { useMemo, useRef, useState, useEffect } from 'react'
import Sheet from './Sheet'

// Type-to-filter organism picker. The full organism/group list comes from the
// lab breakpoint table (AST_data_review.xlsx). Selecting an organism is what
// makes the S/I/R breakpoints resolve for each disk downstream.
export default function OrganismSelect({ value, options, onChange, onClear }) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const inputRef = useRef(null)

  const selected = options.find((o) => o.id === value) || null

  useEffect(() => {
    if (open) {
      setQ('')
      const t = setTimeout(() => inputRef.current?.focus(), 60)
      return () => clearTimeout(t)
    }
  }, [open])

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    if (!needle) return options
    return options.filter((o) => o.label.toLowerCase().includes(needle))
  }, [q, options])

  const pick = (id) => {
    onChange(id)
    setOpen(false)
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`w-full h-12 px-4 rounded-xl border text-left flex items-center justify-between gap-2 bg-white transition-colors ${
          selected ? 'border-teal/50' : 'border-agar-300'
        } active:bg-agar-50`}
      >
        {selected ? (
          <span className="italic font-medium text-ink truncate">{selected.label}</span>
        ) : (
          <span className="text-ink-faint">เลือกหรือค้นหาชนิดเชื้อ…</span>
        )}
        <span aria-hidden className="text-ink-faint shrink-0">▾</span>
      </button>

      <Sheet open={open} onClose={() => setOpen(false)} title="เลือกชนิดเชื้อ">
        <div className="sticky top-0 bg-agar-50 pt-1 pb-2 z-10">
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            inputMode="text"
            placeholder="พิมพ์ชื่อเชื้อ เช่น coli, aureus, Enterobac…"
            className="w-full h-12 px-4 rounded-xl border border-agar-300 bg-white text-base focus:border-teal"
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
            const isSel = o.id === value
            return (
              <li key={o.id}>
                <button
                  onClick={() => pick(o.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left ${
                    isSel ? 'bg-teal-50' : 'active:bg-agar-100'
                  }`}
                >
                  <span className="italic text-ink text-[15px] min-w-0 truncate">{o.label}</span>
                  {isSel && (
                    <span className="ml-auto text-teal shrink-0" aria-hidden>
                      ✓
                    </span>
                  )}
                </button>
              </li>
            )
          })}
          {filtered.length === 0 && (
            <li className="px-4 py-6 text-center text-ink-faint text-sm">ไม่พบเชื้อที่ตรงกับ “{q}”</li>
          )}
        </ul>
      </Sheet>
    </>
  )
}
