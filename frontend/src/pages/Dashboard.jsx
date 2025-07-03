import { useState, useEffect } from 'react'
import { Card } from '../components/Card'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, RadarChart, PolarGrid, PolarAngleAxis, Radar } from 'recharts'
import { motion } from 'framer-motion'

const spendingData = [
  { category: 'Groceries', amount: 120 },
  { category: 'Snacks', amount: 60 },
  { category: 'Drinks', amount: 40 },
  { category: 'Household', amount: 80 },
]
const topPurchases = [
  { item: 'Chicken Breast', price: '$12.99' },
  { item: 'Broccoli', price: '$3.49' },
  { item: 'Greek Yogurt', price: '$5.99' },
  { item: 'Almonds', price: '$7.99' },
  { item: 'Orange Juice', price: '$4.99' },
]
const dietaryData = [
  { name: 'Protein', value: 80 },
  { name: 'Carbs', value: 60 },
  { name: 'Fats', value: 40 },
  { name: 'Fiber', value: 30 },
]
const interactionHistory = [
  { prompt: 'Plan my week', date: '2024-06-25' },
  { prompt: 'Add chicken', date: '2024-06-25' },
  { prompt: 'Show healthy snacks', date: '2024-06-24' },
  { prompt: 'Find vegan options', date: '2024-06-23' },
]
const COLORS = ['#2563eb', '#fbbf24', '#10b981', '#f472b6']

export default function Dashboard() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 py-8">
      {/* Spending Habits */}
      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} whileHover={{ scale: 1.03, boxShadow: '0 8px 32px 0 rgba(37,99,235,0.10)' }}>
        <Card className="p-7 flex flex-col h-full hover:shadow-2xl transition-all">
          <div className="font-bold text-xl mb-3 text-blue-700 tracking-tight">Spending Habits</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={spendingData}>
              <XAxis dataKey="category" fontSize={13} tickLine={false} axisLine={false} />
              <YAxis fontSize={13} tickLine={false} axisLine={false} />
              <Tooltip />
              <Bar dataKey="amount" fill="#2563eb" radius={[10,10,0,0]} shadow="true" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </motion.div>
      {/* Top Purchases */}
      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} whileHover={{ scale: 1.03, boxShadow: '0 8px 32px 0 rgba(37,99,235,0.10)' }}>
        <Card className="p-7 flex flex-col h-full hover:shadow-2xl transition-all">
          <div className="font-bold text-xl mb-3 text-blue-700 tracking-tight">Top Purchases</div>
          <ul className="divide-y">
            {topPurchases.map((item, i) => (
              <li key={i} className="py-3 flex justify-between text-gray-700 text-base">
                <span>{item.item}</span>
                <span className="font-semibold">{item.price}</span>
              </li>
            ))}
          </ul>
        </Card>
      </motion.div>
      {/* Dietary Profile Adherence */}
      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} whileHover={{ scale: 1.03, boxShadow: '0 8px 32px 0 rgba(16,185,129,0.10)' }}>
        <Card className="p-7 flex flex-col h-full hover:shadow-2xl transition-all">
          <div className="font-bold text-xl mb-3 text-green-700 tracking-tight">Dietary Profile Adherence</div>
          <ResponsiveContainer width="100%" height={180}>
            <RadarChart data={dietaryData} outerRadius={75}>
              <PolarGrid />
              <PolarAngleAxis dataKey="name" fontSize={13} />
              <Radar dataKey="value" stroke="#10b981" fill="#10b981" fillOpacity={0.4} />
            </RadarChart>
          </ResponsiveContainer>
        </Card>
      </motion.div>
      {/* Agent Interaction History */}
      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="md:col-span-2 xl:col-span-1" whileHover={{ scale: 1.03, boxShadow: '0 8px 32px 0 rgba(37,99,235,0.10)' }}>
        <Card className="p-7 flex flex-col h-full hover:shadow-2xl transition-all">
          <div className="font-bold text-xl mb-3 text-blue-700 tracking-tight">Agent Interaction History</div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-base">
              <thead>
                <tr className="text-left text-gray-500">
                  <th className="py-2 pr-4">Prompt</th>
                  <th className="py-2">Date</th>
                </tr>
              </thead>
              <tbody>
                {interactionHistory.map((row, i) => (
                  <tr key={i} className="border-t">
                    <td className="py-3 pr-4 text-gray-700">{row.prompt}</td>
                    <td className="py-3 text-gray-500">{row.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.div>
    </div>
  )
} 