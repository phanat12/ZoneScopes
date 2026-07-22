// Client-side export helpers. Builds the /api/report payload (web_spec.md §5.4)
// and, in mock mode, generates the CSV locally so M1 works with no backend.
// edited_by_user + original_diameter_mm are always kept — human corrections are
// free training signal and the human-in-the-loop selling point (§5.4).

export function buildReportPayload({ analysis, plateId, organism, results }) {
  return {
    image_id: analysis.image_id,
    plate_id: plateId || null,
    organism,
    results: results
      .filter((r) => r.antibiotic)
      .map((r) => ({
        disk_id: r.disk.id,
        antibiotic: r.antibiotic,
        diameter_mm: round1(r.diameterMm),
        interpretation: r.interpretation,
        edited_by_user: r.editedByUser,
        original_diameter_mm: round1(r.originalDiameterMm),
      })),
  }
}

export function resultsToCsv({ plateId, organism, organismLabel, standard, results }) {
  const meta = [
    `# ZoneScope report`,
    `# plate_id,${csvCell(plateId || '')}`,
    `# organism,${csvCell(organismLabel || organism || '')}`,
    `# standard,${csvCell(standard || '')}`,
    `# exported,${new Date().toISOString()}`,
  ]
  const header = ['disk', 'antibiotic', 'diameter_mm', 'interpretation', 'edited_by_user', 'original_diameter_mm', 'flags']
  const rows = results
    .filter((r) => r.antibiotic)
    .map((r) =>
      [
        r.disk.index,
        r.antibiotic,
        round1(r.diameterMm),
        r.interpretation,
        r.editedByUser,
        round1(r.originalDiameterMm),
        (r.flags || []).join('|'),
      ]
        .map(csvCell)
        .join(',')
    )
  return [...meta, header.join(','), ...rows].join('\n')
}

export function downloadCsv(filename, csv) {
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function round1(n) {
  return Math.round(n * 10) / 10
}

function csvCell(v) {
  const s = String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}
