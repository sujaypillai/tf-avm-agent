import { BrowserRouter, Routes, Route } from "react-router-dom"
import { MainLayout } from "./components/layout/MainLayout"
import { useTheme } from "./hooks/useTheme"

function App() {
  // Initialize theme
  useTheme()

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/*" element={<MainLayout />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
