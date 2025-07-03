// API Index - Main export file
// This file exports all API services for easy importing

// Import all services
import { productService } from './services/productService.js'
import { userService } from './services/userService.js'
import { orderService } from './services/orderService.js'
import { chatService } from './services/chatService.js'
import { analyticsService } from './services/analyticsService.js'

// Import client and config
import { apiClient } from './client.js'
import { API_CONFIG, API_ENDPOINTS } from './config.js'

// Export all services
export {
  productService,
  userService,
  orderService,
  chatService,
  analyticsService,
  apiClient,
  API_CONFIG,
  API_ENDPOINTS
}

// Default export with all services
export default {
  products: productService,
  users: userService,
  orders: orderService,
  chat: chatService,
  analytics: analyticsService,
  client: apiClient,
  config: API_CONFIG,
  endpoints: API_ENDPOINTS
}