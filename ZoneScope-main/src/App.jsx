import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import Upload from './pages/Upload'
import Processing from './pages/Processing'
import Review from './pages/Review'
import Results from './pages/Results'

// HashRouter keeps deep links working when served as static files without
// server-side route rewrites.
export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<Upload />} />
        <Route path="/processing" element={<Processing />} />
        <Route path="/review" element={<Review />} />
        <Route path="/results" element={<Results />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  )
}
