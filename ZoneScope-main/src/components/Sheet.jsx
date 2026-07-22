import { useEffect } from 'react'
import { createPortal } from 'react-dom'

// Bottom sheet for mobile pickers. Slides up, dims the page, closes on backdrop
// tap / Escape. Keeps focus handling simple and respects reduced motion via CSS.
export default function Sheet({ open, onClose, title, children }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex flex-col justify-end">
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-[1px] animate-[fade_.15s_ease]" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative bg-agar-50 rounded-t-2xl shadow-sheet max-h-[85vh] flex flex-col animate-[slideup_.2s_ease]"
      >
        <div className="pt-2.5 pb-1 flex justify-center">
          <span className="h-1.5 w-10 rounded-full bg-agar-300" />
        </div>
        {title && (
          <div className="px-5 pb-2 flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink">{title}</h2>
            <button onClick={onClose} className="text-ink-faint text-sm font-medium px-2 py-1">
              ปิด
            </button>
          </div>
        )}
        <div className="overflow-y-auto px-3 pb-[max(1rem,env(safe-area-inset-bottom))]">{children}</div>
      </div>
      <style>{`
        @keyframes slideup { from { transform: translateY(12px); opacity: .6 } to { transform: none; opacity: 1 } }
        @keyframes fade { from { opacity: 0 } to { opacity: 1 } }
      `}</style>
    </div>,
    document.body
  )
}
