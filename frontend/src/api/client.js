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
    // if (config.body && typeof config.body === 'object') {
    //   config.body = JSON.stringify(config.body)
    // }
    if (config.body instanceof FormData) {
          // Do NOT stringify or set content-type
          delete config.headers['Content-Type']
    } else if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body)
      config.headers['Content-Type'] = 'application/json'
    }


    try {
      const response = await fetch(url, config)
      
      // Handle ALL errors first (non-2xx responses)
    if (!response.ok) {
      const errorData = await response.json().catch(() => null)
      throw new Error(`API Error ${response.status}: ${errorData?.message || 'Unknown error'}`)
    }

      // Handle non-JSON responses (like DELETE operations)
      const contentType = response.headers.get('content-type')|| ''
      let data

      // Handle audio responses
      if (contentType.includes('audio/mpeg')) {
          return await response.blob()
        }
      
      if (contentType && contentType.includes('application/json')) {
        data = await response.json()
      } else {
        data = await response.text()
      }

      // if (!response.ok) {
      //   if (response.status === 422) {
      //     const errorData = await response.json();
      //     throw new Error(`Validation Error: ${JSON.stringify(errorData)}`);
      //   }
      //   throw new Error(`API Error: ${response.status} - ${data.message || data}`)
      // }

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