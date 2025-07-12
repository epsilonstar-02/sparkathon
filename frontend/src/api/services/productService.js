// Product Service
// This file contains all product-related API calls

import { apiClient } from '../client.js'
import { API_ENDPOINTS } from '../config.js'

export const productService = {
  // Get all products
  // USAGE: Call this in Dashboard.jsx to display product inventory
  // INTEGRATION POINT: Dashboard component - product list section
  async getAllProducts() {
    try {
      return await apiClient.get(API_ENDPOINTS.PRODUCTS)
    } catch (error) {
      console.error('Failed to fetch products:', error)
      throw error
    }
  },

  // Get single product by ID
  // USAGE: Call this when user clicks on a specific product for details
  // INTEGRATION POINT: Product detail modals or pages
  async getProductById(productId) {
    try {
      return await apiClient.get(API_ENDPOINTS.PRODUCT_BY_ID(productId))
    } catch (error) {
      console.error(`Failed to fetch product ${productId}:`, error)
      throw error
    }
  },

  // Create new product (Admin functionality)
  // USAGE: Admin interface for adding new products
  // INTEGRATION POINT: Admin dashboard or product management interface
  async createProduct(productData) {
    try {
      return await apiClient.post(API_ENDPOINTS.PRODUCTS, productData)
    } catch (error) {
      console.error('Failed to create product:', error)
      throw error
    }
  },

  // Update product (Admin functionality)
  // USAGE: Admin interface for editing existing products
  // INTEGRATION POINT: Admin dashboard or product management interface
  async updateProduct(productId, productData) {
    try {
      return await apiClient.put(API_ENDPOINTS.PRODUCT_BY_ID(productId), productData)
    } catch (error) {
      console.error(`Failed to update product ${productId}:`, error)
      throw error
    }
  },

  // Delete product (Admin functionality)
  // USAGE: Admin interface for removing products
  // INTEGRATION POINT: Admin dashboard or product management interface
  async deleteProduct(productId) {
    try {
      return await apiClient.delete(API_ENDPOINTS.PRODUCT_BY_ID(productId))
    } catch (error) {
      console.error(`Failed to delete product ${productId}:`, error)
      throw error
    }
  },

  // Search products by category
  // USAGE: Filter products in Map.jsx and Map3D.jsx by aisle/category
  // INTEGRATION POINT: Map components - product filtering
  async getProductsByCategory(category) {
    try {
      const products = await this.getAllProducts()
      return products.filter(product => 
        product.category.toLowerCase() === category.toLowerCase()
      )
    } catch (error) {
      console.error(`Failed to fetch products by category ${category}:`, error)
      throw error
    }
  },

  // Get products by aisle (for map functionality)
  // USAGE: Map.jsx and Map3D.jsx to show products in specific aisles
  // INTEGRATION POINT: Map components - aisle-based product display
  async getProductsByAisle(aisle) {
    try {
      const products = await this.getAllProducts()
      return products.filter(product => 
        product.aisle.toLowerCase() === aisle.toLowerCase()
      )
    } catch (error) {
      console.error(`Failed to fetch products by aisle ${aisle}:`, error)
      throw error
    }
  },

  // Search products by brand
  // USAGE: Filter products by brand in search functionality
  // INTEGRATION POINT: Search components - brand filtering
  async getProductsByBrand(brand) {
    try {
      const products = await this.getAllProducts()
      return products.filter(product => 
        product.brand && product.brand.toLowerCase().includes(brand.toLowerCase())
      )
    } catch (error) {
      console.error(`Failed to fetch products by brand ${brand}:`, error)
      throw error
    }
  },

  // Get products by availability status
  // USAGE: Filter products by stock status
  // INTEGRATION POINT: Inventory management or product display
  async getProductsByAvailability(availability) {
    try {
      const products = await this.getAllProducts()
      return products.filter(product => 
        product.availability === availability
      )
    } catch (error) {
      console.error(`Failed to fetch products by availability ${availability}:`, error)
      throw error
    }
  },

  // Search products by name or description
  // USAGE: General product search functionality
  // INTEGRATION POINT: Search bar in any component
  async searchProducts(searchTerm) {
    try {
      const products = await this.getAllProducts()
      const term = searchTerm.toLowerCase()
      return products.filter(product => 
        product.name.toLowerCase().includes(term) ||
        (product.shortDescription && product.shortDescription.toLowerCase().includes(term)) ||
        (product.brand && product.brand.toLowerCase().includes(term))
      )
    } catch (error) {
      console.error(`Failed to search products with term ${searchTerm}:`, error)
      throw error
    }
  },

  // Get products with ratings above threshold
  // USAGE: Filter high-rated products
  // INTEGRATION POINT: Product recommendations or quality filters
  async getHighRatedProducts(minRating = 4.0) {
    try {
      const products = await this.getAllProducts()
      return products.filter(product => 
        product.averageRating && product.averageRating >= minRating
      )
    } catch (error) {
      console.error(`Failed to fetch high-rated products:`, error)
      throw error
    }
  },

  // Get products within price range
  // USAGE: Price-based filtering
  // INTEGRATION POINT: Price filter components
  async getProductsByPriceRange(minPrice, maxPrice) {
    try {
      const products = await this.getAllProducts()
      return products.filter(product => 
        product.price >= minPrice && product.price <= maxPrice
      )
    } catch (error) {
      console.error(`Failed to fetch products by price range:`, error)
      throw error
    }
  }
}