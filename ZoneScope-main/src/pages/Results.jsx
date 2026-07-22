import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppBar from '../components/AppBar'
import ImageCanvas from '../components/ImageCanvas'
import ResultTable from '../components/ResultTable'
import { SIR_META } from '../lib/interpret'
import { useSession, selectResults } from '../store/useSession'
import { submitReport } from '../lib/api'
import { buildReportPayload, resultsToCsv, downloadCsv } from '../lib/exportReport'
import PrintReport from '../components/PrintReport'

export default function Results() {
  const nav = useNavigate()
  const state = useSession()
  const { analysis, imageUrl, breakpoints, organism, plateId, persistPanel, reset } = state
  const [busy, setBusy] = useState(false)
  const [savedNote, setSavedNote] = useState('')

  useEffect(() => {
    if (!analysis) nav('/', { replace: true })
  }, [analysis, nav])

  const results = useMemo(() => selectResults(state), [state])
  const resultsById = useMemo(() => Object.fromEntries(results.map((r) => [r.disk.id, r.interpretation])), [results])

  if (!analysis || !breakpoints) return null

  const antibioticLabels = Object.fromEntries(breakpoints.antibiotics.map((a) => [a.code, a.label]))
  const organismLabel = breakpoints.organisms.find((o) => o.id === organism)?.label || organism
  const named = results.filter((r) => r.antibiotic)
  const tally = named.reduce((acc, r) => ((acc[r.interpretation] = (acc[r.interpretation] || 0) + 1), acc), {})
  const incomplete = named.length < analysis.disks.length

  const exportCsv = async () => {
    setBusy(true)
    try {
      const payload = buildReportPayload({ analysis, plateId, organism, results })
      await submitReport(payload) // server = source of truth (§5.3); mock no-ops
      persistPanel() // remember this panel for next plate (§3.1)
      const csv = resultsToCsv({
        plateId,
        organism,
        organismLabel,
        standard: breakpoints.standard,
        results,
      })
      downloadCsv(`zonescope_${plateId || analysis.image_id}.csv`, csv)
      setSavedNote('ดาวน์โหลด CSV แล้ว · จำชุดยานี้ไว้ให้จานถัดไป')
    } finally {
      setBusy(false)
    }
  }

  const printPdf = () => {
    persistPanel()
    window.print()
  }

  return (
    <div className="min-h-full flex flex-col">
      <div className="no-print flex flex-col min-h-full">
        <AppBar title="ผลลัพธ์" sub={`${organismLabel} · ${plateId || 'ไม่มีรหัสจาน'}`} back="/review" />

        <main className="flex-1 px-4 py-4 space-y-4 max-w-md mx-auto w-full pb-28">
          {incomplete && (
            <div className="rounded-xl bg-amber-50 border border-amber-200 px-3 py-2 text-[12px] text-amber-800">
              ⚠️ รายงานนี้ยังไม่สมบูรณ์ — ระบุยาแล้ว {named.length}/{analysis.disks.length} disk
            </div>
          )}

          {/* tally */}
          <div className="flex gap-2">
            {['S', 'I', 'R', 'N/A'].map((k) => (
              <div key={k} className="card flex-1 py-2.5 text-center">
                <div className="tnum text-xl font-bold" style={{ color: SIR_META[k].hex }}>
                  {tally[k] || 0}
                </div>
                <div className="text-[11px] text-ink-faint">{k}</div>
              </div>
            ))}
          </div>

          {/* overlay image — heart of explainability (§4.4) */}
          <div className="h-[38vh] min-h-[240px]">
            <ImageCanvas analysis={analysis} imageUrl={imageUrl} resultsById={resultsById} showMeasures />
          </div>
          <p className="text-[11px] text-ink-faint -mt-2">ขอบวงที่วัดและค่า มม. แสดงทับบนภาพเพื่อตรวจสอบด้วยตา · แตะซูมดูขอบใกล้ ๆ ได้</p>

          <ResultTable results={results} antibioticLabels={antibioticLabels} />

          <p className="text-[11px] text-ink-faint leading-relaxed">
            มาตรฐาน: {breakpoints.standard}. ค่าที่ “แก้โดยคน” ต่างจากที่โมเดลวัด และถูกเก็บไว้ทั้งค่าเดิมและค่าใหม่
            เพื่อปรับปรุงโมเดลรอบถัดไป
          </p>

          {savedNote && <p className="text-[12px] text-teal font-medium">{savedNote}</p>}
        </main>

        {/* export actions */}
        <div className="fixed bottom-0 inset-x-0 bg-agar-50/95 backdrop-blur border-t border-agar-200 px-4 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
          <div className="max-w-md mx-auto flex gap-2">
            <button onClick={exportCsv} disabled={busy || named.length === 0} className="btn btn-primary btn-lg flex-1">
              {busy ? 'กำลังบันทึก…' : 'ดาวน์โหลด CSV'}
            </button>
            <button onClick={printPdf} disabled={named.length === 0} className="btn btn-ghost btn-lg px-4" aria-label="พิมพ์ / บันทึก PDF">
              PDF
            </button>
          </div>
          <div className="max-w-md mx-auto mt-2 flex justify-between text-[13px]">
            <button onClick={() => nav('/review')} className="text-ink-soft font-medium px-2 py-1">
              ‹ แก้ไขการระบุ
            </button>
            <button
              onClick={() => {
                reset()
                nav('/')
              }}
              className="text-teal font-semibold px-2 py-1"
            >
              จานใหม่
            </button>
          </div>
        </div>
      </div>

      {/* printable report (PDF) */}
      <PrintReport
        analysis={analysis}
        imageUrl={imageUrl}
        results={results}
        resultsById={resultsById}
        antibioticLabels={antibioticLabels}
        organismLabel={organismLabel}
        plateId={plateId}
        standard={breakpoints.standard}
        tally={tally}
      />
    </div>
  )
}
