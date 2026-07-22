import { create } from 'zustand'
import { interpret } from '../lib/interpret'
import { saveRecentPanel } from '../lib/recentPanel'

// One in-memory session per plate (no DB in M1, web_spec.md §2). Holds the
// analyze response, the user's per-disk assignments/edits, and derived results.

function seedAssignments(analysis) {
  const map = {}
  for (const d of analysis.disks) {
    const guess = d.ocr_guess?.code || null
    map[d.id] = {
      diskId: d.id,
      // OCR guesses prefill the value but stay unconfirmed until the user
      // verifies (§3.4 — assist, don't decide).
      antibiotic: guess,
      source: guess ? 'ocr' : 'user',
      confirmed: false,
      diameterMm: d.zone.diameter_mm,
      originalDiameterMm: d.zone.diameter_mm,
    }
  }
  return map
}

export const useSession = create((set, get) => ({
  analysis: null,
  file: null, // the picked File object — needed for the real /api/analyze upload
  imageUrl: null, // object URL of the user's picked file (preview), or mock url
  fileName: null,
  organism: null,
  plateId: '',
  breakpoints: null,
  assignments: {},

  setBreakpoints: (bp) => set({ breakpoints: bp }),
  setFile: (file) => set({ file }),
  setOrganism: (organism) => set({ organism }),
  setPlateId: (plateId) => set({ plateId }),

  setAnalysis: (analysis, { imageUrl = null, fileName = null } = {}) =>
    set({
      analysis,
      imageUrl: imageUrl || analysis.image_url,
      fileName,
      assignments: seedAssignments(analysis),
    }),

  // pick an antibiotic for a disk (user action = confirmed)
  assignAntibiotic: (diskId, code) =>
    set((s) => ({
      assignments: {
        ...s.assignments,
        [diskId]: { ...s.assignments[diskId], antibiotic: code, source: 'user', confirmed: true },
      },
    })),

  clearAntibiotic: (diskId) =>
    set((s) => ({
      assignments: {
        ...s.assignments,
        [diskId]: { ...s.assignments[diskId], antibiotic: null, source: 'user', confirmed: false },
      },
    })),

  // accept the OCR guess as-is
  confirmOcr: (diskId) =>
    set((s) => ({
      assignments: {
        ...s.assignments,
        [diskId]: { ...s.assignments[diskId], source: 'user', confirmed: true },
      },
    })),

  setDiameter: (diskId, mm) =>
    set((s) => ({
      assignments: {
        ...s.assignments,
        [diskId]: { ...s.assignments[diskId], diameterMm: mm },
      },
    })),

  // apply a remembered panel: assign codes to disks in index order,
  // skipping duplicates already present
  applyPanel: (codes) =>
    set((s) => {
      const disks = [...s.analysis.disks].sort((a, b) => a.index - b.index)
      const next = { ...s.assignments }
      codes.forEach((code, i) => {
        const disk = disks[i]
        if (disk && code) {
          next[disk.id] = { ...next[disk.id], antibiotic: code, source: 'user', confirmed: true }
        }
      })
      return { assignments: next }
    }),

  persistPanel: () => {
    const { analysis, assignments } = get()
    if (!analysis) return
    const codes = [...analysis.disks]
      .sort((a, b) => a.index - b.index)
      .map((d) => assignments[d.id]?.antibiotic || null)
    saveRecentPanel(codes)
  },

  reset: () =>
    set({
      analysis: null,
      file: null,
      imageUrl: null,
      fileName: null,
      plateId: '',
      assignments: {},
    }),
}))

// ---- derived selectors (kept as plain fns to avoid re-render churn) --------

export function selectUsedAntibiotics(state, exceptDiskId) {
  const used = new Set()
  for (const [id, a] of Object.entries(state.assignments)) {
    if (id !== exceptDiskId && a.antibiotic) used.add(a.antibiotic)
  }
  return used
}

export function selectAssignedCount(state) {
  return Object.values(state.assignments).filter((a) => a.antibiotic).length
}

/** full per-disk result rows, ordered by disk index */
export function selectResults(state) {
  const { analysis, assignments, breakpoints, organism } = state
  if (!analysis) return []
  return [...analysis.disks]
    .sort((a, b) => a.index - b.index)
    .map((disk) => {
      const a = assignments[disk.id]
      const { result, rule, reason } = interpret(breakpoints, organism, a?.antibiotic, a?.diameterMm)
      return {
        disk,
        antibiotic: a?.antibiotic || null,
        source: a?.source,
        confirmed: a?.confirmed,
        diameterMm: a?.diameterMm,
        originalDiameterMm: a?.originalDiameterMm,
        editedByUser: a && Math.abs(a.diameterMm - a.originalDiameterMm) > 1e-9,
        interpretation: result,
        rule,
        reason,
        flags: disk.zone.flags,
        confidence: disk.zone.confidence,
      }
    })
}
