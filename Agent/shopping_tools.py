"""
LangGraph Shopping Assistant Tools
Tools for interacting with the backend API, ChromaDB, and performing shopping tasks.
"""

import asyncio
import httpx
import logging
import time
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from query_products import ProductSearcher
from config import Config

# Set up logging for tools
tool_logger = logging.getLogger("ToolUsage")
api_logger = logging.getLogger("BackendAPI")

def log_tool_call(tool_name: str, params: Dict[str, Any], result: Any = None, error: str = None):
    """Log tool calls with parameters and results."""
    if error:
        tool_logger.error(f"🚨 {tool_name} FAILED with params {params}: {error}")
    else:
        tool_logger.info(f"🔧 {tool_name} called with params: {params}")
        if isinstance(result, dict):
            if result:
                tool_logger.info(f"🔧 {tool_name} RESULT: dict with keys {list(result.keys())}")
            else:
                tool_logger.info(f"🔧 {tool_name} RESULT: empty dict")
        elif isinstance(result, list):
            tool_logger.info(f"🔧 {tool_name} RESULT: {len(result)} items")
        else:
            if result:
                tool_logger.info(f"🔧 {tool_name} RESULT: {type(result).__name__}")
            else:
                tool_logger.info(f"🔧 {tool_name} RESULT: None")

# User session locks for sequential operations
_user_locks = {}

def get_user_lock(user_id: str):
    """Get or create a lock for a specific user to ensure sequential operations."""
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]

# Circuit Breaker implementation
class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
                return False
            return True
        return False
    
    def record_success(self):
        """Record successful call."""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'

class WalmartAPIClient:
    """Client for interacting with the FastAPI backend with circuit breaker protection."""
    
    def __init__(self, base_url: str = Config.BACKEND_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        # Configure httpx client with proper timeouts and connection limits
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),  # 30s total, 10s connect
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            follow_redirects=True,
            headers={
                "User-Agent": "Walmart-Shopping-Assistant/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile and shopping history with retry logic and circuit breaker."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.circuit_breaker.is_open():
                    api_logger.warning(f"Circuit breaker is OPEN for user profile request: {user_id}")
                    return {}
                
                response = await self._make_request("GET", f"{self.base_url}/api/users/{user_id}")
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    api_logger.warning(f"User not found: {user_id}")
                    return {}
                elif response.status_code >= 500:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    api_logger.warning(f"Server error getting user profile for {user_id}: HTTP {response.status_code}")
                    return {}
                else:
                    api_logger.warning(f"Failed to get user profile for {user_id}: HTTP {response.status_code}")
                    return {}
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                api_logger.warning(f"Network error getting user profile for {user_id} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {}
            except Exception as e:
                if "Circuit breaker is OPEN" in str(e):
                    api_logger.warning(f"Circuit breaker prevented request for user {user_id}")
                    return {}
                api_logger.error(f"Error getting user profile for {user_id}: {e}")
                return {}
    
    async def get_shopping_list(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's current shopping list with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.get(f"{self.base_url}/api/users/{user_id}/shopping-list")
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    api_logger.warning(f"User not found: {user_id}")
                    return []
                elif response.status_code >= 500:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    api_logger.warning(f"Server error getting shopping list for {user_id}: HTTP {response.status_code}")
                    return []
                else:
                    api_logger.warning(f"Failed to get shopping list for {user_id}: HTTP {response.status_code}")
                    return []
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                api_logger.warning(f"Network error getting shopping list for {user_id} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return []
            except Exception as e:
                api_logger.error(f"Error getting shopping list for {user_id}: {e}")
                return []
    
    async def add_to_shopping_list(self, user_id: str, product_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Add item to user's shopping list."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use 'product_id' as required by backend API
                data = {"product_id": product_id, "quantity": quantity}
                response = await self.client.post(
                    f"{self.base_url}/api/users/{user_id}/shopping-list",
                    json=data
                )
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                elif response.status_code == 404:
                    api_logger.warning(f"User or product not found for {user_id}: {product_id}")
                    return {"success": False, "error": "User or product not found"}
                elif response.status_code >= 500:
                    api_logger.warning(f"Server error adding item to shopping list for {user_id}: HTTP {response.status_code}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return {"success": False, "error": f"Server error: {response.status_code}"}
                else:
                    api_logger.warning(f"Failed to add item to shopping list for {user_id}: HTTP {response.status_code}")
                    error_details = ""
                    try:
                        error_response = response.json()
                        error_details = f" - {error_response}"
                    except:
                        error_details = f" - {response.text}"
                    api_logger.warning(f"Response details: {error_details}")
                    return {"success": False, "error": f"API returned status {response.status_code}{error_details}"}
            except httpx.TimeoutException:
                api_logger.warning(f"Timeout adding item to shopping list for {user_id} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"success": False, "error": "Request timeout"}
            except httpx.ConnectError:
                api_logger.error(f"Connection error adding item to shopping list for {user_id} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"success": False, "error": "Connection error"}
            except Exception as e:
                api_logger.error(f"Error adding to shopping list for {user_id}: {e}")
                return {"success": False, "error": str(e)}
    
    async def remove_from_shopping_list(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """Remove a specific item from user's shopping list."""
        try:
            response = await self.client.delete(f"{self.base_url}/api/users/{user_id}/shopping-list/{item_id}")
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            api_logger.warning(f"Failed to remove item {item_id} for {user_id}: HTTP {response.status_code}")
            return {"success": False, "error": f"API returned status {response.status_code}"}
        except Exception as e:
            api_logger.error(f"Error removing item {item_id} for {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def clear_shopping_list(self, user_id: str) -> Dict[str, Any]:
        """Clear all items from user's shopping list using concurrent requests."""
        try:
            # First get the current shopping list
            shopping_list = await self.get_shopping_list(user_id)
            
            if not shopping_list:
                return {"success": True, "message": "Shopping list was already empty", "items_removed": 0}
            
            # Remove all items concurrently for better performance
            removal_tasks = []
            for item in shopping_list:
                item_id = item.get("id")
                if item_id:
                    removal_tasks.append(self.remove_from_shopping_list(user_id, item_id))
            
            if not removal_tasks:
                return {"success": True, "message": "Shopping list was already empty", "items_removed": 0}
            
            # Execute all removal requests concurrently
            results = await asyncio.gather(*removal_tasks, return_exceptions=True)
            
            # Count successful removals
            removed_count = 0
            failed_items = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_items.append(shopping_list[i].get("id", f"item_{i}"))
                    api_logger.error(f"Exception removing item {i}: {result}")
                elif isinstance(result, dict) and result.get("success"):
                    removed_count += 1
                else:
                    failed_items.append(shopping_list[i].get("id", f"item_{i}"))
            
            if failed_items:
                api_logger.warning(f"Partially cleared shopping list for {user_id}: {removed_count} removed, {len(failed_items)} failed")
                return {
                    "success": removed_count > 0,  # Partial success if some items were removed
                    "message": f"Partially cleared. {removed_count} items removed, {len(failed_items)} failed",
                    "items_removed": removed_count,
                    "failed_items": failed_items
                }
            else:
                api_logger.info(f"Successfully cleared shopping list for {user_id}: {removed_count} items removed")
                return {
                    "success": True, 
                    "message": f"Shopping list cleared successfully. {removed_count} items removed",
                    "items_removed": removed_count
                }
                
        except Exception as e:
            api_logger.error(f"Error clearing shopping list for {user_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_spending_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get user's spending analytics by category."""
        try:
            response = await self.client.get(f"{self.base_url}/api/users/{user_id}/analytics/spending")
            if response.status_code == 200:
                return response.json()
            api_logger.warning(f"Failed to get spending analytics for {user_id}: HTTP {response.status_code}")
            return {}
        except Exception as e:
            api_logger.error(f"Error getting spending analytics for {user_id}: {e}")
            return {}
    
    async def create_chat_message(self, user_id: str, content: str, is_user: bool = True) -> Dict[str, Any]:
        """Create a chat message record."""
        try:
            data = {
                "user_id": user_id,
                "content": content,
                "is_user": is_user
            }
            response = await self.client.post(f"{self.base_url}/api/chat", json=data)
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            api_logger.warning(f"Failed to create chat message for {user_id}: HTTP {response.status_code}")
            return {"success": False, "error": f"API returned status {response.status_code}"}
        except Exception as e:
            api_logger.error(f"Error creating chat message for {user_id}: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """Close the HTTP client and cleanup resources."""
        if self.client:
            await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def __del__(self):
        """Destructor to ensure client is closed."""
        if hasattr(self, 'client') and self.client:
            # Note: In production, you should ensure proper async cleanup
            # This is a safety net for cases where close() wasn't called
            import warnings
            warnings.warn("WalmartAPIClient was not properly closed. Use 'await client.close()' or async context manager.")

    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with circuit breaker protection."""
        if self.circuit_breaker.is_open():
            raise Exception("Circuit breaker is OPEN - too many recent failures")
        
        try:
            response = await getattr(self.client, method.lower())(url, **kwargs)
            self.circuit_breaker.record_success()
            return response
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise e

# Global instances
api_client = WalmartAPIClient()
# product_searcher will be injected from the assistant
_product_searcher = None

def initialize_tools(product_searcher_instance):
    """Initialize tools with the shared product searcher instance."""
    global _product_searcher
    _product_searcher = product_searcher_instance

# LangChain Tools for the agent

@tool
async def search_products_semantic(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for products using semantic similarity with intelligent filtering.
    Use this when users ask for products, ingredients, or items.
    
    Args:
        query: Search query (e.g., "healthy snacks", "pasta ingredients")
        max_results: Maximum number of products to return
    
    Returns:
        List of relevant products with details
    """
    params = {"query": query, "max_results": max_results}
    tool_logger.info(f"🔍 Starting semantic product search: '{query}' (max: {max_results})")
    
    try:
        if not _product_searcher:
            error = "Product searcher not initialized. Please run sync_products.py first."
            log_tool_call("search_products_semantic", params, error=error)
            tool_logger.error(f"🔍 Critical error: {error}")
            return [{"error": error, "suggestion": "Run sync_products.py to initialize the product database"}]
        
        # Use a more restrictive similarity threshold for better results
        results = _product_searcher.search(query, n_results=max_results * 2, min_similarity=0.1)
        
        formatted_products = []
        for product in results.get("results", []):
            metadata = product.get("metadata", {})
            
            # Calculate similarity score based on distance metric
            distance = product.get("distance", 0)
            
            # Check what distance metric was used
            try:
                if _product_searcher and hasattr(_product_searcher, 'collection'):
                    collection_config = _product_searcher.collection._client.get_collection(_product_searcher.collection.name).configuration_json
                    distance_metric = collection_config['hnsw']['space']
                else:
                    distance_metric = 'l2'  # fallback
            except:
                distance_metric = 'l2'  # fallback
            
            if distance_metric == 'cosine':
                # For cosine: distance = 1 - cosine_similarity, so similarity = 1 - distance
                similarity_score = max(0, 1 - distance)
            else:
                # For L2: use inverse relationship: similarity = 1 / (1 + distance)
                similarity_score = 1 / (1 + distance) if distance >= 0 else 0
            
            # Smart filtering based on query relevance and product categories
            category = metadata.get("category", "").lower()
            query_lower = query.lower()
            product_name_lower = product.get("document", "").lower()
            
            # Intelligent relevance assessment based on distance and context
            is_relevant = True
            relevance_score = similarity_score
            
            # Adaptive filtering based on distance thresholds
            # Better matches have lower distances, so higher thresholds = more permissive
            if distance > 1.8:  # Very poor matches across all searches
                is_relevant = False
                tool_logger.info(f"Filtering out very poor match: {product.get('document', '')} (distance: {distance:.3f})")
            elif distance > 1.5:  # Moderate filtering for average matches
                # Use product name and category context to decide
                product_context = f"{product_name_lower} {category}".lower()
                
                # Check if this could be completely irrelevant (e.g., electronics for food search)
                electronic_indicators = ['cell phone', 'mobile', 'electronic', 'phone', 'technology', 'tool', 'gadget']
                food_indicators = ['food', 'ingredient', 'meal', 'recipe', 'cook', 'eat', 'drink', 'nutrition']
                
                query_context = query_lower
                is_food_query = any(indicator in query_context for indicator in food_indicators)
                is_electronic_product = any(indicator in product_context for indicator in electronic_indicators)
                
                # If it's clearly a food query and this is clearly electronics, filter it out
                if is_food_query and is_electronic_product:
                    is_relevant = False
                    tool_logger.info(f"Filtering out irrelevant category match: {product.get('document', '')} (food query vs electronics)")
            
            # Smart relevance scoring based on category alignment
            # Boost scores for good category matches while avoiding hardcoded lists
            category_boost = 1.0
            if distance < 1.0:  # Very good semantic matches
                category_boost = 1.3  # Significant boost for excellent matches
            elif distance < 1.2:  # Good matches
                category_boost = 1.1  # Modest boost for good matches
            
            relevance_score *= category_boost
            
            # Skip irrelevant products
            if not is_relevant:
                continue
            
            # Extract product name from document
            document = product.get("document", "")
            if "|" in document:
                # Format: "Product: Name | Brand: Brand | Category: Category"
                product_name_part = document.split("|")[0].replace("Product: ", "").strip()
                brand = metadata.get("brand", "Unknown")
                full_name = f"{brand} {product_name_part}" if brand != "Unknown" else product_name_part
            else:
                full_name = f"{metadata.get('brand', 'Unknown')} {document}"
            
            formatted_products.append({
                "id": metadata.get("product_id"),  # Use PostgreSQL ID from metadata, not ChromaDB ID
                "chroma_id": product.get("id"),   # Keep ChromaDB ID for reference if needed
                "name": full_name,
                "category": metadata.get("category"),
                "price": metadata.get("price"),  # This should work now
                "currency": metadata.get("currency", "USD"),
                "rating": metadata.get("rating"),
                "availability": metadata.get("availability"),
                "similarity_score": similarity_score,
                "relevance_score": relevance_score,
                "distance": distance,
                "distance_metric": distance_metric
            })
        
        # Sort by relevance score and limit results
        formatted_products.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        formatted_products = formatted_products[:max_results]
        
        # If no good results found, provide helpful feedback
        if not formatted_products:
            # Try alternative search terms for common ingredients
            alternative_suggestions = {
                'lettuce': ['salad', 'greens', 'vegetables'],
                'mayonnaise': ['sauce', 'spread', 'condiment'],
                'bread': ['bakery', 'sandwich', 'grain'],
                'celery': ['vegetables', 'fresh produce', 'canned vegetables'],
                'fresh': ['canned', 'frozen', 'packaged']
            }
            
            suggested_terms = []
            for alt_key, alternatives in alternative_suggestions.items():
                if alt_key in query.lower():
                    suggested_terms.extend(alternatives)
            
            if suggested_terms:
                tool_logger.warning(f"🔍 No good matches for '{query}'. Database mainly contains canned/packaged items.")
                return [{
                    "error": f"No good matches found for '{query}'",
                    "suggestion": f"Try searching for: {', '.join(suggested_terms[:3])}",
                    "note": "This database mainly contains canned, jarred, and packaged food items"
                }]
        
        log_tool_call("search_products_semantic", params, formatted_products)
        tool_logger.info(f"🔍 Search completed: found {len(formatted_products)} relevant products")
        return formatted_products
        
    except Exception as e:
        error_msg = f"Search failed: {str(e)}"
        log_tool_call("search_products_semantic", params, error=error_msg)
        tool_logger.error(f"🔍 Search failed: {e}")
        return [{"error": error_msg}]

# Removed duplicate - using the more comprehensive version below

# Removed duplicate - using the more comprehensive version below

@tool
async def get_user_preferences(user_id: str) -> Dict[str, Any]:
    """
    Get user profile and preferences from backend API.
    
    Args:
        user_id: User identifier
    
    Returns:
        User profile with preferences and history
    """
    params = {"user_id": user_id}
    api_logger.info(f"📡 Fetching user profile from backend API for user: {user_id}")
    
    try:
        result = await api_client.get_user_profile(user_id)
        log_tool_call("get_user_preferences", params, result)
        
        if result:
            api_logger.info(f"📡 User profile retrieved successfully: {list(result.keys())}")
        else:
            api_logger.warning(f"📡 No user profile found for user: {user_id}")
            
        return result
        
    except Exception as e:
        error_msg = f"Failed to get user profile: {str(e)}"
        log_tool_call("get_user_preferences", params, error=error_msg)
        api_logger.error(f"📡 Backend API call failed: {e}")
        return {}

@tool
async def get_user_shopping_list(user_id: str) -> List[Dict[str, Any]]:
    """
    Get user's current shopping list from backend API.
    
    Args:
        user_id: User identifier
    
    Returns:
        List of items in shopping list
    """
    params = {"user_id": user_id}
    api_logger.info(f"🛍️ Fetching shopping list from backend API for user: {user_id}")
    
    try:
        result = await api_client.get_shopping_list(user_id)
        log_tool_call("get_user_shopping_list", params, result)
        
        api_logger.info(f"🛍️ Shopping list retrieved: {len(result)} items")
        return result
        
    except Exception as e:
        error_msg = f"Failed to get shopping list: {str(e)}"
        log_tool_call("get_user_shopping_list", params, error=error_msg)
        api_logger.error(f"🛍️ Backend API call failed: {e}")
        return []

@tool
async def add_product_to_list(user_id: str, product_id: str, quantity: int = 1) -> Dict[str, Any]:
    """
    Add a product to the user's shopping list via backend API.
    
    Args:
        user_id: User identifier
        product_id: Product identifier
        quantity: Quantity to add
    
    Returns:
        Result of the add operation
    """
    params = {"user_id": user_id, "product_id": product_id, "quantity": quantity}
    api_logger.info(f"➕ Adding product {product_id} (qty: {quantity}) to shopping list for user: {user_id}")
    
    try:
        # Get the user lock for sequential operation
        async with get_user_lock(user_id):
            result = await api_client.add_to_shopping_list(user_id, product_id, quantity)

        log_tool_call("add_product_to_list", params, result)
        
        if result.get("success"):
            api_logger.info(f"➕ Product added successfully")
        else:
            api_logger.warning(f"➕ Failed to add product: {result.get('error', 'Unknown error')}")
            
        return result
        
    except Exception as e:
        error_msg = f"Failed to add product to list: {str(e)}"
        log_tool_call("add_product_to_list", params, error=error_msg)
        api_logger.error(f"➕ Backend API call failed: {e}")
        return {"success": False, "error": error_msg}

@tool
async def remove_product_from_list(user_id: str, item_id: str) -> Dict[str, Any]:
    """
    Remove a specific item from the user's shopping list via backend API.
    
    Args:
        user_id: User identifier
        item_id: Shopping list item identifier
    
    Returns:
        Result of the remove operation
    """
    params = {"user_id": user_id, "item_id": item_id}
    api_logger.info(f"➖ Removing item {item_id} from shopping list for user: {user_id}")
    
    try:
        # Get the user lock for sequential operation
        async with get_user_lock(user_id):
            result = await api_client.remove_from_shopping_list(user_id, item_id)

        log_tool_call("remove_product_from_list", params, result)
        
        if result.get("success"):
            api_logger.info(f"➖ Item removed successfully")
        else:
            api_logger.warning(f"➖ Failed to remove item: {result.get('error', 'Unknown error')}")
            
        return result
        
    except Exception as e:
        error_msg = f"Failed to remove item from list: {str(e)}"
        log_tool_call("remove_product_from_list", params, error=error_msg)
        api_logger.error(f"➖ Backend API call failed: {e}")
        return {"success": False, "error": error_msg}

@tool
async def clear_shopping_list(user_id: str) -> Dict[str, Any]:
    """
    Clear all items from the user's shopping list via backend API.
    
    Args:
        user_id: User identifier
    
    Returns:
        Result of the clear operation
    """
    params = {"user_id": user_id}
    api_logger.info(f"🧹 Clearing shopping list for user: {user_id}")
    
    try:
        # Get the user lock for sequential operation
        async with get_user_lock(user_id):
            result = await api_client.clear_shopping_list(user_id)

        log_tool_call("clear_shopping_list", params, result)
        
        if result.get("success"):
            api_logger.info(f"🧹 Shopping list cleared successfully: {result.get('message', '')}")
        else:
            api_logger.warning(f"🧹 Failed to clear shopping list: {result.get('error', 'Unknown error')}")
            
        return result
        
    except Exception as e:
        error_msg = f"Failed to clear shopping list: {str(e)}"
        log_tool_call("clear_shopping_list", params, error=error_msg)
        api_logger.error(f"🧹 Backend API call failed: {e}")
        return {"success": False, "error": error_msg}

@tool
async def get_spending_breakdown(user_id: str) -> Dict[str, Any]:
    """
    Get user's spending analytics by category from backend API.
    
    Args:
        user_id: User identifier
    
    Returns:
        Spending breakdown by category
    """
    params = {"user_id": user_id}
    api_logger.info(f"💰 Fetching spending breakdown from backend API for user: {user_id}")
    
    try:
        # For now, return mock data since we don't have this endpoint implemented
        result = {
            "total_spent": 0.0,
            "categories": {},
            "weekly_average": 0.0
        }
        log_tool_call("get_spending_breakdown", params, result)
        api_logger.info(f"💰 Spending breakdown retrieved")
        return result
        
    except Exception as e:
        error_msg = f"Failed to get spending breakdown: {str(e)}"
        log_tool_call("get_spending_breakdown", params, error=error_msg)
        api_logger.error(f"💰 Backend API call failed: {e}")
        return {"total_spent": 0.0, "categories": {}, "weekly_average": 0.0}

@tool
async def filter_products_by_dietary_restrictions(products: List[Dict[str, Any]], 
                                          restrictions: List[str]) -> List[Dict[str, Any]]:
    """
    Filter products based on dietary restrictions.
    
    Args:
        products: List of products to filter
        restrictions: List of dietary restrictions (e.g., ["vegetarian", "gluten-free"])
    
    Returns:
        Filtered list of products
    """
    if not restrictions:
        return products
    
    filtered_products = []
    for product in products:
        product_name = product.get("name", "").lower()
        product_category = product.get("category", "").lower()
        
        # Simple filtering logic - can be enhanced with more sophisticated matching
        exclude_product = False
        for restriction in restrictions:
            restriction = restriction.lower()
            
            # Smart dietary restriction filtering using flexible pattern matching
            product_text = f"{product_name} {product_category}".lower()
            
            # Vegetarian/Vegan restrictions - look for meat-related terms
            if any(term in restriction for term in ["vegetarian", "vegan"]):
                meat_indicators = ["meat", "chicken", "beef", "pork", "fish", "bacon", "turkey", "lamb", "sausage", "ham"]
                if any(meat_term in product_text for meat_term in meat_indicators):
                    exclude_product = True
                    break
            
            # Gluten-free restrictions - look for gluten-containing terms
            elif any(term in restriction for term in ["gluten-free", "no gluten", "gluten free"]):
                gluten_indicators = ["wheat", "bread", "pasta", "cereal", "flour", "barley", "rye", "oats"]
                if any(gluten_term in product_text for gluten_term in gluten_indicators):
                    exclude_product = True
                    break
            
            # Nut-free restrictions - look for nut-related terms
            elif any(term in restriction for term in ["no nuts", "nut-free", "nut free", "no nut"]):
                nut_indicators = ["nuts", "almond", "peanut", "walnut", "cashew", "pistachio", "hazelnut", "pecan"]
                if any(nut_term in product_text for nut_term in nut_indicators):
                    exclude_product = True
                    break
            
            # Dairy-free restrictions - look for dairy-related terms
            elif any(term in restriction for term in ["dairy-free", "no dairy", "dairy free", "lactose-free"]):
                dairy_indicators = ["milk", "cheese", "butter", "cream", "yogurt", "dairy", "lactose"]
                if any(dairy_term in product_text for dairy_term in dairy_indicators):
                    exclude_product = True
                    break
            
            # Sugar-free restrictions - look for sugar-related terms
            elif any(term in restriction for term in ["sugar-free", "no sugar", "sugar free", "low sugar"]):
                sugar_indicators = ["sugar", "sweetened", "syrup", "honey", "candy", "chocolate"]
                if any(sugar_term in product_text for sugar_term in sugar_indicators):
                    exclude_product = True
                    break
            
            # Low-sodium restrictions - look for high-sodium terms
            elif any(term in restriction for term in ["low sodium", "no salt", "salt-free"]):
                sodium_indicators = ["salted", "salt", "sodium", "salty", "pickle", "cured"]
                if any(sodium_term in product_text for sodium_term in sodium_indicators):
                    exclude_product = True
                    break
        
        if not exclude_product:
            filtered_products.append(product)
    
    return filtered_products

@tool
async def filter_products_by_budget(products: List[Dict[str, Any]], 
                             max_budget: float) -> List[Dict[str, Any]]:
    """
    Filter products to fit within budget.
    
    Args:
        products: List of products to filter
        max_budget: Maximum budget per item
    
    Returns:
        Products within budget, sorted by price
    """
    affordable_products = []
    for product in products:
        price = product.get("price")
        if price is not None and price <= max_budget:
            affordable_products.append(product)
    
    # Sort by price (ascending)
    affordable_products.sort(key=lambda x: x.get("price", 0))
    return affordable_products

@tool
async def generate_meal_plan_suggestions(dietary_preferences: List[str], 
                                       budget: float = 100.0,
                                       days: int = 7) -> Dict[str, Any]:
    """
    Generate meal plan suggestions with shopping list.
    
    Args:
        dietary_preferences: List of dietary preferences/restrictions
        budget: Weekly budget for meals
        days: Number of days to plan for
    
    Returns:
        Meal plan with suggested products
    """
    try:
        # Search for meal-related products
        meal_queries = [
            "breakfast ingredients cereal oats",
            "lunch ingredients bread sandwich",
            "dinner ingredients pasta rice chicken",
            "healthy snacks fruits vegetables",
            "cooking essentials spices oil"
        ]
        
        meal_suggestions = {}
        total_cost = 0.0
        
        for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
            query = next((q for q in meal_queries if meal_type in q), meal_queries[0])
            products = await search_products_semantic.ainvoke({
                "query": query, 
                "max_results": 3
            })
            
            # Filter by dietary preferences
            if dietary_preferences:
                products = await filter_products_by_dietary_restrictions.ainvoke({
                    "products": products, 
                    "restrictions": dietary_preferences
                })
            
            # Filter by budget (per item should be reasonable)
            max_item_budget = budget / (days * 3)  # Rough estimate per meal component
            products = await filter_products_by_budget.ainvoke({
                "products": products, 
                "max_budget": max_item_budget
            })
            
            meal_suggestions[meal_type] = products[:2]  # Top 2 suggestions per meal
            
            # Calculate estimated cost
            for product in meal_suggestions[meal_type]:
                if product.get("price"):
                    total_cost += product["price"]
        
        return {
            "meal_plan": meal_suggestions,
            "estimated_cost": total_cost,
            "days_planned": days,
            "budget_status": "within_budget" if total_cost <= budget else "over_budget",
            "budget_utilization": min(total_cost / budget, 1.0) if budget > 0 else 0
        }
        
    except Exception as e:
        return {"error": f"Failed to generate meal plan: {str(e)}"}

@tool
async def analyze_nutrition_balance(shopping_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze nutritional balance of shopping list.
    
    Args:
        shopping_list: List of products in shopping list
    
    Returns:
        Nutritional analysis and suggestions
    """
    try:
        # Categorize products by nutritional value
        nutrition_categories = {
            "protein": [],
            "carbs": [],
            "dairy": [],
            "fruits_vegetables": [],
            "snacks": [],
            "other": []
        }
        
        # Enhanced nutrition categorization with flexible pattern matching
        for item in shopping_list:
            category = item.get("category", "").lower()
            name = item.get("name", "").lower()
            item_text = f"{name} {category}"
            
            # Protein sources - comprehensive detection
            protein_indicators = ["meat", "chicken", "fish", "beans", "eggs", "protein", "beef", "pork", "turkey", 
                                "tofu", "quinoa", "lentils", "nuts", "seed", "salmon", "tuna"]
            if any(protein_term in item_text for protein_term in protein_indicators):
                nutrition_categories["protein"].append(item)
            
            # Carbohydrates - comprehensive detection
            elif any(carb_term in item_text for carb_term in ["bread", "pasta", "rice", "cereal", "grain", 
                                                             "oats", "wheat", "corn", "potato", "sweet potato"]):
                nutrition_categories["carbs"].append(item)
            
            # Dairy products - comprehensive detection
            elif any(dairy_term in item_text for dairy_term in ["dairy", "milk", "cheese", "yogurt", 
                                                               "cream", "butter", "ice cream"]):
                nutrition_categories["dairy"].append(item)
            
            # Fruits and vegetables - comprehensive detection
            elif any(produce_term in item_text for produce_term in ["produce", "fruit", "vegetable", "fresh", 
                                                                   "apple", "banana", "orange", "berry", "lettuce", 
                                                                   "spinach", "carrot", "tomato", "broccoli"]):
                nutrition_categories["fruits_vegetables"].append(item)
            
            # Snacks and processed foods
            elif any(snack_term in item_text for snack_term in ["snack", "chip", "cookie", "candy", "soda", 
                                                               "processed", "packaged"]):
                nutrition_categories["snacks"].append(item)
            
            # Everything else
            else:
                nutrition_categories["other"].append(item)
        
        # Smart nutrition analysis with adaptive suggestions
        suggestions = []
        total_items = len(shopping_list)
        
        # Dynamic thresholds based on shopping list size
        if total_items > 0:
            protein_ratio = len(nutrition_categories["protein"]) / total_items
            produce_ratio = len(nutrition_categories["fruits_vegetables"]) / total_items
            dairy_ratio = len(nutrition_categories["dairy"]) / total_items
            snack_ratio = len(nutrition_categories["snacks"]) / total_items
            
            # Adaptive suggestions based on ratios, not hardcoded counts
            if protein_ratio < 0.15:  # Less than 15% protein
                suggestions.append("Consider adding more protein sources for balanced nutrition")
            if produce_ratio < 0.25:  # Less than 25% fruits/vegetables
                suggestions.append("Add more fruits and vegetables for essential vitamins and fiber")
            if dairy_ratio == 0 and total_items > 5:  # No dairy in larger lists
                suggestions.append("Consider adding dairy products for calcium and vitamin D")
            if snack_ratio > 0.4:  # More than 40% snacks
                suggestions.append("Try to balance snacks with more whole food options")
            
            # Positive reinforcement for good choices
            if produce_ratio >= 0.4:
                suggestions.append("Great job including plenty of fruits and vegetables!")
            if protein_ratio >= 0.2:
                suggestions.append("Excellent protein variety in your list!")
        
        # Calculate more sophisticated balance score
        category_diversity = len([cat for cat in nutrition_categories.values() if cat])
        balance_score = min(category_diversity / 5.0, 1.0)  # 5 main categories
        
        # Adjust score based on ratios
        if total_items > 0:
            # Penalize extreme imbalances
            if snack_ratio > 0.5:
                balance_score *= 0.8
            if produce_ratio < 0.1:
                balance_score *= 0.9
            # Reward good balance
            if 0.15 <= protein_ratio <= 0.3 and produce_ratio >= 0.25:
                balance_score = min(balance_score * 1.1, 1.0)
        
        return {
            "nutrition_breakdown": {k: len(v) for k, v in nutrition_categories.items()},
            "total_items": total_items,
            "balance_score": balance_score,
            "suggestions": suggestions,
            "categories": nutrition_categories,
            "nutrition_ratios": {
                "protein_ratio": protein_ratio if total_items > 0 else 0,
                "produce_ratio": produce_ratio if total_items > 0 else 0,
                "dairy_ratio": dairy_ratio if total_items > 0 else 0,
                "snack_ratio": snack_ratio if total_items > 0 else 0
            }
        }
        
    except Exception as e:
        return {"error": f"Failed to analyze nutrition: {str(e)}"}

@tool
async def save_chat_interaction(user_id: str, user_message: str, 
                               assistant_response: str) -> Dict[str, Any]:
    """
    Save chat interaction to backend for history tracking.
    
    Args:
        user_id: User identifier
        user_message: User's message
        assistant_response: Assistant's response
    
    Returns:
        Result of save operation
    """
    try:
        # Save user message
        user_result = await api_client.create_chat_message(user_id, user_message, is_user=True)
        
        # Save assistant response
        assistant_result = await api_client.create_chat_message(user_id, assistant_response, is_user=False)
        
        return {
            "success": user_result.get("success", False) and assistant_result.get("success", False),
            "user_message_saved": user_result.get("success", False),
            "assistant_response_saved": assistant_result.get("success", False)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@tool
async def analyze_nutrition_profile(shopping_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze the nutritional profile of a shopping list.
    
    Args:
        shopping_list: List of products to analyze
    
    Returns:
        Nutritional analysis and recommendations
    """
    return await analyze_nutrition_balance(shopping_list)

@tool
async def find_product_alternatives(product_name: str, 
                                  dietary_restrictions: List[str] = None) -> List[Dict[str, Any]]:
    """
    Find alternative products for comparison.
    
    Args:
        product_name: Name of the product to find alternatives for
        dietary_restrictions: List of dietary restrictions to consider
    
    Returns:
        List of alternative products
    """
    try:
        # Search for similar products
        search_query = f"alternative to {product_name} similar product"
        alternatives = await search_products_semantic.ainvoke({
            "query": search_query, 
            "max_results": 5
        })
        
        # Filter by dietary restrictions if provided
        if dietary_restrictions:
            alternatives = await filter_products_by_dietary_restrictions.ainvoke({
                "products": alternatives, 
                "restrictions": dietary_restrictions
            })
        
        # Remove the original product from alternatives (rough matching)
        filtered_alternatives = []
        for alt in alternatives:
            alt_name = alt.get("name", "").lower()
            if product_name.lower() not in alt_name:
                filtered_alternatives.append(alt)
        
        return filtered_alternatives[:3]  # Return top 3 alternatives
        
    except Exception as e:
        return [{"error": f"Failed to find alternatives: {str(e)}"}]

@tool
async def optimize_shopping_list_for_budget(shopping_list: List[Dict[str, Any]], 
                                    max_budget: float) -> Dict[str, Any]:
    """
    Optimize shopping list to fit within budget.
    
    Args:
        shopping_list: Current shopping list
        max_budget: Maximum budget constraint
    
    Returns:
        Optimized shopping list and savings information
    """
    try:
        # Calculate current total
        current_total = sum(item.get("price", 0) * item.get("quantity", 1) 
                          for item in shopping_list if item.get("price"))
        
        if current_total <= max_budget:
            return {
                "optimized_list": shopping_list,
                "current_total": current_total,
                "budget": max_budget,
                "savings": 0,
                "optimization_needed": False
            }
        
        # Sort by price per unit (ascending) to prioritize cheaper items
        sorted_items = sorted(shopping_list, key=lambda x: x.get("price", 0))
        
        optimized_list = []
        running_total = 0
        
        for item in sorted_items:
            item_cost = item.get("price", 0) * item.get("quantity", 1)
            if running_total + item_cost <= max_budget:
                optimized_list.append(item)
                running_total += item_cost
            elif running_total + (item.get("price", 0)) <= max_budget:
                # Reduce quantity to fit budget
                affordable_qty = int((max_budget - running_total) // item.get("price", 1))
                if affordable_qty > 0:
                    modified_item = item.copy()
                    modified_item["quantity"] = affordable_qty
                    optimized_list.append(modified_item)
                    running_total += affordable_qty * item.get("price", 0)
                break
        
        savings = current_total - running_total
        
        return {
            "optimized_list": optimized_list,
            "current_total": running_total,
            "original_total": current_total,
            "budget": max_budget,
            "savings": savings,
            "optimization_needed": True,
            "items_removed": len(shopping_list) - len(optimized_list)
        }
        
    except Exception as e:
        return {"error": f"Failed to optimize shopping list: {str(e)}"}

# Tool list for LangGraph
SHOPPING_ASSISTANT_TOOLS = [
    search_products_semantic,
    get_user_shopping_list,
    add_product_to_list,
    get_user_preferences,
    get_spending_breakdown,
    filter_products_by_dietary_restrictions,
    filter_products_by_budget,
    generate_meal_plan_suggestions,
    analyze_nutrition_balance,
    analyze_nutrition_profile,
    find_product_alternatives,
    optimize_shopping_list_for_budget,
    save_chat_interaction,
    remove_product_from_list,
    clear_shopping_list
]
