export function Card({ children, className = '' }) {
  return (
    <div className={`rounded-2xl shadow-lg border border-blue-100 bg-white/80 backdrop-blur ${className}`}>
      {children}
    </div>
  )
} 