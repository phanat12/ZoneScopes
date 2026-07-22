// Single switch between mock data and the real FastAPI backend (web_spec.md §6).
// VITE_USE_MOCK=true  -> read bundled mock JSON (no backend needed for M1)
// VITE_USE_MOCK=false -> POST multipart/form-data to /api/analyze

import analyzeMock from '../mocks/analyze.json'
import breakpointsMock from '../mocks/breakpoints.json'

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'

const delay = (ms) => new Promise((r) => setTimeout(r, ms))

/**
 * Send an image for analysis. Returns the analyze response (§5.1).
 * @param {File} file
 * @param {(step:number)=>void} [onStep] progress callback (0..stepLabels.length)
 */
export async function analyze(file, onStep) {
  if (USE_MOCK) {
    // Simulate the classical + segmentation pipeline stages so the progress
    // screen shows real steps, not an empty spinner (§4.2).
    for (let i = 1; i <= ANALYZE_STEPS.length; i++) {
      await delay(520)
      onStep?.(i)
    }
    // Point the mock at an object URL of the file the user actually picked when
    // one exists, so preview feels real; fall back to the bundled plate.
    return { ...analyzeMock }
  }

  const body = new FormData()
  body.append('image', file)
  const res = await fetch('/api/analyze', { method: 'POST', body })
  if (!res.ok) throw new Error(`analyze failed: ${res.status}`)
  return res.json()
}

export const ANALYZE_STEPS = [
  { key: 'preprocess', label: 'เตรียมภาพ' },
  { key: 'dish', label: 'หาจานเพาะเชื้อ' },
  { key: 'disks', label: 'หา disk ยา + คาลิเบรต' },
  { key: 'zones', label: 'วัดวงยับยั้ง' },
]

export async function getBreakpoints() {
  if (USE_MOCK) {
    await delay(120)
    return breakpointsMock
  }
  const res = await fetch('/api/breakpoints')
  if (!res.ok) throw new Error(`breakpoints failed: ${res.status}`)
  return res.json()
}

/** Build the export payload (§5.4) and POST it (or return it in mock mode). */
export async function submitReport(payload) {
  if (USE_MOCK) {
    await delay(200)
    return { csv_url: null, pdf_url: null, ok: true }
  }
  const res = await fetch('/api/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`report failed: ${res.status}`)
  return res.json()
}

export { USE_MOCK }
