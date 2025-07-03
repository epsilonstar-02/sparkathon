// Analytics Service
// This file contains analytics and reporting API calls

import { apiClient } from '../client.js'
import { userService } from './userService.js'
import { productService } from './productService.js'

export const analyticsService = {
  // Get comprehensive dashboard data
  // USAGE: Dashboard.jsx to load all analytics data at once
  // INTEGRATION POINT: Dashboard component - useEffect hook for data loading
  async getDashboardData(userId) {
    try {
      const [user, spendingData, orders] = await Promise.all([
        userService.getUserById(userId),
        userService.getSpendingAnalytics(userId),
        userService.getUserOrders(userId)
      ])

      return {
        user,
        spendingData,
        orders,
        totalSpent: Object.values(spendingData).reduce((sum, amount) => sum + amount, 0),
        totalOrders: orders.length,
        averageOrderValue: orders.length > 0 
          ? (orders.reduce((sum, order) => sum + order.total, 0) / orders.length).toFixed(2)
          : 0
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      throw error
    }
  },

  // Get spending trends over time
  // USAGE: Dashboard.jsx for trend charts
  // INTEGRATION POINT: Dashboard component - spending trends section
  async getSpendingTrends(userId, timeRange = '30d') {
    try {
      const orders = await userService.getUserOrders(userId)
      
      // Process orders to create spending trends
      const trends = this.processSpendingTrends(orders, timeRange)
      return trends
    } catch (error) {
      console.error('Failed to fetch spending trends:', error)
      throw error
    }
  },

  // Get top purchased products
  // USAGE: Dashboard.jsx for top purchases section
  // INTEGRATION POINT: Dashboard component - top purchases widget
  async getTopPurchases(userId, limit = 5) {
    try {
      const orders = await userService.getUserOrders(userId)
      const topPurchases = this.processTopPurchases(orders, limit)
      return topPurchases
    } catch (error) {
      console.error('Failed to fetch top purchases:', error)
      throw error
    }
  },

  // Get shopping patterns
  // USAGE: Dashboard.jsx for shopping behavior insights
  // INTEGRATION POINT: Dashboard component - shopping patterns section
  async getShoppingPatterns(userId) {
    try {
      const [orders, user] = await Promise.all([
        userService.getUserOrders(userId),
        userService.getUserById(userId)
      ])

      const patterns = this.analyzeShoppingPatterns(orders, user)
      return patterns
    } catch (error) {
      console.error('Failed to fetch shopping patterns:', error)
      throw error
    }
  },

  // Process spending trends from orders
  processSpendingTrends(orders, timeRange) {
    const now = new Date()
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
    const startDate = new Date(now.getTime() - (days * 24 * 60 * 60 * 1000))

    const trends = []
    for (let i = 0; i < days; i++) {
      const date = new Date(startDate.getTime() + (i * 24 * 60 * 60 * 1000))
      const dateStr = date.toISOString().split('T')[0]
      
      const dayOrders = orders.filter(order => 
        order.createdAt.split('T')[0] === dateStr
      )
      
      const dayTotal = dayOrders.reduce((sum, order) => sum + order.total, 0)
      
      trends.push({
        date: dateStr,
        amount: dayTotal,
        orders: dayOrders.length
      })
    }

    return trends
  },

  // Process top purchases from orders
  processTopPurchases(orders, limit) {
    const productCounts = {}
    const productTotals = {}

    orders.forEach(order => {
      if (Array.isArray(order.items)) {
        order.items.forEach(item => {
          const productId = item.productId
          const quantity = item.quantity || 1
          const price = item.price || 0

          productCounts[productId] = (productCounts[productId] || 0) + quantity
          productTotals[productId] = (productTotals[productId] || 0) + (price * quantity)
        })
      }
    })

    const topProducts = Object.entries(productCounts)
      .map(([productId, count]) => ({
        productId,
        count,
        total: productTotals[productId] || 0,
        name: `Product ${productId}` // This would be replaced with actual product names
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, limit)

    return topProducts
  },

  // Analyze shopping patterns
  analyzeShoppingPatterns(orders, user) {
    const patterns = {
      averageOrderValue: orders.length > 0 
        ? orders.reduce((sum, order) => sum + order.total, 0) / orders.length 
        : 0,
      orderFrequency: this.calculateOrderFrequency(orders),
      preferredCategories: this.getPreferredCategories(orders),
      shoppingTimes: this.analyzeShoppingTimes(orders),
      seasonalTrends: this.analyzeSeasonalTrends(orders)
    }

    return patterns
  },

  // Calculate order frequency
  calculateOrderFrequency(orders) {
    if (orders.length < 2) return 0
    
    const dates = orders.map(order => new Date(order.createdAt)).sort()
    const intervals = []
    
    for (let i = 1; i < dates.length; i++) {
      const interval = (dates[i] - dates[i-1]) / (1000 * 60 * 60 * 24) // days
      intervals.push(interval)
    }
    
    return intervals.reduce((sum, interval) => sum + interval, 0) / intervals.length
  },

  // Get preferred categories from orders
  getPreferredCategories(orders) {
    const categoryTotals = {}
    
    orders.forEach(order => {
      if (Array.isArray(order.items)) {
        order.items.forEach(item => {
          // This would need to be enhanced with actual product category data
          const category = item.category || 'Unknown'
          categoryTotals[category] = (categoryTotals[category] || 0) + (item.price * item.quantity)
        })
      }
    })
    
    return Object.entries(categoryTotals)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([category, total]) => ({ category, total }))
  },

  // Analyze shopping times
  analyzeShoppingTimes(orders) {
    const hourCounts = {}
    const dayCounts = {}
    
    orders.forEach(order => {
      const date = new Date(order.createdAt)
      const hour = date.getHours()
      const day = date.getDay() // 0 = Sunday, 1 = Monday, etc.
      
      hourCounts[hour] = (hourCounts[hour] || 0) + 1
      dayCounts[day] = (dayCounts[day] || 0) + 1
    })
    
    return { hourCounts, dayCounts }
  },

  // Analyze seasonal trends
  analyzeSeasonalTrends(orders) {
    const monthCounts = {}
    
    orders.forEach(order => {
      const month = new Date(order.createdAt).getMonth()
      monthCounts[month] = (monthCounts[month] || 0) + order.total
    })
    
    return monthCounts
  }
}