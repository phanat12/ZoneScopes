// S / I / R interpretation runs on the client so edits/antibiotic changes update
// instantly with no server round-trip (web_spec.md §5.3). Rules come from
// /api/breakpoints (mocked). The server stays the source of truth at export.

/**
 * @param {object} bp   loaded breakpoints table
 * @param {string} organism  organism id, e.g. "e_coli"
 * @param {string} antibiotic  antibiotic code, e.g. "CIP5"
 * @param {number|null} diameterMm  measured inhibition-zone diameter in mm
 * @returns {{ result: 'S'|'I'|'R'|'N/A', rule: object|null, reason?: string }}
 */
export function interpret(bp, organism, antibiotic, diameterMm) {
  if (!bp || !organism || !antibiotic || diameterMm == null) {
    return { result: 'N/A', rule: null, reason: 'ยังระบุไม่ครบ' }
  }
  const rule = bp.rules.find((r) => r.organism === organism && r.antibiotic === antibiotic)
  if (!rule) {
    return { result: 'N/A', rule: null, reason: 'ไม่มีเกณฑ์สำหรับคู่เชื้อ+ยานี้' }
  }
  // Decision logic is fixed (web_spec.md §5.2):
  //   d >= s_min -> S ; d <= r_max -> R ; else I
  if (diameterMm >= rule.s_min) return { result: 'S', rule }
  if (diameterMm <= rule.r_max) return { result: 'R', rule }
  return { result: 'I', rule }
}

export const SIR_META = {
  S: { label: 'S', full: 'Susceptible — ไวต่อยา', tone: 'sir-s', hex: '#2E9E6B' },
  I: { label: 'I', full: 'Intermediate — กึ่งกลาง', tone: 'sir-i', hex: '#DDA02B' },
  R: { label: 'R', full: 'Resistant — ดื้อยา', tone: 'sir-r', hex: '#D2483F' },
  'N/A': { label: 'N/A', full: 'ไม่มีเกณฑ์ตัดสิน', tone: 'na', hex: '#7A8582' },
}

// Human-readable meaning for the diagnostic flags a disk can carry (§5.1).
export const FLAG_META = {
  fuzzy_edge: { label: 'ขอบเบลอ', hint: 'โมเดลไม่มั่นใจตำแหน่งขอบวง — ตรวจด้วยตา', severity: 'warn' },
  overlapping_zone: { label: 'วงซ้อนกัน', hint: 'วงยับยั้งซ้อนกับ disk ข้างเคียง อาจวัดเกินจริง', severity: 'warn' },
  no_zone: { label: 'ไม่มีวง', hint: 'เชื้อขึ้นชิด disk = ดื้อ วัดได้เท่าขนาด disk (6.0 มม.)', severity: 'info' },
  low_confidence: { label: 'มั่นใจต่ำ', hint: 'ค่าความมั่นใจของโมเดลต่ำ ควรตรวจสอบ', severity: 'warn' },
  colony_in_zone: { label: 'มีโคโลนีในวง', hint: 'พบเชื้อขึ้นในวงใส อาจเป็นสายพันธุ์ดื้อ', severity: 'warn' },
}

export const WARNING_META = {
  camera_tilt_minor: { label: 'กล้องเอียงเล็กน้อย', hint: 'ค่าที่วัดอาจคลาดเคลื่อนได้บ้าง', severity: 'warn' },
  camera_tilt_major: { label: 'กล้องเอียงมาก', hint: 'ควรถ่ายใหม่ให้ตรง ค่าอาจเพี้ยน', severity: 'error' },
  dish_not_centered: { label: 'จานไม่อยู่กลางเฟรม', hint: 'จัดจานให้อยู่กลางแล้วถ่ายใหม่', severity: 'warn' },
  dish_not_found: { label: 'หาจานไม่เจอ', hint: 'ถ่ายใหม่ให้เห็นจานเต็มใบ', severity: 'error' },
  few_disks_found: { label: 'เจอ disk น้อย', hint: 'อาจมี disk ที่ระบบมองไม่เห็น', severity: 'warn' },
  overexposed: { label: 'ภาพสว่างเกิน', hint: 'ลดแสง/exposure แล้วถ่ายใหม่', severity: 'warn' },
}
