import { Routes, Route, Link, useLocation } from 'react-router-dom'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import Map from './pages/Map'
import Map3D from './pages/Map3D'
import { createContext } from 'react'

function Navbar() {
  const location = useLocation()
  const navLinks = [
    { to: '/', label: 'Mission Control' },
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/map', label: 'Store Map' },
    { to: '/map3d', label: '3D Store Map' }
  ]
  return (
    <nav className="sticky top-0 z-30 w-full bg-white/80 backdrop-blur border-b border-blue-100 shadow-sm flex items-center px-6 py-3 mb-8 rounded-b-2xl">
      <div className="flex items-center gap-8 w-full max-w-6xl mx-auto">
        {/* Optional: Walmart logo/avatar */}
        <span className="text-2xl font-extrabold text-blue-700 tracking-tight mr-6">Walmart AI</span>
        <div className="flex gap-4 flex-1">
          {navLinks.map(link => (
            <Link
              key={link.to}
              to={link.to}
              className={`px-4 py-2 rounded-lg font-semibold transition-all text-base
                ${location.pathname === link.to ? 'bg-blue-600 text-white shadow' : 'text-blue-700 hover:bg-blue-100'}`}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  )
}

export const PremiumUserContext = createContext({ isPremium: true })

export default function App() {
  return (
    <PremiumUserContext.Provider value={{ isPremium: true }}>
      <div className="min-h-screen font-sans bg-gradient-to-br from-blue-50 via-white to-blue-100">
        <Navbar />
        <div className="max-w-6xl mx-auto px-4">
          <Routes>
            <Route path="/" element={<Chat />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/map" element={<Map />} />
            <Route path="/map3d" element={<Map3D />} />
          </Routes>
        </div>
      </div>
    </PremiumUserContext.Provider>
  )
}