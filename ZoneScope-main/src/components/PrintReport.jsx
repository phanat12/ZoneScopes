import { SIR_META } from '../lib/interpret'

// Print-only report -> "Save as PDF" from the browser print dialog. Hidden on
// screen; the app chrome is hidden on paper. Static overlay (no zoom/pan) so it
// lays out predictably on a page.
export default function PrintReport({
  analysis,
  imageUrl,
  results,
  resultsById,
  antibioticLabels,
  organismLabel,
  plateId,
  standard,
  tally,
}) {
  const { width: W, height: H, dish, disks } = analysis
  const named = results.filter((r) => r.antibiotic)

  return (
    <div className="print-report">
      <style>{`
        .print-report { display: none; }
        @media print {
          .no-print { display: none !important; }
          .print-report { display: block !important; padding: 16px 20px; color: #1C2321; }
          @page { margin: 12mm; }
        }
      `}</style>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderBottom: '2px solid #0F7C82', paddingBottom: 8 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>ZoneScope — รายงานผล Disk Diffusion</div>
          <div style={{ fontSize: 12, color: '#465250', fontStyle: 'italic' }}>{organismLabel}</div>
        </div>
        <div style={{ textAlign: 'right', fontSize: 12, color: '#465250' }}>
          <div>รหัสจาน: <b>{plateId || '—'}</b></div>
          <div>{new Date().toLocaleString('th-TH')}</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 20, marginTop: 14 }}>
        {/* plate with static overlay */}
        <div style={{ position: 'relative', width: 340, flexShrink: 0 }}>
          <img src={imageUrl} alt="จาน" style={{ width: '100%', display: 'block', borderRadius: 8 }} />
          <svg viewBox={`0 0 ${W} ${H}`} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
            <circle cx={dish.cx} cy={dish.cy} r={dish.r} fill="none" stroke="#0F7C82" strokeOpacity="0.4" strokeWidth={3} />
            {disks.map((d) => {
              const sir = resultsById[d.id]
              const color = sir && SIR_META[sir] ? SIR_META[sir].hex : '#0F7C82'
              const noZone = d.zone.flags.includes('no_zone')
              const pts = d.zone.polygon.map((p) => p.join(',')).join(' ')
              return (
                <g key={d.id}>
                  {noZone ? (
                    <circle cx={d.cx} cy={d.cy} r={d.r_px + 6} fill="none" stroke={color} strokeWidth={4} strokeDasharray="7 9" />
                  ) : (
                    pts && <polygon points={pts} fill={color} fillOpacity={0.12} stroke={color} strokeWidth={5} strokeLinejoin="round" />
                  )}
                  <circle cx={d.cx} cy={d.cy} r={26} fill={color} />
                  <text x={d.cx} y={d.cy + 9} textAnchor="middle" fontSize={28} fontWeight="700" fill="#fff" fontFamily="monospace">
                    {d.index}
                  </text>
                </g>
              )
            })}
          </svg>
        </div>

        {/* table */}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            {['S', 'I', 'R', 'N/A'].map((k) => (
              <div key={k} style={{ flex: 1, textAlign: 'center', border: '1px solid #DCD0B2', borderRadius: 6, padding: '4px 0' }}>
                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'monospace', color: SIR_META[k].hex }}>{tally[k] || 0}</div>
                <div style={{ fontSize: 10, color: '#7A8582' }}>{k}</div>
              </div>
            ))}
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ textAlign: 'left', color: '#465250' }}>
                <th style={{ padding: '4px 6px' }}>#</th>
                <th style={{ padding: '4px 6px' }}>ยา</th>
                <th style={{ padding: '4px 6px', textAlign: 'right' }}>มม.</th>
                <th style={{ padding: '4px 6px', textAlign: 'center' }}>ผล</th>
              </tr>
            </thead>
            <tbody>
              {named.map((r) => (
                <tr key={r.disk.id} style={{ borderTop: '1px solid #EBE3CE' }}>
                  <td style={{ padding: '4px 6px', fontFamily: 'monospace' }}>{r.disk.index}</td>
                  <td style={{ padding: '4px 6px' }}>
                    <b style={{ fontFamily: 'monospace' }}>{r.antibiotic}</b>
                    <div style={{ fontSize: 10, color: '#7A8582' }}>{antibioticLabels[r.antibiotic]}</div>
                  </td>
                  <td style={{ padding: '4px 6px', textAlign: 'right', fontFamily: 'monospace', fontWeight: 700 }}>
                    {r.diameterMm.toFixed(1)}
                    {r.editedByUser && <span style={{ color: '#0F7C82', fontSize: 9 }}> *</span>}
                  </td>
                  <td style={{ padding: '4px 6px', textAlign: 'center' }}>
                    <span style={{ background: SIR_META[r.interpretation].hex, color: r.interpretation === 'N/A' ? '#465250' : '#fff', padding: '2px 8px', borderRadius: 5, fontWeight: 700, fontFamily: 'monospace' }}>
                      {r.interpretation}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ marginTop: 12, fontSize: 10, color: '#7A8582' }}>
        มาตรฐาน: {standard} · เครื่องหมาย * = ค่าที่ผู้ใช้แก้จากที่โมเดลวัด · รายงานสร้างโดย ZoneScope (เดโม)
      </div>
    </div>
  )
}
