# Frontend API Integration Guide

This directory contains all the API integration code for connecting your frontend to the FastAPI backend. **No existing frontend files have been modified.**

## 📁 File Structure

```
src/sapi/
├── config.js              # API configuration and endpoints
├── client.js               # HTTP client for API requests
├── services/
│   ├── productService.js   # Product-related API calls
│   ├── userService.js      # User and shopping list API calls
│   ├── orderService.js     # Order management API calls
│   ├── chatService.js      # Chat and messaging API calls
│   └── analyticsService.js # Analytics and dashboard data
├── hooks/
│   └── useApi.js          # React hooks for API integration
├── index.js               # Main export file
└── README.md              # This file
```

## 🔌 Integration Points

### 1. **Chat.jsx** - AI Chat Interface

**Current Location**: `frontend/src/pages/Chat.jsx`

**Integration Points**:
```javascript
// REPLACE the current handleSend function with:
import { chatService } from '../api'

const handleSend = async (message) => {
  if (!message.trim()) return
  
  try {
    const userId = 'david123' // Replace with actual user ID
    const response = await chatService.sendChatMessage(userId, message)
    
    // Update chat state with both user and AI messages
    setChat(prev => [...prev, response.userMessage, response.aiMessage])
    setInput('')
  } catch (error) {
    console.error('Failed to send message:', error)
  }
}

// LOAD chat history on component mount:
useEffect(() => {
  const loadChatHistory = async () => {
    try {
      const userId = 'david123' // Replace with actual user ID
      const history = await chatService.getChatHistory(userId)
      setChat(history)
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }
  
  loadChatHistory()
}, [])
```

### 2. **Dashboard.jsx** - Analytics Dashboard

**Current Location**: `frontend/src/pages/Dashboard.jsx`

**Integration Points**:
```javascript
// REPLACE static data with API calls:
import { useDashboardData, useSpendingAnalytics } from '../api/hooks/useApi'

function Dashboard() {
  const userId = 'david123' // Replace with actual user ID
  const { data: dashboardData, loading, error } = useDashboardData(userId)
  const { data: spendingData } = useSpendingAnalytics(userId)
  
  // REPLACE static spendingData with:
  const chartData = spendingData ? 
    Object.entries(spendingData).map(([category, amount]) => ({
      category,
      amount
    })) : []
  
  // REPLACE static topPurchases with:
  const topPurchases = dashboardData?.orders?.slice(0, 5).map(order => ({
    item: order.items[0]?.name || 'Unknown Item',
    price: `$${order.total.toFixed(2)}`
  })) || []
  
  if (loading) return <div>Loading dashboard...</div>
  if (error) return <div>Error loading dashboard: {error.message}</div>
  
  // Rest of component remains the same
}
```

### 3. **Map.jsx** - Store Navigation

**Current Location**: `frontend/src/pages/Map.jsx`

**Integration Points**:
```javascript
// ADD shopping list integration:
import { useShoppingList, productService } from '../api'

function Map() {
  const userId = 'david123' // Replace with actual user ID
  const { data: shoppingList, loading } = useShoppingList(userId)
  
  // REPLACE static items with shopping list data:
  const items = shoppingList?.map((item, index) => ({
    item: item.product.name,
    aisle: item.product.aisle,
    quantity: item.quantity
  })) || []
  
  // ADD function to add items to shopping list:
  const addToShoppingList = async (productId) => {
    try {
      await userService.addToShoppingList(userId, productId, 1)
      // Refresh shopping list
    } catch (error) {
      console.error('Failed to add item:', error)
    }
  }
  
  // Rest of component logic remains the same
}
```

### 4. **Map3D.jsx** - 3D Store Map

**Current Location**: `frontend/src/pages/Map3D.jsx`

**Integration Points**:
```javascript
// ADD product search and shopping list integration:
import { productService, useShoppingList } from '../api'

function Map3D() {
  const userId = 'david123' // Replace with actual user ID
  const { data: shoppingList } = useShoppingList(userId)
  const [availableProducts, setAvailableProducts] = useState([])
  
  // LOAD products on component mount:
  useEffect(() => {
    const loadProducts = async () => {
      try {
        const products = await productService.getAllProducts()
        setAvailableProducts(products)
      } catch (error) {
        console.error('Failed to load products:', error)
      }
    }
    
    loadProducts()
  }, [])
  
  // ENHANCE product search with real data:
  const selectedProducts = useMemo(() => {
    return availableProducts.filter(product => 
      chips.some(chip => 
        product.name.toLowerCase().includes(chip.toLowerCase())
      )
    )
  }, [chips, availableProducts])
  
  // Rest of component logic remains the same
}
```

## 🚀 Quick Start Integration

### Step 1: Import API Services
```javascript
// Add to any component that needs API access:
import { productService, userService, chatService } from '../api'

// Or use hooks for easier state management:
import { useProducts, useUser, useChatHistory } from '../api/hooks/useApi'
```

### Step 2: Replace Static Data
```javascript
// Instead of static data:
const staticData = [...]

// Use API calls:
const { data, loading, error } = useProducts()
```

### Step 3: Add Error Handling
```javascript
if (loading) return <div>Loading...</div>
if (error) return <div>Error: {error.message}</div>
```

## 🔧 Configuration

### Backend URL
Update the API base URL in `config.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000' // Change for production
```

### Demo User ID
Replace `'david123'` with actual user ID from your authentication system:
```javascript
const userId = 'david123' // Replace with actual user ID
```

## 📊 Available API Methods

### Products
- `productService.getAllProducts()`
- `productService.getProductById(id)`
- `productService.getProductsByCategory(category)`
- `productService.getProductsByAisle(aisle)`

### Users & Shopping Lists
- `userService.getUserById(userId)`
- `userService.getShoppingList(userId)`
- `userService.addToShoppingList(userId, productId, quantity)`
- `userService.removeFromShoppingList(userId, itemId)`
- `userService.getSpendingAnalytics(userId)`

### Orders
- `orderService.createOrder(userId, items)`
- `orderService.checkoutShoppingList(userId, shoppingListItems)`

### Chat
- `chatService.getChatHistory(userId)`
- `chatService.sendChatMessage(userId, message)`

### Analytics
- `analyticsService.getDashboardData(userId)`
- `analyticsService.getSpendingTrends(userId)`
- `analyticsService.getTopPurchases(userId)`

## 🎯 Next Steps

1. **Start with Chat.jsx**: Replace the handleSend function with API integration
2. **Update Dashboard.jsx**: Replace static data with API calls using hooks
3. **Enhance Map components**: Add real product data and shopping list integration
4. **Add error handling**: Implement proper loading states and error messages
5. **Replace demo user ID**: Integrate with your authentication system

All API services are ready to use and include comprehensive error handling and loading states!