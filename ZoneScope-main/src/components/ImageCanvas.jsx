import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { SIR_META } from '../lib/interpret'

// The plate is the hero (web_spec.md §8). Renders the photo with the model's
// measured zone edges overlaid, plus numbered markers — the explainability
// surface. Markers live in a screen-space layer so they stay a constant,
// tappable size at any zoom; zone polygons live in the scaled SVG so they track
// the image exactly. Selection is two-way with the disk list (§4.3).

const MIN_MULT = 1 // fit-to-contain (whole plate visible, letterboxed)
const MAX_MULT = 7

export default function ImageCanvas({
  analysis,
  imageUrl,
  selectedId,
  onSelect,
  resultsById, // optional: { [diskId]: 'S'|'I'|'R'|'N/A' } to tint markers/zones
  showMeasures = false,
}) {
  const { width: W, height: H, disks, dish } = analysis
  const containerRef = useRef(null)
  const [box, setBox] = useState({ w: 0, h: 0 })
  const [t, setT] = useState({ s: 0, x: 0, y: 0 }) // s = screen px per image px
  const baseRef = useRef(1)

  // pointer bookkeeping for pan / pinch
  const ptrs = useRef(new Map())
  const gesture = useRef(null)

  const clamp = useCallback(
    (s, x, y) => {
      const { w: cw, h: ch } = box
      const iw = W * s
      const ih = H * s
      const nx = iw <= cw ? (cw - iw) / 2 : Math.min(0, Math.max(cw - iw, x))
      const ny = ih <= ch ? (ch - ih) / 2 : Math.min(0, Math.max(ch - ih, y))
      return { s, x: nx, y: ny }
    },
    [box, W, H]
  )

  // measure container + set fit scale
  useLayoutEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      const r = el.getBoundingClientRect()
      setBox({ w: r.width, h: r.height })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    if (!box.w || !box.h) return
    // fit the whole plate inside the frame (contain), not just its width
    const base = Math.min(box.w / W, box.h / H)
    baseRef.current = base
    setT((prev) => {
      // keep fit unless the user has already zoomed in
      if (!prev.s || prev.s <= baseRef.current * 1.02) return clamp(base, 0, 0)
      return clamp(prev.s, prev.x, prev.y)
    })
  }, [box.w, box.h, W, clamp])

  const zoomAround = useCallback(
    (factor, px, py) => {
      setT((prev) => {
        const base = baseRef.current
        const ns = Math.min(base * MAX_MULT, Math.max(base * MIN_MULT, prev.s * factor))
        const k = ns / prev.s
        return clamp(ns, px - (px - prev.x) * k, py - (py - prev.y) * k)
      })
    },
    [clamp]
  )

  const relPoint = (e) => {
    const r = containerRef.current.getBoundingClientRect()
    return { x: e.clientX - r.left, y: e.clientY - r.top }
  }

  const onPointerDown = (e) => {
    containerRef.current.setPointerCapture?.(e.pointerId)
    ptrs.current.set(e.pointerId, relPoint(e))
    if (ptrs.current.size === 1) {
      gesture.current = { type: 'pan', last: relPoint(e) }
    } else if (ptrs.current.size === 2) {
      const [a, b] = [...ptrs.current.values()]
      gesture.current = { type: 'pinch', dist: dist(a, b), mid: mid(a, b) }
    }
  }

  const onPointerMove = (e) => {
    if (!ptrs.current.has(e.pointerId)) return
    const p = relPoint(e)
    ptrs.current.set(e.pointerId, p)
    const g = gesture.current
    if (!g) return
    if (g.type === 'pan' && ptrs.current.size === 1) {
      const dx = p.x - g.last.x
      const dy = p.y - g.last.y
      g.last = p
      setT((prev) => clamp(prev.s, prev.x + dx, prev.y + dy))
    } else if (ptrs.current.size === 2) {
      const [a, b] = [...ptrs.current.values()]
      const d = dist(a, b)
      const m = mid(a, b)
      if (g.type !== 'pinch') {
        gesture.current = { type: 'pinch', dist: d, mid: m }
        return
      }
      if (g.dist > 0) zoomAround(d / g.dist, m.x, m.y)
      gesture.current = { type: 'pinch', dist: d, mid: m }
    }
  }

  const onPointerUp = (e) => {
    ptrs.current.delete(e.pointerId)
    if (ptrs.current.size === 0) gesture.current = null
    else if (ptrs.current.size === 1) gesture.current = { type: 'pan', last: [...ptrs.current.values()][0] }
  }

  const onWheel = (e) => {
    e.preventDefault()
    const p = relPoint(e)
    zoomAround(Math.exp(-e.deltaY * 0.0015), p.x, p.y)
  }

  const resetView = () => setT(clamp(baseRef.current, 0, 0))
  const zoomedIn = t.s > baseRef.current * 1.05

  return (
    <div className="relative h-full w-full overflow-hidden bg-[#1b1b16] rounded-2xl select-none">
      <div
        ref={containerRef}
        className="absolute inset-0 touch-none cursor-grab active:cursor-grabbing"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onWheel={onWheel}
      >
        {/* scaled layer: image + measured-edge overlays */}
        <div
          className="absolute top-0 left-0 origin-top-left will-change-transform"
          style={{ width: W, height: H, transform: `translate(${t.x}px, ${t.y}px) scale(${t.s})` }}
        >
          <img src={imageUrl} alt="จานเพาะเชื้อ" width={W} height={H} draggable={false} className="block w-full h-full" />
          <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="absolute inset-0 pointer-events-none">
            <circle cx={dish.cx} cy={dish.cy} r={dish.r} fill="none" stroke="#0F7C82" strokeOpacity="0.35" strokeWidth={3} />
            {disks.map((d) => {
              const sel = d.id === selectedId
              const sir = resultsById?.[d.id]
              const color = sir && SIR_META[sir] ? SIR_META[sir].hex : '#0F7C82'
              const fuzzy = d.zone.flags.includes('fuzzy_edge') || d.zone.flags.includes('low_confidence')
              const noZone = d.zone.flags.includes('no_zone')
              const pts = d.zone.polygon.map((p) => p.join(',')).join(' ')
              return (
                <g key={d.id}>
                  {/* disk outline */}
                  <circle cx={d.cx} cy={d.cy} r={d.r_px} fill="none" stroke="#ffffff" strokeOpacity="0.85" strokeWidth={2} />
                  {noZone ? (
                    <circle
                      cx={d.cx}
                      cy={d.cy}
                      r={d.r_px + 6}
                      fill="none"
                      stroke={color}
                      strokeOpacity="0.7"
                      strokeWidth={sel ? 5 : 3}
                      strokeDasharray="6 8"
                    />
                  ) : (
                    pts && (
                      <polygon
                        points={pts}
                        fill={color}
                        fillOpacity={sel ? 0.16 : 0.09}
                        stroke={color}
                        strokeOpacity={sel ? 1 : 0.85}
                        strokeWidth={sel ? 6 : 3.5}
                        strokeDasharray={fuzzy ? '10 8' : undefined}
                        strokeLinejoin="round"
                      />
                    )
                  )}
                </g>
              )
            })}
          </svg>
        </div>

        {/* screen-space layer: constant-size markers + optional mm labels */}
        <div className="absolute inset-0 pointer-events-none">
          {disks.map((d) => {
            const left = t.x + d.cx * t.s
            const top = t.y + d.cy * t.s
            if (left < -40 || top < -40 || left > box.w + 40 || top > box.h + 40) return null
            const sel = d.id === selectedId
            const sir = resultsById?.[d.id]
            const bg = sir && sir !== 'N/A' && SIR_META[sir] ? SIR_META[sir].hex : '#0F7C82'
            const flagged = d.zone.flags.some((f) => f !== 'no_zone')
            return (
              <div key={d.id} className="absolute" style={{ left, top, transform: 'translate(-50%,-50%)' }}>
                <button
                  type="button"
                  onPointerDown={(e) => e.stopPropagation()}
                  onClick={() => onSelect?.(d.id)}
                  aria-label={`disk ${d.index}`}
                  className="pointer-events-auto grid place-items-center rounded-full font-bold text-white tnum shadow-md transition-transform"
                  style={{
                    width: sel ? 34 : 28,
                    height: sel ? 34 : 28,
                    background: bg,
                    boxShadow: sel ? '0 0 0 4px rgba(255,255,255,.9), 0 0 0 6px rgba(15,124,130,.5)' : '0 1px 4px rgba(0,0,0,.5)',
                    fontSize: sel ? 15 : 13,
                  }}
                >
                  {d.index}
                </button>
                {flagged && (
                  <span
                    className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-sir-i ring-2 ring-white pointer-events-none"
                    aria-hidden
                  />
                )}
                {showMeasures && !d.zone.flags.includes('no_zone') && (
                  <span
                    className="tnum absolute left-1/2 -translate-x-1/2 mt-1 whitespace-nowrap rounded bg-black/70 px-1.5 py-0.5 text-[11px] font-semibold text-white"
                    style={{ top: sel ? 20 : 16 }}
                  >
                    {d.zone.diameter_mm.toFixed(1)}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* controls */}
      <div className="absolute right-2 bottom-2 flex flex-col gap-1.5">
        <CtrlBtn label="ซูมเข้า" onClick={() => zoomAround(1.4, box.w / 2, box.h / 2)}>＋</CtrlBtn>
        <CtrlBtn label="ซูมออก" onClick={() => zoomAround(1 / 1.4, box.w / 2, box.h / 2)}>－</CtrlBtn>
        {zoomedIn && (
          <CtrlBtn label="รีเซ็ตมุมมอง" onClick={resetView}>
            ⤢
          </CtrlBtn>
        )}
      </div>
    </div>
  )
}

function CtrlBtn({ children, label, onClick }) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="h-9 w-9 grid place-items-center rounded-lg bg-white/90 text-ink text-lg font-semibold shadow active:bg-white"
    >
      {children}
    </button>
  )
}

const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y)
const mid = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 })
