// Order Service
// This file contains all order-related API calls

import { apiClient } from '../client.js'
import { API_ENDPOINTS } from '../config.js'

export const orderService = {
  // Create new order from shopping list
  // USAGE: Checkout functionality when user completes shopping
  // INTEGRATION POINT: Checkout component or shopping list "Complete Order" button
  async createOrder(userId, items) {
    try {
      const orderData = {
        user_id: userId,
        items: items.map(item => ({
          product_id: item.productId || item.product_id,
          quantity: item.quantity
        }))
      }
      return await apiClient.post(API_ENDPOINTS.ORDERS, orderData)
    } catch (error) {
      console.error('Failed to create order:', error)
      throw error
    }
  },

  // Get specific order by ID
  // USAGE: Order details view in Dashboard.jsx
  // INTEGRATION POINT: Dashboard - order history section (order detail modals)
  async getOrderById(orderId) {
    try {
      return await apiClient.get(API_ENDPOINTS.ORDER_BY_ID(orderId))
    } catch (error) {
      console.error(`Failed to fetch order ${orderId}:`, error)
      throw error
    }
  },

  // Create order from current shopping list
  // USAGE: One-click checkout from shopping list
  // INTEGRATION POINT: Shopping list component - "Checkout" button
  async checkoutShoppingList(userId, shoppingListItems) {
    try {
      const items = shoppingListItems.map(item => ({
        product_id: item.productId,
        quantity: item.quantity
      }))
      
      return await this.createOrder(userId, items)
    } catch (error) {
      console.error('Failed to checkout shopping list:', error)
      throw error
    }
  },

  // Calculate order total (client-side helper)
  // USAGE: Display estimated total before checkout
  // INTEGRATION POINT: Shopping list component - total calculation
  calculateOrderTotal(items) {
    return items.reduce((total, item) => {
      const itemTotal = (item.product?.price || item.price || 0) * item.quantity
      return total + itemTotal
    }, 0).toFixed(2)
  }
}