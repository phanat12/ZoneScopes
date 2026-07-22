import FlagBadge from './FlagBadge'

// Keeps px_per_mm and ellipticity visible so the user can sanity-check the scale
// and catch a tilted camera (web_spec.md §4.1, §9.6). Never hidden.
export default function CalibrationBar({ calibration, warnings = [], disks }) {
  const tiltHigh = calibration.disk_ellipticity > 0.08
  return (
    <div className="px-4 py-2.5 bg-white border-b border-agar-200">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px]">
        <Metric label="สเกล" value={`${calibration.px_per_mm.toFixed(1)} px/มม.`} />
        <Metric
          label="ความรี disk"
          value={calibration.disk_ellipticity.toFixed(3)}
          warn={tiltHigh}
          hint={tiltHigh ? 'disk รีเกินเกณฑ์ — กล้องอาจเอียง ค่าที่วัดอาจเพี้ยน' : 'disk กลมดี'}
        />
        <Metric label="disk ที่พบ" value={disks?.length ?? calibration.n_disks_used} />
        <span className="text-ink-faint">คาลิเบรตจาก {calibration.source === 'disk_6mm' ? 'disk 6 มม.' : calibration.source}</span>
      </div>
      {warnings.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {warnings.map((w) => (
            <FlagBadge key={w} code={w} kind="warning" />
          ))}
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, warn, hint }) {
  return (
    <span className="inline-flex items-center gap-1.5" title={hint}>
      <span className="field-label">{label}</span>
      <span className={`tnum font-semibold ${warn ? 'text-sir-i' : 'text-ink'}`}>
        {value}
        {warn && ' ⚠'}
      </span>
    </span>
  )
}
