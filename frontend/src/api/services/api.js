// utils/api.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const fetchProducts = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/products`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch products:', error);
    return [];
  }
};

export const fetchShoppingList = async (userId = 'user1') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/users/${userId}/shopping-list`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch shopping list:', error);
    return [];
  }
};

export const addToCartAPI = async (userId, productId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/users/${userId}/shopping-list`, {
      productId,
      quantity: 1
    });
    return response.data;
  } catch (error) {
    console.error('Failed to add to cart:', error);
    return null;
  }
};