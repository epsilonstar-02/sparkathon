import { useState } from 'react'
import { motion } from 'framer-motion'
import { Card } from '../components/Card'

const aisleCoordinates = {
  Produce:  { x: 60,  y: 210 },  // Lettuce (left, by green veggies)
  Dairy:    { x: 340, y: 60  },  // Milk (back wall, left fridge)
  Snacks:   { x: 220, y: 220 },  // Chips (middle shelf)
  Drinks:   { x: 410, y: 170 },  // Juice (back wall, right fridge)
  Checkout: { x: 540, y: 270 }   // Pay (rightmost, by green shelves)
};
const items = [
  { item: 'Lettuce', aisle: 'Produce' },
  { item: 'Milk', aisle: 'Dairy' },
  { item: 'Chips', aisle: 'Snacks' },
  { item: 'Juice', aisle: 'Drinks' },
  { item: 'Pay', aisle: 'Checkout' }
];

export default function Map() {
  const [activeIdx, setActiveIdx] = useState(null)
  return (
    <div className="flex flex-col md:flex-row h-[80vh] gap-6 bg-gradient-to-br from-blue-50 to-white rounded-2xl p-4 shadow-xl">
      {/* Map Area */}
      <div className="relative flex-1 bg-white rounded-2xl shadow-lg overflow-hidden flex items-center justify-center min-h-[400px]">
        {/* Store Map Image */}
        <img src="/store-map.png" alt="Store Map" className="w-full h-full object-contain select-none pointer-events-none" />
        {/* Pins */}
        {items.map((item, i) => {
          const coord = aisleCoordinates[item.aisle]
          if (!coord) return null
          return (
            <motion.div
              key={item.aisle}
              className="absolute z-20 group"
              style={{ left: coord.x, top: coord.y, transform: 'translate(-50%, -50%)' }}
              animate={activeIdx === i ? { scale: [1, 1.25, 1] } : { scale: 1 }}
              transition={{ duration: 0.7, repeat: activeIdx === i ? Infinity : 0, repeatType: 'loop' }}
            >
              <button
                className={`w-9 h-9 rounded-full shadow-lg border-2 border-white flex items-center justify-center transition-all
                  bg-gradient-to-br from-blue-500 to-blue-700 text-white font-bold text-base
                  ${activeIdx === i ? 'ring-4 ring-blue-200' : 'hover:ring-2 hover:ring-blue-300'}`}
                onClick={() => setActiveIdx(i)}
                tabIndex={0}
                aria-label={`${item.item} (${item.aisle})`}
              >
                {i + 1}
              </button>
              {/* Tooltip */}
              <div className="absolute left-1/2 -translate-x-1/2 mt-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition pointer-events-none">
                <div className="bg-white text-blue-700 text-xs font-semibold px-3 py-1 rounded shadow border border-blue-100">
                  {item.item} <span className="text-gray-400">({item.aisle})</span>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
      {/* Item List */}
      <Card className="w-full md:w-80 p-6 flex flex-col gap-3 bg-white/80 backdrop-blur sticky top-8 self-start shadow-lg rounded-2xl border border-blue-100">
        <div className="font-bold text-lg mb-2 text-blue-700">Shopping List</div>
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i}>
              <button
                className={`flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg transition font-semibold text-base
                  ${activeIdx === i ? 'bg-blue-100 text-blue-700 ring-2 ring-blue-300' : 'hover:bg-gray-100'}`}
                onClick={() => setActiveIdx(i)}
              >
                <span className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 text-white flex items-center justify-center text-base font-bold shadow">
                  {i + 1}
                </span>
                {item.item} <span className="ml-auto text-xs text-gray-400 font-normal">({item.aisle})</span>
              </button>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
} 