// React Hooks for API calls
// This file contains custom React hooks for API integration

import { useState, useEffect, useCallback } from 'react'
import { 
  productService, 
  userService, 
  orderService, 
  chatService, 
  analyticsService 
} from '../index.js'

// Generic API hook
export function useApi(apiFunction, dependencies = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await apiFunction()
      setData(result)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, dependencies)

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { data, loading, error, refetch: fetchData }
}

// Products hooks
export function useProducts() {
  return useApi(() => productService.getAllProducts())
}

export function useProduct(productId) {
  return useApi(() => productService.getProductById(productId), [productId])
}

// User hooks
export function useUser(userId) {
  return useApi(() => userService.getUserById(userId), [userId])
}

export function useShoppingList(userId) {
  return useApi(() => userService.getShoppingList(userId), [userId])
}

export function useUserOrders(userId) {
  return useApi(() => userService.getUserOrders(userId), [userId])
}

export function useSpendingAnalytics(userId) {
  return useApi(() => userService.getSpendingAnalytics(userId), [userId])
}

// Chat hooks
export function useChatHistory(userId) {
  return useApi(() => chatService.getChatHistory(userId), [userId])
}

// Dashboard hook
export function useDashboardData(userId) {
  return useApi(() => analyticsService.getDashboardData(userId), [userId])
}

// Shopping list management hook
export function useShoppingListManager(userId) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const addItem = async (productId, quantity = 1) => {
    try {
      setLoading(true)
      const newItem = await userService.addToShoppingList(userId, productId, quantity)
      setItems(prev => [...prev, newItem])
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  const removeItem = async (itemId) => {
    try {
      setLoading(true)
      await userService.removeFromShoppingList(userId, itemId)
      setItems(prev => prev.filter(item => item.id !== itemId))
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  const loadItems = async () => {
    try {
      setLoading(true)
      const shoppingList = await userService.getShoppingList(userId)
      setItems(shoppingList)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (userId) {
      loadItems()
    }
  }, [userId])

  return {
    items,
    loading,
    error,
    addItem,
    removeItem,
    refetch: loadItems
  }
}