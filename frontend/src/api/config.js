// API Configuration
// This file contains the base configuration for API calls

const API_BASE_URL = 'http://localhost:8000'

//https://backend-sparkthon-1.onrender.com
// API endpoints configuration
export const API_ENDPOINTS = {
  // Product endpoints
  PRODUCTS: '/api/products',
  PRODUCT_BY_ID: (id) => `/api/products/${id}`,
  
  // User endpoints
  USER_BY_ID: (userId) => `/api/users/${userId}`,
  USER_SHOPPING_LIST: (userId) => `/api/users/${userId}/shopping-list`,
  USER_ORDERS: (userId) => `/api/users/${userId}/orders`,
  USER_ANALYTICS_SPENDING: (userId) => `/api/users/${userId}/analytics/spending`,
  
  // Shopping list endpoints
  SHOPPING_LIST_ITEM: (userId, itemId) => `/api/users/${userId}/shopping-list/${itemId}`,
  SHOPPING_LIST: (userId) => `/api/users/${userId}/shopping-list`,
  // Add other endpoints as needed

  // Order endpoints
  ORDERS: '/api/orders',
  ORDER_BY_ID: (id) => `/api/orders/${id}`,
  
  // Chat endpoints
  CHAT: '/api/chat',
  CHAT_HISTORY: '/api/chat/history',
  
  // Talk endpoint for speech-to-speech interaction
  TALK: '/api/talk',

  // Health check
  HEALTH: '/health'
}

// Default headers for API requests
export const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

// API configuration object
export const API_CONFIG = {
  baseURL: API_BASE_URL,
  timeout: 10000, // 10 seconds
  headers: DEFAULT_HEADERS
}

export default API_CONFIG