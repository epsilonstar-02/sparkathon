// import { useState, useEffect } from 'react'
// import { Card } from '../components/Card'
// import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, RadarChart, PolarGrid, PolarAngleAxis, Radar } from 'recharts'
// import { motion } from 'framer-motion'

// const spendingData = [
//   { category: 'Groceries', amount: 120 },
//   { category: 'Snacks', amount: 60 },
//   { category: 'Drinks', amount: 40 },
//   { category: 'Household', amount: 80 },
// ]
// const topPurchases = [
//   { item: 'Chicken Breast', price: '$12.99' },
//   { item: 'Broccoli', price: '$3.49' },
//   { item: 'Greek Yogurt', price: '$5.99' },
//   { item: 'Almonds', price: '$7.99' },
//   { item: 'Orange Juice', price: '$4.99' },
// ]
// const dietaryData = [
//   { name: 'Protein', value: 80 },
//   { name: 'Carbs', value: 60 },
//   { name: 'Fats', value: 40 },
//   { name: 'Fiber', value: 30 },
// ]
// const interactionHistory = [
//   { prompt: 'Plan my week', date: '2024-06-25' },
//   { prompt: 'Add chicken', date: '2024-06-25' },
//   { prompt: 'Show healthy snacks', date: '2024-06-24' },
//   { prompt: 'Find vegan options', date: '2024-06-23' },
// ]
// const COLORS = ['#2563eb', '#fbbf24', '#10b981', '#f472b6']

// export default function Dashboard() {
//   return (
//     <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 py-8">
//       {/* Spending Habits */}
//       <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} whileHover={{ scale: 1.03, boxShadow: '0 8px 32px 0 rgba(37,99,235,0.10)' }}>
//         <Card className="p-7 flex flex-col h-full hover:shadow-2xl transition-all">
//           <div className="font-bold text-xl mb-3 text-blue-700 tracking-tight">Spending Habits</div>
//           <ResponsiveContainer width="100%" height={180}>
//             <BarChart data={spendingData}>
//               <XAxis dataKey="category" fontSize={13} tickLine={false} axisLine={false} />
//               <YAxis fontSize={13} tickLine={false} axisLine={false} />
//               <Tooltip />
//               <Bar dataKey="amount" fill="#2563eb" radius={[10,10,0,0]} shadow="true" />
//             </BarChart>
//           </ResponsiveContainer>
//         </Card>
//       </motion.div>
//       {/* Top Purchases */}
//       <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} whileHover={{ scale: 1.03, boxShadow: '0 8px 32px 0 rgba(37,99,235,0.10)' }}>
//         <Card className="p-7 flex flex-col h-full hover:shadow-2xl transition-all">
//           <div className="font-bold text-xl mb-3 text-blue-700 tracking-tight">Top Purchases</div>
//           <ul className="divide-y">
//             {topPurchases.map((item, i) => (
//               <li key={i} className="py-3 flex justify-between text-gray-700 text-base">
//                 <span>{item.item}</span>
//                 <span className="font-semibold">{item.price}</span>
//               </li>
//             ))}
//           </ul>
//         </Card>
//       </motion.div>
//       {/* Dietary Profile Adherence */}
//       <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} whileHover={{ scale: 1.03, boxShadow: '0 8px 32px 0 rgba(16,185,129,0.10)' }}>
//         <Card className="p-7 flex flex-col h-full hover:shadow-2xl transition-all">
//           <div className="font-bold text-xl mb-3 text-green-700 tracking-tight">Dietary Profile Adherence</div>
//           <ResponsiveContainer width="100%" height={180}>
//             <RadarChart data={dietaryData} outerRadius={75}>
//               <PolarGrid />
//               <PolarAngleAxis dataKey="name" fontSize={13} />
//               <Radar dataKey="value" stroke="#10b981" fill="#10b981" fillOpacity={0.4} />
//             </RadarChart>
//           </ResponsiveContainer>
//         </Card>
//       </motion.div>
//       {/* Agent Interaction History */}
//       <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="md:col-span-2 xl:col-span-1" whileHover={{ scale: 1.03, boxShadow: '0 8px 32px 0 rgba(37,99,235,0.10)' }}>
//         <Card className="p-7 flex flex-col h-full hover:shadow-2xl transition-all">
//           <div className="font-bold text-xl mb-3 text-blue-700 tracking-tight">Agent Interaction History</div>
//           <div className="overflow-x-auto">
//             <table className="min-w-full text-base">
//               <thead>
//                 <tr className="text-left text-gray-500">
//                   <th className="py-2 pr-4">Prompt</th>
//                   <th className="py-2">Date</th>
//                 </tr>
//               </thead>
//               <tbody>
//                 {interactionHistory.map((row, i) => (
//                   <tr key={i} className="border-t">
//                     <td className="py-3 pr-4 text-gray-700">{row.prompt}</td>
//                     <td className="py-3 text-gray-500">{row.date}</td>
//                   </tr>
//                 ))}
//               </tbody>
//             </table>
//           </div>
//         </Card>
//       </motion.div>
//     </div>
//   )
// } 

import { useState, useEffect } from 'react';
import { Card } from '../components/Card';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, 
  ResponsiveContainer, RadarChart, PolarGrid, 
  PolarAngleAxis, Radar, PieChart, Pie, Cell,
  AreaChart, Area, CartesianGrid
} from 'recharts';
import { motion } from 'framer-motion';
import { analyticsService } from '../api/services/analyticsService';

const COLORS = ['#2563eb', '#fbbf24', '#10b981', '#f472b6', '#8b5cf6'];

// Month names for seasonal trends
const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
];

// Day names for shopping times
const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export default function Dashboard() {
  const [dashboardData, setDashboardData] = useState({
    spendingData: [],
    topPurchases: [],
    dietaryData: [],
    interactionHistory: [],
    topBrands: [],
    shoppingTimes: { hourCounts: {}, dayCounts: {} },
    seasonalTrends: {},
    orderFrequency: 0,
    loading: true
  });

  const userId = "cmcqhdhix00jauwtg9jza2xo7"; // Replace with actual user ID

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await analyticsService.getDashboardData(userId);
        setDashboardData({
          ...data,
          loading: false
        });
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
        setDashboardData(prev => ({
          ...prev,
          loading: false
        }));
      }
    };

    fetchData();
  }, []);

  // Prepare shopping time data for visualization
  const shoppingTimeData = () => {
    const { hourCounts, dayCounts } = dashboardData.shoppingTimes;
    
    // Prepare hourly data
    const hourlyData = Array.from({ length: 24 }, (_, i) => ({
      hour: `${i}:00`,
      orders: hourCounts[i] || 0
    }));
    
    // Prepare daily data
    const dailyData = DAY_NAMES.map((day, i) => ({
      day,
      orders: dayCounts[i] || 0
    }));
    
    return { hourlyData, dailyData };
  };


const data = dashboardData.shoppingListCategories || [];
const total = data.reduce((sum, item) => sum + item.value, 0);

const dataWithTotal = data.map(item => ({
  ...item,
  total, // Attach total to each data item
}));

// Abbreviate long category names
const abbreviateName = (name) => {
  const abbreviations = {
    "Canned & Jarred Beans & Legumes": "Beans & Legumes",
    "Canned & Jarred Meats": "Canned Meats",
    "Canned & Jarred Poultry": "Canned Poultry",
    "Packaged Meals": "Pkg. Meals"
  };
  return abbreviations[name] || name;
};

// Custom tooltip component
const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const item = payload[0].payload;
    const percent = item.total ? ((item.value / item.total) * 100).toFixed(0) : '0';

    return (
      <div className="bg-white p-3 border border-gray-200 shadow-lg rounded-md">
        <p className="font-medium">{item.name}</p>
        <p className="text-sm">
          {item.value} items ({percent}%)
        </p>
      </div>
    );
  }
  return null;
};




  // Prepare seasonal trends data
  const seasonalTrendsData = () => {
    return Object.entries(dashboardData.seasonalTrends)
      .map(([month, amount]) => ({
        month: MONTH_NAMES[parseInt(month)],
        amount
      }));
  };

  if (dashboardData.loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 py-8">
        {[...Array(6)].map((_, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="p-6 flex flex-col h-full">
              <div className="h-6 bg-gray-200 rounded mb-4 w-3/4"></div>
              <div className="h-40 bg-gray-100 rounded animate-pulse"></div>
            </Card>
          </motion.div>
        ))}
      </div>
    );
  }

  const { 
    spendingData, 
    topPurchases, 
    dietaryData, 
    interactionHistory,
    topBrands,
    orderFrequency,
    totalSpent,
    totalOrders,
    averageOrderValue
  } = dashboardData;

  const { hourlyData, dailyData } = shoppingTimeData();
  const seasonalData = seasonalTrendsData();

  return (
    <div className="space-y-8 py-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 bg-gradient-to-r from-blue-50 to-blue-100 border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-gray-500 text-sm">Total Spent</h3>
              <p className="text-2xl font-bold text-blue-700">${totalSpent.toFixed(2)}</p>
            </div>
            <div className="bg-blue-100 p-3 rounded-full">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-gradient-to-r from-green-50 to-green-100 border border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-gray-500 text-sm">Total Orders</h3>
              <p className="text-2xl font-bold text-green-700">{totalOrders}</p>
            </div>
            <div className="bg-green-100 p-3 rounded-full">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
              </svg>
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-gradient-to-r from-purple-50 to-purple-100 border border-purple-200">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-gray-500 text-sm">Avg. Order Frequency</h3>
              <p className="text-2xl font-bold text-purple-700">{orderFrequency} days</p>
            </div>
            <div className="bg-purple-100 p-3 rounded-full">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </Card>
      </div>

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          {/* Spending Habits */}
          <motion.div 
            initial={{ opacity: 0, y: 30 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.1 }} 
          >
            <Card className="p-6 flex flex-col h-full">
              <div className="font-bold text-lg mb-4 text-blue-700 tracking-tight">Spending by Category</div>
              {spendingData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={spendingData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="category" fontSize={12} />
                    <YAxis fontSize={12} tickFormatter={(value) => `$${value}`} />
                    <Tooltip formatter={(value) => [`$${value}`, 'Amount']} />
                    <Bar dataKey="amount" fill="#2563eb" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-40 flex items-center justify-center text-gray-500">
                  No spending data available
                </div>
              )}
            </Card>
          </motion.div>

          {/* Top Brands */}
          <motion.div 
            initial={{ opacity: 0, y: 30 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.2 }} 
          >
            <Card className="p-6 flex flex-col h-full">
              <div className="font-bold text-lg mb-4 text-purple-700 tracking-tight">Top Brands</div>
              {topBrands.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={topBrands}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="total"
                      nameKey="brand"
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    >
                      {topBrands.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [`$${value.toFixed(2)}`, 'Amount']} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-40 flex items-center justify-center text-gray-500">
                  No brand data available
                </div>
              )}
            </Card>
          </motion.div>
        </div>

        {/* Middle Column */}
        <div className="space-y-6">
          {/* Top Purchases */}
          <motion.div 
            initial={{ opacity: 0, y: 30 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.3 }} 
          >
            <Card className="p-6 flex flex-col h-full">
              <div className="font-bold text-lg mb-4 text-blue-700 tracking-tight">Frequently Purchased Items</div>
              {topPurchases.length > 0 ? (
                <div className="space-y-4">
                  {topPurchases.map((item, i) => (
                    <div key={i} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                      {item.thumbnail ? (
                        <img 
                          src={item.thumbnail} 
                          alt={item.item} 
                          className="w-12 h-12 object-cover rounded-md"
                        />
                      ) : (
                        <div className="bg-gray-200 border-2 border-dashed rounded-xl w-12 h-12" />
                      )}
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">{item.item}</div>
                        <div className="text-sm text-gray-500">{item.price}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-40 flex items-center justify-center text-gray-500">
                  No purchase history
                </div>
              )}
            </Card>
          </motion.div>

          {/* Shopping Times */}
          <motion.div 
            initial={{ opacity: 0, y: 30 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.4 }} 
          >
            <Card className="p-6 flex flex-col h-full">
              <div className="font-bold text-lg mb-4 text-green-700 tracking-tight">Shopping Times</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">By Hour</h3>
                  <ResponsiveContainer width="100%" height={150}>
                    <BarChart data={hourlyData}>
                      <XAxis dataKey="hour" fontSize={10} />
                      <YAxis fontSize={10} />
                      <Tooltip />
                      <Bar dataKey="orders" fill="#10b981" radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">By Day</h3>
                  <ResponsiveContainer width="100%" height={150}>
                    <BarChart data={dailyData}>
                      <XAxis dataKey="day" fontSize={10} />
                      <YAxis fontSize={10} />
                      <Tooltip />
                      <Bar dataKey="orders" fill="#f472b6" radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </Card>
          </motion.div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Shopping List Categories */}
          <motion.div 
  initial={{ opacity: 0, y: 30 }} 
  animate={{ opacity: 1, y: 0 }} 
  transition={{ delay: 0.5 }} 
>
  <Card className="p-6 flex flex-col h-full">
    <div className="font-bold text-lg mb-4 text-green-700 tracking-tight">
      Shopping List Categories
      <span className="text-sm font-normal text-gray-500 block mt-1">
        Distribution of items in your shopping list
      </span>
    </div>
    {dataWithTotal.length > 0 ? (
      <ResponsiveContainer width="100%" height={350}>
        <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 40 }}>
          <Pie
            data={dataWithTotal}
            cx="50%"
            cy="40%"
            labelLine={false}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
            nameKey="name"
            label={({ percent }) => `${(percent * 100).toFixed(0)}%`}
          >
            {dataWithTotal.map((entry, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={COLORS[index % COLORS.length]} 
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            layout="horizontal" 
            verticalAlign="bottom" 
            align="center"
            wrapperStyle={{ width: '100%', marginTop: 10 }}
            formatter={(value) => <span className="text-xs">{abbreviateName(value)}</span>}
          />
        </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-40 flex flex-col items-center justify-center text-gray-500">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  <p>Your shopping list is empty</p>
                </div>
              )}
            </Card>
          </motion.div>

          {/* Seasonal Trends */}
          <motion.div 
            initial={{ opacity: 0, y: 30 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.6 }} 
          >
            <Card className="p-6 flex flex-col h-full">
              <div className="font-bold text-lg mb-4 text-blue-700 tracking-tight">Seasonal Spending Trends</div>
              {seasonalData.length > 0 ? (
                <ResponsiveContainer width="100%" height={150}>
                  <AreaChart data={seasonalData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="month" fontSize={10} />
                    <YAxis fontSize={10} tickFormatter={(value) => `$${value}`} />
                    <Tooltip formatter={(value) => [`$${value.toFixed(2)}`, 'Amount']} />
                    <Area type="monotone" dataKey="amount" stroke="#2563eb" fill="#2563eb" fillOpacity={0.1} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-40 flex items-center justify-center text-gray-500">
                  No seasonal data available
                </div>
              )}
            </Card>
          </motion.div>
        </div>
      </div>

      {/* Agent Interaction History */}
      <motion.div 
        initial={{ opacity: 0, y: 30 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ delay: 0.7 }} 
      >
        <Card className="p-6">
          <div className="font-bold text-lg mb-4 text-blue-700 tracking-tight">Recent Agent Interactions</div>
          {interactionHistory.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 bg-gray-50">
                    <th className="py-3 px-4 font-medium">Prompt</th>
                    <th className="py-3 px-4 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {interactionHistory.map((row, i) => (
                    <tr key={i} className="border-t hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-800">{row.prompt}</td>
                      <td className="py-3 px-4 text-gray-500">{row.date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-8 flex flex-col items-center justify-center text-gray-500">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <p>No recent interactions</p>
            </div>
          )}
        </Card>
      </motion.div>
    </div>
  );
}