// API Client
// This file contains the base HTTP client for making API requests

import { API_CONFIG } from './config.js'

class APIClient {
  constructor(config = API_CONFIG) {
    this.baseURL = config.baseURL
    this.timeout = config.timeout
    this.defaultHeaders = config.headers
  }

  // Generic request method
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`
    
    const config = {
      method: 'GET',
      headers: { ...this.defaultHeaders },
      ...options
    }

    // Add body for POST/PUT requests
    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body)
    }

    try {
      const response = await fetch(url, config)
      
      // Handle non-JSON responses (like DELETE operations)
      const contentType = response.headers.get('content-type')
      let data
      
      if (contentType && contentType.includes('application/json')) {
        data = await response.json()
      } else {
        data = await response.text()
      }

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} - ${data.message || data}`)
      }

      return data
    } catch (error) {
      console.error('API Request failed:', error)
      throw error
    }
  }

  // HTTP method helpers
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString()
    const url = queryString ? `${endpoint}?${queryString}` : endpoint
    return this.request(url, { method: 'GET' })
  }

  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: data
    })
  }

  async put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: data
    })
  }

  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' })
  }
}

// Create and export a singleton instance
export const apiClient = new APIClient()
export default apiClient