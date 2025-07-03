import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Html } from '@react-three/drei'
import { useState, useMemo, useRef } from 'react'
import * as THREE from 'three'

// Realistic Walmart product data, grouped by aisle, with stock and promo
const products = [
  { name: 'Great Value Milk', aisle: 'Dairy', position: [2, 0.5, -4], grid: [6, 2], stock: 'in', promo: true },
  { name: 'Yoplait Yogurt', aisle: 'Dairy', position: [2, 0.5, -3], grid: [6, 3], stock: 'low', promo: false },
  { name: "Lay's Classic Chips", aisle: 'Snacks', position: [-2, 0.5, 0], grid: [2, 7], stock: 'in', promo: false },
  { name: "Doritos Nacho Cheese", aisle: 'Snacks', position: [-2, 0.5, 1], grid: [2, 8], stock: 'out', promo: false },
  { name: 'Coca-Cola 2L', aisle: 'Drinks', position: [4, 0.5, 2], grid: [8, 10], stock: 'in', promo: true },
  { name: 'Pepsi 2L', aisle: 'Drinks', position: [4, 0.5, 3], grid: [8, 11], stock: 'in', promo: false },
  { name: 'Tyson Chicken Breast', aisle: 'Meat', position: [-4, 0.5, 4], grid: [0, 12], stock: 'low', promo: false },
  { name: 'Oscar Mayer Bacon', aisle: 'Meat', position: [-4, 0.5, 5], grid: [0, 13], stock: 'in', promo: false },
  { name: 'Bananas', aisle: 'Produce', position: [-5, 0.5, -2], grid: [1, 4], stock: 'in', promo: false },
  { name: 'Fresh Strawberries', aisle: 'Produce', position: [-5, 0.5, -1], grid: [1, 5], stock: 'out', promo: true },
  { name: "Kellogg's Corn Flakes", aisle: 'Cereal', position: [5, 0.5, -2], grid: [11, 4], stock: 'in', promo: false },
  { name: 'Cheerios', aisle: 'Cereal', position: [5, 0.5, -1], grid: [11, 5], stock: 'in', promo: false },
]
const entryPosition = [0, 0, 7]
const entryGrid = [6, 13]
const gridSize = 13

function astar(start, goal, isWalkable) {
  const [sx, sz] = start, [gx, gz] = goal
  const open = [[sx, sz]]
  const cameFrom = {}
  const gScore = { [`${sx},${sz}`]: 0 }
  const fScore = { [`${sx},${sz}`]: Math.abs(gx - sx) + Math.abs(gz - sz) }
  const dirs = [[1,0],[-1,0],[0,1],[0,-1]]
  while (open.length) {
    open.sort((a, b) => (fScore[`${a[0]},${a[1]}`] ?? 1e9) - (fScore[`${b[0]},${b[1]}`] ?? 1e9))
    const [x, z] = open.shift()
    if (x === gx && z === gz) {
      let path = [[x, z]]
      let curr = [x, z]
      while (cameFrom[`${curr[0]},${curr[1]}`]) {
        curr = cameFrom[`${curr[0]},${curr[1]}`]
        path.push(curr)
      }
      return path.reverse()
    }
    for (const [dx, dz] of dirs) {
      const nx = x + dx, nz = z + dz
      if (nx < 0 || nx > gridSize || nz < 0 || nz > gridSize) continue
      if (!isWalkable(nx, nz)) continue
      const tentative = (gScore[`${x},${z}`] ?? 1e9) + 1
      if (tentative < (gScore[`${nx},${nz}`] ?? 1e9)) {
        cameFrom[`${nx},${nz}`] = [x, z]
        gScore[`${nx},${nz}`] = tentative
        fScore[`${nx},${nz}`] = tentative + Math.abs(gx - nx) + Math.abs(gz - nz)
        if (!open.some(([ox, oz]) => ox === nx && oz === nz)) open.push([nx, nz])
      }
    }
  }
  return []
}

function gridTo3D([x, z]) {
  return [x - 6, 0.15, z - 6]
}

function PathLine({ path, highlightColor = '#38bdf8' }) {
  const ref = useRef()
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.material.color.setHSL(0.6 + 0.1 * Math.sin(clock.getElapsedTime() * 2), 1, 0.6)
    }
  })
  if (!path || path.length < 2) return null
  const points = path.map(gridTo3D).map(([x, y, z]) => new THREE.Vector3(x, y, z))
  return (
    <line ref={ref}>
      <bufferGeometry attach="geometry">
        <bufferAttribute
          attach="attributes-position"
          count={points.length}
          array={new Float32Array(points.flat())}
          itemSize={3}
        />
      </bufferGeometry>
      <lineBasicMaterial attach="material" color={highlightColor} linewidth={6} />
    </line>
  )
}

function Store3D({ highlights, path }) {
  const aisles = [
    { name: 'Dairy', color: '#fbbf24', x: 2, zStart: -4, zEnd: -3 },
    { name: 'Snacks', color: '#f472b6', x: -2, zStart: 0, zEnd: 1 },
    { name: 'Drinks', color: '#38bdf8', x: 4, zStart: 2, zEnd: 3 },
    { name: 'Meat', color: '#a3e635', x: -4, zStart: 4, zEnd: 5 },
    { name: 'Produce', color: '#34d399', x: -5, zStart: -2, zEnd: -1 },
    { name: 'Cereal', color: '#818cf8', x: 5, zStart: -2, zEnd: -1 },
  ]
  return (
    <>
      {/* Floor */}
      <mesh position={[0, 0, 0]} receiveShadow>
        <boxGeometry args={[14, 0.1, 14]} />
        <meshStandardMaterial color="#f1f5f9" />
      </mesh>
      {/* Walls */}
      <mesh position={[0, 1, -7]}>
        <boxGeometry args={[14, 2, 0.2]} />
        <meshStandardMaterial color="#e0e7ef" />
      </mesh>
      <mesh position={[-7, 1, 0]}>
        <boxGeometry args={[0.2, 2, 14]} />
        <meshStandardMaterial color="#e0e7ef" />
      </mesh>
      <mesh position={[7, 1, 0]}>
        <boxGeometry args={[0.2, 2, 14]} />
        <meshStandardMaterial color="#e0e7ef" />
      </mesh>
      {/* Entry Gate (polished) */}
      <mesh position={entryPosition}>
        <boxGeometry args={[2, 0.2, 0.2]} />
        <meshStandardMaterial color="#38bdf8" />
      </mesh>
      <Html position={[entryPosition[0], 0.5, entryPosition[2] + 0.7]} center style={{ pointerEvents: 'none' }}>
        <div className="text-xs font-bold px-3 py-1 rounded shadow bg-blue-400 text-white animate-pulse border-2 border-white">Entry</div>
      </Html>
      {/* Aisles (as blocks) */}
      {aisles.map(aisle => (
        <mesh key={aisle.name} position={[aisle.x, 0.5, (aisle.zStart + aisle.zEnd) / 2]} castShadow>
          <boxGeometry args={[1.2, 1, Math.abs(aisle.zEnd - aisle.zStart) + 1.2]} />
          <meshStandardMaterial color={aisle.color} opacity={0.18} transparent />
          <Html position={[0, 0.7, 0]} center style={{ pointerEvents: 'none' }}>
            <div className="text-xs font-bold px-2 py-1 rounded shadow bg-white/80 text-slate-700 border border-blue-100">{aisle.name}</div>
          </Html>
        </mesh>
      ))}
      {/* Products (animated label + 3D icon, stock/promo color) */}
      {products.map((p, i) => (
        <group key={p.name} position={p.position}>
          {/* Product block */}
          <mesh castShadow>
            <boxGeometry args={[0.7, 0.7, 0.7]} />
            <meshStandardMaterial color={
              p.stock === 'out' ? '#d1d5db' :
              highlights.includes(p.name) ? '#fbbf24' :
              p.promo ? '#38bdf8' : '#64748b'
            } opacity={p.stock === 'out' ? 0.5 : 1} />
          </mesh>
          {/* Animated 3D icon above product */}
          <AnimatedIcon highlight={highlights.includes(p.name)} promo={p.promo} stock={p.stock} />
          {/* Animated product label */}
          <Html position={[0, 0.7, 0]} center style={{ pointerEvents: 'none' }}>
            <div className={`text-xs font-bold px-2 py-1 rounded shadow border ${
              p.stock === 'out' ? 'bg-gray-200 text-gray-400 border-gray-300 line-through' :
              highlights.includes(p.name) ? 'bg-yellow-300 text-yellow-900 border-yellow-400 animate-bounce' :
              p.promo ? 'bg-blue-200 text-blue-900 border-blue-400 animate-pulse' :
              'bg-white/80 text-slate-700 border-blue-100'
            }`}>
              {p.name}
              {p.promo && <span className="ml-2 text-xs font-bold text-blue-600">Promo</span>}
              {p.stock === 'low' && <span className="ml-2 text-xs font-bold text-yellow-500">Low</span>}
              {p.stock === 'out' && <span className="ml-2 text-xs font-bold text-red-400">Out</span>}
            </div>
          </Html>
        </group>
      ))}
      {/* Checkout */}
      <mesh position={[0, 0.5, -6]}>
        <boxGeometry args={[2, 1, 1]} />
        <meshStandardMaterial color="#22c55e" />
        <Html position={[0, 0.7, 0]} center style={{ pointerEvents: 'none' }}>
          <div className="text-xs font-bold px-2 py-1 rounded shadow bg-green-300 text-green-900">Checkout</div>
        </Html>
      </mesh>
      {/* Path Line */}
      <PathLine path={path} highlightColor={highlights.length ? '#38bdf8' : undefined} />
      {/* Lighting */}
      <ambientLight intensity={0.7} />
      <directionalLight position={[5, 10, 5]} intensity={0.7} castShadow />
    </>
  )
}

function AnimatedIcon({ highlight, promo, stock }) {
  const ref = useRef()
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.position.y = 1.1 + 0.15 * Math.sin(clock.getElapsedTime() * 2)
      ref.current.material.emissiveIntensity = highlight ? 0.7 : promo ? 0.5 : 0.2
    }
  })
  let color = '#fbbf24'
  if (stock === 'out') color = '#d1d5db'
  else if (promo) color = '#38bdf8'
  return (
    <mesh ref={ref} position={[0, 1.1, 0]}>
      <sphereGeometry args={[0.18, 24, 24]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.2} />
    </mesh>
  )
}

function CameraFocus({ target }) {
  const { camera } = useThree()
  const targetVec = useMemo(() => new THREE.Vector3(...target), [target])
  useFrame(() => {
    camera.position.lerp(new THREE.Vector3(target[0], 8, target[2] + 8), 0.08)
    camera.lookAt(targetVec)
  })
  return null
}

// Nearest-neighbor TSP for demo: entry -> closest item -> next closest ...
function getOptimalPath(entry, items, isWalkable) {
  if (!items.length) return []
  let order = []
  let curr = entry
  let remaining = [...items]
  while (remaining.length) {
    let bestIdx = 0
    let bestDist = Math.abs(curr[0] - remaining[0].grid[0]) + Math.abs(curr[1] - remaining[0].grid[1])
    for (let i = 1; i < remaining.length; ++i) {
      const d = Math.abs(curr[0] - remaining[i].grid[0]) + Math.abs(curr[1] - remaining[i].grid[1])
      if (d < bestDist) { bestDist = d; bestIdx = i }
    }
    order.push(remaining[bestIdx])
    curr = remaining[bestIdx].grid
    remaining.splice(bestIdx, 1)
  }
  // Build full path: entry -> item1 -> item2 ...
  let path = []
  curr = entry
  for (const item of order) {
    const seg = astar(curr, item.grid, isWalkable)
    if (seg.length > 1) path.push(...(path.length ? seg.slice(1) : seg))
    curr = item.grid
  }
  return path
}

export default function Map3D() {
  const [input, setInput] = useState('')
  const [chips, setChips] = useState([])
  const selectedProducts = useMemo(() =>
    products.filter(p => chips.some(c => p.name.toLowerCase().includes(c.toLowerCase()))),
    [chips]
  )
  const isWalkable = (x, z) => x >= 0 && x <= gridSize && z >= 0 && z <= gridSize
  const path = useMemo(() =>
    selectedProducts.length ? getOptimalPath(entryGrid, selectedProducts, isWalkable) : null
  , [selectedProducts])
  // Camera focus: center on last item or entry
  const focusTarget = selectedProducts.length ? selectedProducts[selectedProducts.length - 1].position : entryPosition
  return (
    <div className="relative h-[80vh] rounded-2xl shadow-2xl bg-white/80 backdrop-blur-lg overflow-hidden border border-blue-100">
      {/* Shopping List Input */}
      <div className="absolute top-6 left-1/2 -translate-x-1/2 z-20 w-full max-w-xl flex flex-col items-center">
        <div className="flex flex-wrap gap-2 mb-2">
          {chips.map((chip, i) => (
            <span key={i} className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full font-semibold text-sm flex items-center gap-1">
              {chip}
              <button className="ml-1 text-blue-400 hover:text-blue-700" onClick={() => setChips(chips.filter((_, j) => j !== i))}>&times;</button>
            </span>
          ))}
        </div>
        <input
          className="w-full px-5 py-3 rounded-xl shadow bg-white/90 border border-blue-200 text-lg font-semibold focus:ring-2 focus:ring-blue-400 outline-none"
          placeholder="Type a product and press Enter (e.g. Milk, Chips)"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if ((e.key === 'Enter' || e.key === ',') && input.trim()) {
              setChips([...chips, input.replace(/,$/, '').trim()])
              setInput('')
            }
            if (e.key === 'Backspace' && !input && chips.length) {
              setChips(chips.slice(0, -1))
            }
          }}
        />
      </div>
      {/* 3D Canvas */}
      <Canvas camera={{ position: [0, 8, 12], fov: 40 }} shadows>
        <Store3D highlights={selectedProducts.map(p => p.name)} path={path} />
        {selectedProducts.length > 0 && <CameraFocus target={focusTarget} />}
        <OrbitControls enablePan enableZoom enableRotate maxPolarAngle={Math.PI / 2.1} minPolarAngle={0.2} />
      </Canvas>
    </div>
  )
} 