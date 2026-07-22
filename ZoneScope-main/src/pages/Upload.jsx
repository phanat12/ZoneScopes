import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppBar, { ZoneMark } from '../components/AppBar'
import OrganismSelect from '../components/OrganismSelect'
import { getBreakpoints, USE_MOCK } from '../lib/api'
import { useSession } from '../store/useSession'

// Upload-first: the phone is fixed in the light box and shot with a manual
// camera app; the browser never captures live.
export default function Upload() {
  const nav = useNavigate()
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  const breakpoints = useSession((s) => s.breakpoints)
  const setBreakpoints = useSession((s) => s.setBreakpoints)
  const organism = useSession((s) => s.organism)
  const setOrganism = useSession((s) => s.setOrganism)
  const setFileStore = useSession((s) => s.setFile)
  const plateId = useSession((s) => s.plateId)
  const setPlateId = useSession((s) => s.setPlateId)

  useEffect(() => {
    if (!breakpoints) getBreakpoints().then(setBreakpoints).catch(() => {})
  }, [breakpoints, setBreakpoints])

  useEffect(() => () => previewUrl && URL.revokeObjectURL(previewUrl), [previewUrl])

  const pick = (f) => {
    if (!f) return
    setFile(f)
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return URL.createObjectURL(f)
    })
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    pick(e.dataTransfer.files?.[0])
  }

  const canAnalyze = Boolean((file || USE_MOCK) && organism)
  const start = () => {
    if (!canAnalyze) return
    setFileStore(file) // hand the real File to the store so Processing can upload it
    nav('/processing', { state: { fileName: file?.name, previewUrl } })
  }

  const organisms = breakpoints?.organisms || []

  return (
    <div className="min-h-full flex flex-col">
      <AppBar
        title="ZoneScope"
        sub="อ่านจาน Disk Diffusion อัตโนมัติ"
        right={
          USE_MOCK ? (
            <span className="text-[10px] font-semibold text-teal bg-teal-50 px-2 py-1 rounded-md">MOCK</span>
          ) : null
        }
      />

      <main className="flex-1 px-4 pb-28 pt-4 space-y-5 max-w-md mx-auto w-full">
        {/* dropzone */}
        <div>
          <label className="field-label">ภาพจานเพาะเชื้อ</label>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={`mt-2 w-full rounded-2xl border-2 border-dashed p-6 flex flex-col items-center gap-3 transition-colors ${
              dragOver ? 'border-teal bg-teal-50' : 'border-agar-300 bg-white'
            }`}
          >
            {previewUrl ? (
              <img src={previewUrl} alt="ตัวอย่างภาพจาน" className="max-h-56 rounded-xl object-contain" />
            ) : (
              <>
                <span className="h-14 w-14 grid place-items-center rounded-full bg-teal-50 text-teal">
                  <ZoneMark size={28} />
                </span>
                <div className="text-center">
                  <p className="font-semibold text-ink">แตะเพื่อเลือกรูปจาน</p>
                  <p className="text-sm text-ink-faint mt-0.5">หรือลากไฟล์มาวาง · เลือกหลายจานได้</p>
                </div>
              </>
            )}
            {file && <p className="tnum text-xs text-ink-faint truncate max-w-full">{file.name}</p>}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => pick(e.target.files?.[0])}
          />
        </div>

        {/* organism — searchable */}
        <div>
          <label className="field-label">ชนิดเชื้อ</label>
          <div className="mt-2">
            <OrganismSelect
              value={organism}
              options={organisms}
              onChange={setOrganism}
              onClear={() => setOrganism(null)}
            />
          </div>
          {organisms.length === 0 && (
            <p className="text-sm text-ink-faint mt-1.5">กำลังโหลดรายการเชื้อ…</p>
          )}
        </div>

        {/* plate name (optional) */}
        <div>
          <label className="field-label" htmlFor="plate">
            ID ของจาน
          </label>
          <input
            id="plate"
            value={plateId}
            onChange={(e) => setPlateId(e.target.value)}
            placeholder="ระบุ ID ของจาน (ไม่บังคับ)"
            className="mt-2 w-full h-12 px-4 rounded-xl border border-agar-300 bg-white focus:border-teal"
          />
        </div>

        {breakpoints?.standard && (
          <p className="text-[11px] text-ink-faint leading-relaxed pt-1">
            เกณฑ์อ้างอิง: {breakpoints.standard}
          </p>
        )}
      </main>

      {/* sticky action */}
      <div className="fixed bottom-0 inset-x-0 bg-agar-50/90 backdrop-blur border-t border-agar-200 px-4 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <div className="max-w-md mx-auto">
          <button onClick={start} disabled={!canAnalyze} className="btn btn-primary btn-lg w-full">
            วิเคราะห์จาน
          </button>
        </div>
      </div>
    </div>
  )
}
