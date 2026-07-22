// "จำ panel ล่าสุด" (web_spec.md §3, ตัวช่วยอันดับ 1). Labs reuse the same set
// of antibiotic disks in the same clockwise order plate after plate, so we
// remember the last confirmed panel and offer it as a one-tap prefill.

const KEY = 'zonescope.recentPanel.v1'

/** @returns {string[]|null} last confirmed antibiotic codes in disk order */
export function loadRecentPanel() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const arr = JSON.parse(raw)
    return Array.isArray(arr) && arr.length ? arr : null
  } catch {
    return null
  }
}

/** @param {string[]} codes  antibiotic codes ordered by disk index */
export function saveRecentPanel(codes) {
  try {
    if (codes.some(Boolean)) localStorage.setItem(KEY, JSON.stringify(codes))
  } catch {
    /* storage unavailable — non-fatal */
  }
}
