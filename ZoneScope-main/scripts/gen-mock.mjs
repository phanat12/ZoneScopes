// Generates a synthetic petri-dish "photo" (public/plate.svg) and a perfectly
// aligned mock analyze response (src/mocks/analyze.json). One source of truth so
// the overlay coordinates the frontend draws line up with the drawn image.
//
// Covers every case required by web_spec.md §6:
//   normal zone · no_zone (resistant) · fuzzy_edge · overlapping_zone ·
//   low_confidence · ocr_guess:null · warning camera_tilt_minor
//
// Run: npm run gen:mock

import { writeFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, '..')

// ---- geometry ------------------------------------------------------------
const W = 1200
const H = 1200
const PX_PER_MM = 12
const cx = 600
const cy = 600
const dishR = 540
const ring = 340 // radius on which disks are placed
const diskR = 36 // 6 mm disk => 3 mm radius * 12 px/mm

// deterministic RNG so re-runs are stable
function mulberry32(seed) {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const deg2rad = (d) => (d * Math.PI) / 180

// index 1..8 laid out clockwise from 12 o'clock
const spec = [
  { code: 'CIP5', mm: 24.0, conf: 0.95, ocr: ['CIP5', 0.9], flags: [] },
  { code: null, mm: 6.0, conf: 0.9, ocr: null, flags: ['no_zone'] },
  { code: 'FOX30', mm: 17.8, conf: 0.51, ocr: ['FOX30', 0.41], flags: ['fuzzy_edge', 'overlapping_zone'] },
  { code: 'CTX30', mm: 20.2, conf: 0.88, ocr: ['CTX30', 0.72], flags: [] },
  { code: null, mm: 27.5, conf: 0.7, ocr: null, flags: ['overlapping_zone'] },
  { code: 'AN30', mm: 28.0, conf: 0.93, ocr: ['AN30', 0.81], flags: [] },
  { code: 'CAZ30', mm: 11.0, conf: 0.6, ocr: ['CAZ30', 0.55], flags: ['low_confidence'] },
  { code: 'AM10', mm: 19.5, conf: 0.9, ocr: ['AM10', 0.68], flags: [] },
]

const disks = spec.map((s, i) => {
  const angle = -90 + i * 45
  const dx = cx + ring * Math.cos(deg2rad(angle))
  const dy = cy + ring * Math.sin(deg2rad(angle))
  const zoneR = (s.mm / 2) * PX_PER_MM
  const rng = mulberry32(1000 + i * 37)
  const isNoZone = s.flags.includes('no_zone')
  const fuzz = s.flags.includes('fuzzy_edge') ? 9 : s.flags.includes('overlapping_zone') ? 6 : 3

  // measured-edge polygon (skip for no-zone: nothing to draw)
  const polygon = []
  if (!isNoZone) {
    const N = 56
    for (let k = 0; k < N; k++) {
      const a = (k / N) * Math.PI * 2
      const r = zoneR + (rng() - 0.5) * 2 * fuzz
      polygon.push([Math.round(dx + r * Math.cos(a)), Math.round(dy + r * Math.sin(a))])
    }
  }

  return {
    id: `d${i + 1}`,
    index: i + 1,
    cx: Math.round(dx),
    cy: Math.round(dy),
    r_px: diskR + (i % 2),
    crop_url: `/crops/d${i + 1}.svg`,
    ocr_guess: s.ocr ? { code: s.ocr[0], confidence: s.ocr[1] } : null,
    _code: s.code, // used only to draw the printed code on the synthetic disk
    zone: {
      diameter_mm: s.mm,
      radius_px: Math.round(isNoZone ? diskR : zoneR),
      polygon,
      confidence: s.conf,
      flags: s.flags,
    },
  }
})

// ---- analyze.json --------------------------------------------------------
const analyze = {
  image_id: 'mock-a3f9c1',
  image_url: '/plate.svg',
  width: W,
  height: H,
  exif_orientation_applied: true,
  dish: { cx, cy, r: dishR },
  calibration: {
    px_per_mm: PX_PER_MM,
    source: 'disk_6mm',
    n_disks_used: 8,
    disk_ellipticity: 0.021,
  },
  disks: disks.map(({ _code, ...d }) => d),
  warnings: ['camera_tilt_minor'],
}

mkdirSync(resolve(root, 'src/mocks'), { recursive: true })
writeFileSync(resolve(root, 'src/mocks/analyze.json'), JSON.stringify(analyze, null, 2))

// ---- synthetic plate photo (public/plate.svg) ----------------------------
function diskCrop(d) {
  // small square crop around the disk, used as the row thumbnail
  const s = 120
  const label = d._code || '??'
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${s}" height="${s}" viewBox="0 0 ${s} ${s}">
  <rect width="${s}" height="${s}" fill="#C4B790"/>
  <circle cx="${s / 2}" cy="${s / 2}" r="${s / 2 - 6}" fill="#ECE5D3"/>
  <circle cx="${s / 2}" cy="${s / 2}" r="30" fill="#F8F6F1" stroke="#A99E82" stroke-width="2"/>
  <text x="${s / 2}" y="${s / 2 + 4}" font-family="monospace" font-size="15" font-weight="700" fill="#5f5847" text-anchor="middle">${label}</text>
</svg>`
}

const zoneCircles = disks
  .filter((d) => !d.zone.flags.includes('no_zone'))
  .map((d) => {
    const fuzzy = d.zone.flags.includes('fuzzy_edge')
    return `<circle cx="${d.cx}" cy="${d.cy}" r="${d.zone.radius_px}" fill="#ECE5D3" ${
      fuzzy ? 'filter="url(#soft)"' : 'filter="url(#edge)"'
    }/>`
  })
  .join('\n    ')

const diskCircles = disks
  .map(
    (d) => `<g>
      <circle cx="${d.cx}" cy="${d.cy}" r="${d.r_px}" fill="#F8F6F1" stroke="#A99E82" stroke-width="2.5"/>
      <circle cx="${d.cx}" cy="${d.cy}" r="${d.r_px - 6}" fill="none" stroke="#D8CFB6" stroke-width="1.5"/>
      <text x="${d.cx}" y="${d.cy + 4}" font-family="monospace" font-size="13" font-weight="700" fill="#6b6350" text-anchor="middle">${
        d._code || ''
      }</text>
    </g>`
  )
  .join('\n    ')

const plateSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <defs>
    <radialGradient id="agar" cx="42%" cy="38%" r="72%">
      <stop offset="0%" stop-color="#EFE9D8"/>
      <stop offset="70%" stop-color="#E4DABE"/>
      <stop offset="100%" stop-color="#D3C8A8"/>
    </radialGradient>
    <radialGradient id="vign" cx="50%" cy="50%" r="50%">
      <stop offset="70%" stop-color="#000000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0.28"/>
    </radialGradient>
    <filter id="lawn"><feTurbulence type="fractalNoise" baseFrequency="0.055 0.06" numOctaves="3" seed="7" result="n"/>
      <feColorMatrix in="n" type="matrix" values="0 0 0 0 0.77  0 0 0 0 0.72  0 0 0 0 0.56  0 0 0 0.6 0"/>
    </filter>
    <filter id="edge"><feGaussianBlur stdDeviation="2.2"/></filter>
    <filter id="soft"><feGaussianBlur stdDeviation="7"/></filter>
    <clipPath id="dishClip"><circle cx="${cx}" cy="${cy}" r="${dishR - 8}"/></clipPath>
  </defs>

  <rect width="${W}" height="${H}" fill="#20201A"/>
  <circle cx="${cx}" cy="${cy}" r="${dishR + 10}" fill="#171712"/>
  <circle cx="${cx}" cy="${cy}" r="${dishR}" fill="url(#agar)"/>

  <g clip-path="url(#dishClip)">
    <rect x="${cx - dishR}" y="${cy - dishR}" width="${dishR * 2}" height="${dishR * 2}" filter="url(#lawn)"/>
    ${zoneCircles}
    ${diskCircles}
  </g>

  <circle cx="${cx}" cy="${cy}" r="${dishR}" fill="none" stroke="#B7AC8E" stroke-width="6" opacity="0.7"/>
  <circle cx="${cx}" cy="${cy}" r="${dishR - 3}" fill="url(#vign)"/>
  <ellipse cx="${cx - 150}" cy="${cy - 170}" rx="220" ry="130" fill="#ffffff" opacity="0.06"/>
</svg>`

mkdirSync(resolve(root, 'public/crops'), { recursive: true })
writeFileSync(resolve(root, 'public/plate.svg'), plateSvg)
for (const d of disks) writeFileSync(resolve(root, `public/crops/${d.id}.svg`), diskCrop(d))

console.log(`✓ wrote src/mocks/analyze.json (${disks.length} disks)`)
console.log('✓ wrote public/plate.svg + public/crops/*.svg')
