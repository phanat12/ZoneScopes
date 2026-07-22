import SIRChip from './SIRChip'

// Antibiogram table for the Results screen (web_spec.md §4.4): antibiotic → mm →
// S/I/R, marking values a human edited away from the model's measurement.
export default function ResultTable({ results, antibioticLabels }) {
  const rows = results.filter((r) => r.antibiotic)
  return (
    <div className="card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-ink-faint bg-agar-50">
            <th className="font-semibold px-3 py-2 w-8">#</th>
            <th className="font-semibold px-2 py-2">ยา</th>
            <th className="font-semibold px-2 py-2 text-right">มม.</th>
            <th className="font-semibold px-3 py-2 text-center">ผล</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.disk.id} className="border-t border-agar-200 align-middle">
              <td className="tnum px-3 py-2.5 text-ink-faint">{r.disk.index}</td>
              <td className="px-2 py-2.5">
                <div className="tnum font-semibold text-ink">{r.antibiotic}</div>
                <div className="text-[11px] text-ink-faint truncate max-w-[10rem]">
                  {antibioticLabels[r.antibiotic] || ''}
                </div>
              </td>
              <td className="px-2 py-2.5 text-right">
                <span className="tnum font-semibold text-ink">{r.diameterMm.toFixed(1)}</span>
                {r.editedByUser && (
                  <div
                    className="text-[10px] text-teal font-semibold"
                    title={`โมเดลวัดได้ ${r.originalDiameterMm.toFixed(1)} มม.`}
                  >
                    แก้โดยคน
                  </div>
                )}
                {r.disk.zone.flags.includes('no_zone') && (
                  <div className="text-[10px] text-ink-faint">ไม่มีวง</div>
                )}
              </td>
              <td className="px-3 py-2.5 text-center">
                <SIRChip value={r.interpretation} size="lg" title={r.reason} />
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={4} className="px-3 py-8 text-center text-ink-faint">
                ยังไม่มี disk ที่ระบุยา
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
