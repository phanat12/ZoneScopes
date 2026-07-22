import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ZoneMark } from '../components/AppBar'
import { analyze, ANALYZE_STEPS, USE_MOCK } from '../lib/api'
import { useSession } from '../store/useSession'

// Progress that names the pipeline stage instead of an empty spinner (§4.2).
export default function Processing() {
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [error, setError] = useState(null)
  const organism = useSession((s) => s.organism)
  const file = useSession((s) => s.file)
  const setAnalysis = useSession((s) => s.setAnalysis)
  const started = useRef(false)

  useEffect(() => {
    // real mode needs the picked File; mock mode ignores it
    if (!organism || (!USE_MOCK && !file)) {
      nav('/', { replace: true })
      return
    }
    if (started.current) return
    started.current = true
    analyze(file, setStep)
      .then((data) => {
        setAnalysis(data)
        nav('/review', { replace: true })
      })
      .catch((e) => setError(e.message || 'วิเคราะห์ไม่สำเร็จ'))
  }, [organism, file, nav, setAnalysis])

  return (
    <div className="min-h-full grid place-items-center px-6 py-16">
      <div className="w-full max-w-sm text-center">
        <div className="mx-auto h-16 w-16 grid place-items-center rounded-full bg-teal-50 text-teal animate-[spin_3s_linear_infinite] motion-reduce:animate-none">
          <ZoneMark size={34} />
        </div>
        <h1 className="mt-5 text-lg font-semibold text-ink">กำลังวิเคราะห์จาน</h1>
        <p className="text-sm text-ink-faint mt-1">
          {USE_MOCK ? 'โหมดเดโม — ใช้ข้อมูลตัวอย่าง' : 'กำลังประมวลผลภาพจริง'}
        </p>

        <ol className="mt-7 space-y-2.5 text-left">
          {ANALYZE_STEPS.map((s, i) => {
            const state = error ? 'idle' : i < step ? 'done' : i === step ? 'active' : 'idle'
            return (
              <li key={s.key} className="flex items-center gap-3">
                <span
                  className={`h-7 w-7 shrink-0 grid place-items-center rounded-full text-xs font-bold tnum ${
                    state === 'done'
                      ? 'bg-teal text-white'
                      : state === 'active'
                        ? 'bg-teal-50 text-teal ring-2 ring-teal'
                        : 'bg-agar-200 text-ink-faint'
                  }`}
                >
                  {state === 'done' ? '✓' : i + 1}
                </span>
                <span className={state === 'idle' ? 'text-ink-faint' : 'text-ink font-medium'}>{s.label}</span>
                {state === 'active' && <span className="ml-auto text-teal text-sm animate-pulse">•••</span>}
              </li>
            )
          })}
        </ol>

        {error && (
          <div className="mt-6">
            <p className="text-sm text-sir-r font-medium">{error}</p>
            <button onClick={() => nav('/')} className="btn btn-ghost btn-md mt-3">
              ลองใหม่
            </button>
          </div>
        )}
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
