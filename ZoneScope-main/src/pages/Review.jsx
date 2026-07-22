import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppBar from '../components/AppBar'
import CalibrationBar from '../components/CalibrationBar'
import ImageCanvas from '../components/ImageCanvas'
import DiskRow from '../components/DiskRow'
import {
  useSession,
  selectResults,
  selectUsedAntibiotics,
  selectAssignedCount,
} from '../store/useSession'
import { loadRecentPanel } from '../lib/recentPanel'

export default function Review() {
  const nav = useNavigate()
  const state = useSession()
  const {
    analysis,
    imageUrl,
    breakpoints,
    assignments,
    assignAntibiotic,
    clearAntibiotic,
    confirmOcr,
    setDiameter,
    applyPanel,
  } = state

  const [selectedId, setSelectedId] = useState(null)
  const [recentPanel] = useState(() => loadRecentPanel())

  useEffect(() => {
    if (!analysis) nav('/', { replace: true })
  }, [analysis, nav])

  const results = useMemo(() => selectResults(state), [state])
  const resultsById = useMemo(() => Object.fromEntries(results.map((r) => [r.disk.id, r.interpretation])), [results])
  const rowsById = useMemo(() => Object.fromEntries(results.map((r) => [r.disk.id, r])), [results])

  // duplicate antibiotic detection (§9.5 — no duplicate per plate)
  const dupCodes = useMemo(() => {
    const counts = {}
    for (const a of Object.values(assignments)) if (a.antibiotic) counts[a.antibiotic] = (counts[a.antibiotic] || 0) + 1
    return new Set(Object.entries(counts).filter(([, n]) => n > 1).map(([c]) => c))
  }, [assignments])

  if (!analysis || !breakpoints) return null

  const options = breakpoints.antibiotics
  const total = analysis.disks.length
  const assigned = selectAssignedCount(state)
  const hasDup = dupCodes.size > 0
  const complete = assigned === total && !hasDup

  const organismLabel = breakpoints.organisms.find((o) => o.id === state.organism)?.label

  return (
    <div className="h-[100dvh] flex flex-col overflow-hidden">
      <AppBar title="ตรวจสอบ & ระบุยา" sub={organismLabel} back="/" />
      <CalibrationBar calibration={analysis.calibration} warnings={analysis.warnings} disks={analysis.disks} />

      {/* image — the hero, ~40% of the screen */}
      <div className="shrink-0 h-[40vh] min-h-[240px] p-2">
        <ImageCanvas
          analysis={analysis}
          imageUrl={imageUrl}
          selectedId={selectedId}
          onSelect={(id) => setSelectedId((cur) => (cur === id ? null : id))}
          resultsById={resultsById}
        />
      </div>

      {/* progress strip */}
      <div className="px-4 py-2 bg-agar-50 border-y border-agar-200">
        <div className="flex items-center justify-between text-[13px]">
          <span className="font-semibold text-ink">
            ระบุยาแล้ว <span className="tnum">{assigned}/{total}</span>
          </span>
          {recentPanel && assigned === 0 && (
            <button onClick={() => applyPanel(recentPanel)} className="text-teal font-semibold text-[13px] underline decoration-dotted">
              ใช้ชุดยาล่าสุด
            </button>
          )}
          {hasDup && <span className="text-sir-r font-semibold">มียาซ้ำ</span>}
        </div>
        <div className="mt-1.5 h-1.5 rounded-full bg-agar-200 overflow-hidden">
          <div className="h-full bg-teal transition-all" style={{ width: `${(assigned / total) * 100}%` }} />
        </div>
      </div>

      {/* disk list */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5 bg-agar-50">
        {[...analysis.disks]
          .sort((a, b) => a.index - b.index)
          .map((disk) => (
            <DiskRow
              key={disk.id}
              disk={disk}
              assignment={assignments[disk.id]}
              row={rowsById[disk.id]}
              options={options}
              usedCodes={selectUsedAntibiotics(state, disk.id)}
              selected={selectedId === disk.id}
              invalidDup={dupCodes.has(assignments[disk.id]?.antibiotic)}
              onSelect={(id) => setSelectedId((cur) => (cur === id ? null : id))}
              onAssign={assignAntibiotic}
              onClear={clearAntibiotic}
              onDiameter={setDiameter}
              onConfirmOcr={confirmOcr}
            />
          ))}
        <div className="h-2" />
      </div>

      {/* sticky action */}
      <div className="shrink-0 bg-agar-50/95 backdrop-blur border-t border-agar-200 px-4 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <button
          onClick={() => nav('/results')}
          disabled={assigned === 0 || hasDup}
          className="btn btn-primary btn-lg w-full"
        >
          {complete ? 'ดูผลลัพธ์' : `ดูผลลัพธ์ (ยังไม่ครบ ${assigned}/${total})`}
        </button>
        {hasDup && <p className="text-center text-[11px] text-sir-r mt-1.5">มี disk ที่ระบุยาซ้ำกัน — แก้ก่อนจึงจะไปต่อได้</p>}
      </div>
    </div>
  )
}
