import { useEffect, useRef } from 'react'
import AntibioticSelect from './AntibioticSelect'
import SIRChip from './SIRChip'
import FlagBadge from './FlagBadge'

// One disk in the Review & Assign list (web_spec.md §4.3). The crop thumbnail
// lets the user read the printed code without zooming the big image; S/I/R
// updates live as the antibiotic or diameter changes.
export default function DiskRow({
  disk,
  assignment,
  row, // interpret() result for this disk
  options,
  usedCodes,
  selected,
  invalidDup,
  onSelect,
  onAssign,
  onClear,
  onDiameter,
  onConfirmOcr,
}) {
  const ref = useRef(null)
  const ocr = disk.ocr_guess
  const showVerify = assignment.source === 'ocr' && !assignment.confirmed && assignment.antibiotic
  const noZone = disk.zone.flags.includes('no_zone')
  const edited = Math.abs(assignment.diameterMm - assignment.originalDiameterMm) > 1e-9

  // scroll into view when selected from the image
  useEffect(() => {
    if (selected) ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [selected])

  return (
    <div
      ref={ref}
      onClick={() => onSelect(disk.id)}
      className={`card p-3 scroll-mt-3 border transition-colors ${
        selected ? 'border-teal ring-1 ring-teal/40' : 'border-transparent'
      }`}
    >
      <div className="flex gap-3">
        {/* index + crop */}
        <div className="shrink-0 flex flex-col items-center gap-1.5">
          <span className="tnum grid place-items-center h-6 w-6 rounded-full bg-teal text-white text-xs font-bold">
            {disk.index}
          </span>
          <img
            src={disk.crop_url}
            alt={`disk ${disk.index}`}
            className="h-14 w-14 rounded-lg object-cover border border-agar-300 bg-agar-100"
            loading="lazy"
          />
        </div>

        {/* controls */}
        <div className="min-w-0 flex-1">
          <div onClick={(e) => e.stopPropagation()}>
            <AntibioticSelect
              value={assignment.antibiotic}
              options={options}
              usedCodes={usedCodes}
              invalid={invalidDup}
              onChange={(code) => onAssign(disk.id, code)}
              onClear={() => onClear(disk.id)}
            />
          </div>

          {showVerify && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onConfirmOcr(disk.id)
              }}
              className="mt-1.5 inline-flex items-center gap-1.5 rounded-md bg-amber-50 border border-amber-200 px-2 py-1 text-[11px] font-semibold text-amber-800"
            >
              ความเชื่อมั่น {Math.round(ocr.confidence * 100)}% — แตะเพื่อยืนยัน
            </button>
          )}

          {/* diameter + result */}
          <div className="mt-2 flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <label className="field-label shrink-0">มม.</label>
            <div className="relative">
              <input
                type="number"
                inputMode="decimal"
                step="0.1"
                min="0"
                value={assignment.diameterMm}
                onChange={(e) => onDiameter(disk.id, clampNum(e.target.value))}
                disabled={noZone}
                className="tnum w-24 h-10 px-2.5 rounded-lg border border-agar-300 bg-white text-center font-semibold disabled:bg-agar-100 disabled:text-ink-faint focus:border-teal"
              />
            </div>
            {edited && (
              <button
                onClick={() => onDiameter(disk.id, assignment.originalDiameterMm)}
                title={`ค่าเดิมจากโมเดล ${assignment.originalDiameterMm.toFixed(1)} มม.`}
                className="text-[11px] font-semibold text-teal underline decoration-dotted"
              >
                แก้แล้ว · คืนค่า
              </button>
            )}
            <div className="ml-auto">
              <SIRChip value={row.interpretation} />
            </div>
          </div>

          {/* flags */}
          {(disk.zone.flags.length > 0 || disk.zone.confidence < 0.7) && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {disk.zone.flags.map((f) => (
                <FlagBadge key={f} code={f} />
              ))}
              {disk.zone.confidence < 0.7 && !disk.zone.flags.includes('low_confidence') && (
                <span className="text-[11px] text-ink-faint">มั่นใจ {Math.round(disk.zone.confidence * 100)}%</span>
              )}
            </div>
          )}
          {row.interpretation === 'N/A' && assignment.antibiotic && (
            <p className="mt-1.5 text-[11px] text-ink-faint">ℹ️ {row.reason}</p>
          )}
        </div>
      </div>
    </div>
  )
}

function clampNum(v) {
  const n = parseFloat(v)
  if (Number.isNaN(n)) return 0
  return Math.max(0, Math.min(200, n))
}
