// User Service
// This file contains all user-related API calls

import { apiClient } from '../client.js'
import { API_ENDPOINTS } from '../config.js'

export const userService = {
  // Get user with full profile, orders, and shopping list
  // USAGE: Call this in Dashboard.jsx to load user data and analytics
  // INTEGRATION POINT: Dashboard component - user profile section
  async getUserById(userId) {
    try {
      return await apiClient.get(API_ENDPOINTS.USER_BY_ID(userId))
    } catch (error) {
      console.error(`Failed to fetch user ${userId}:`, error)
      throw error
    }
  },

  // Update user profile
  // USAGE: User profile editing functionality
  // INTEGRATION POINT: User settings or profile edit components
  async updateUser(userId, userData) {
    try {
      return await apiClient.put(API_ENDPOINTS.USER_BY_ID(userId), userData)
    } catch (error) {
      console.error(`Failed to update user ${userId}:`, error)
      throw error
    }
  },

  // Get user's shopping list with product details
  // USAGE: Display shopping list in Dashboard.jsx and Map components
  // INTEGRATION POINT: Dashboard - shopping list section, Map components - route planning
  async getShoppingList(userId) {
    try {
      return await apiClient.get(API_ENDPOINTS.USER_SHOPPING_LIST(userId))
    } catch (error) {
      console.error(`Failed to fetch shopping list for user ${userId}:`, error)
      throw error
    }
  },

  // Add item to shopping list
  // USAGE: Chat.jsx when AI suggests products, Map components when user selects items
  // INTEGRATION POINT: Chat component - AI recommendations, Map components - product selection
  async addToShoppingList(userId, productId, quantity = 1) {
    try {
      const itemData = {
        product_id: productId,
        quantity: quantity
      }
      return await apiClient.post(API_ENDPOINTS.USER_SHOPPING_LIST(userId), itemData)
    } catch (error) {
      console.error(`Failed to add item to shopping list for user ${userId}:`, error)
      throw error
    }
  },

  // Remove item from shopping list
  // USAGE: Shopping list management in Dashboard.jsx
  // INTEGRATION POINT: Dashboard - shopping list section (remove buttons)
  async removeFromShoppingList(userId, itemId) {
    try {
      return await apiClient.delete(API_ENDPOINTS.SHOPPING_LIST_ITEM(userId, itemId))
    } catch (error) {
      console.error(`Failed to remove item ${itemId} from shopping list:`, error)
      throw error
    }
  },

  // Get user's order history
  // USAGE: Display order history in Dashboard.jsx
  // INTEGRATION POINT: Dashboard component - order history section
  async getUserOrders(userId) {
    try {
      return await apiClient.get(API_ENDPOINTS.USER_ORDERS(userId))
    } catch (error) {
      console.error(`Failed to fetch orders for user ${userId}:`, error)
      throw error
    }
  },

  // Get spending analytics by category
  // USAGE: Dashboard.jsx for spending charts and analytics
  // INTEGRATION POINT: Dashboard component - analytics charts (BarChart, PieChart)
  async getSpendingAnalytics(userId) {
    try {
      return await apiClient.get(API_ENDPOINTS.USER_ANALYTICS_SPENDING(userId))
    } catch (error) {
      console.error(`Failed to fetch spending analytics for user ${userId}:`, error)
      throw error
    }
  }
}