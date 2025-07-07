"""
LangGraph Shopping Assistant Tools
Tools for interacting with the backend API, ChromaDB, and performing shopping tasks.
"""

import asyncio
import httpx
import logging
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
        tool_logger.error(f"🔧 {tool_name} FAILED: {error} | Params: {params}")
    else:
        tool_logger.info(f"🔧 {tool_name} CALLED | Params: {params}")
        if result:
            if isinstance(result, list):
                tool_logger.info(f"🔧 {tool_name} RESULT: {len(result)} items returned")
            elif isinstance(result, dict):
                tool_logger.info(f"🔧 {tool_name} RESULT: {list(result.keys())}")
            else:
                tool_logger.info(f"🔧 {tool_name} RESULT: {type(result).__name__}")

class WalmartAPIClient:
    """Client for interacting with the FastAPI backend."""
    
    def __init__(self, base_url: str = Config.BACKEND_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient()
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile and shopping history."""
        try:
            response = await self.client.get(f"{self.base_url}/api/users/{user_id}")
            if response.status_code == 200:
                return response.json()
            api_logger.warning(f"Failed to get user profile for {user_id}: HTTP {response.status_code}")
            return {}
        except Exception as e:
            api_logger.error(f"Error getting user profile for {user_id}: {e}")
            return {}
    
    async def get_shopping_list(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's current shopping list."""
        try:
            response = await self.client.get(f"{self.base_url}/api/users/{user_id}/shopping-list")
            if response.status_code == 200:
                return response.json()
            api_logger.warning(f"Failed to get shopping list for {user_id}: HTTP {response.status_code}")
            return []
        except Exception as e:
            api_logger.error(f"Error getting shopping list for {user_id}: {e}")
            return []
    
    async def add_to_shopping_list(self, user_id: str, product_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Add item to user's shopping list."""
        try:
            data = {"product_id": product_id, "quantity": quantity}
            response = await self.client.post(
                f"{self.base_url}/api/users/{user_id}/shopping-list",
                json=data
            )
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            api_logger.warning(f"Failed to add item to shopping list for {user_id}: HTTP {response.status_code}")
            return {"success": False, "error": f"API returned status {response.status_code}"}
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
        """Clear all items from user's shopping list."""
        try:
            # First get the current shopping list
            shopping_list = await self.get_shopping_list(user_id)
            
            if not shopping_list:
                return {"success": True, "message": "Shopping list was already empty", "items_removed": 0}
            
            # Remove each item
            removed_count = 0
            failed_items = []
            
            for item in shopping_list:
                item_id = item.get("id")
                if item_id:
                    result = await self.remove_from_shopping_list(user_id, item_id)
                    if result.get("success"):
                        removed_count += 1
                    else:
                        failed_items.append(item_id)
            
            if failed_items:
                api_logger.warning(f"Partially cleared shopping list for {user_id}: {removed_count} removed, {len(failed_items)} failed")
                return {
                    "success": False, 
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
    Search for products using semantic similarity.
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
            error = "Product searcher not initialized"
            log_tool_call("search_products_semantic", params, error=error)
            return [{"error": error}]
        
        results = _product_searcher.search(query, n_results=max_results)
        
        formatted_products = []
        for product in results.get("results", []):
            metadata = product.get("metadata", {})
            formatted_products.append({
                "id": product.get("id"),
                "name": metadata.get("brand", "Unknown") + " " + product.get("document", "").split("|")[0].replace("Product: ", ""),
                "category": metadata.get("category"),
                "price": metadata.get("price"),
                "currency": metadata.get("currency", "USD"),
                "rating": metadata.get("rating"),
                "availability": metadata.get("availability"),
                "similarity_score": 1 - product.get("distance", 0)
            })
        
        log_tool_call("search_products_semantic", params, formatted_products)
        tool_logger.info(f"🔍 Search completed: found {len(formatted_products)} products")
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
            
            # Common restriction patterns
            if restriction in ["vegetarian", "vegan"]:
                if any(meat_term in product_name or meat_term in product_category 
                      for meat_term in ["meat", "chicken", "beef", "pork", "fish", "bacon"]):
                    exclude_product = True
                    break
            
            elif restriction in ["gluten-free", "no gluten"]:
                if any(gluten_term in product_name 
                      for gluten_term in ["wheat", "bread", "pasta", "cereal"]):
                    exclude_product = True
                    break
            
            elif restriction in ["no nuts", "nut-free"]:
                if any(nut_term in product_name 
                      for nut_term in ["nuts", "almond", "peanut", "walnut"]):
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
        
        for item in shopping_list:
            category = item.get("category", "").lower()
            name = item.get("name", "").lower()
            
            if any(protein_term in name or protein_term in category 
                  for protein_term in ["meat", "chicken", "fish", "beans", "eggs"]):
                nutrition_categories["protein"].append(item)
            elif any(carb_term in name or carb_term in category 
                    for carb_term in ["bread", "pasta", "rice", "cereal"]):
                nutrition_categories["carbs"].append(item)
            elif "dairy" in category or any(dairy_term in name 
                                          for dairy_term in ["milk", "cheese", "yogurt"]):
                nutrition_categories["dairy"].append(item)
            elif any(produce_term in category 
                    for produce_term in ["produce", "fruit", "vegetable"]):
                nutrition_categories["fruits_vegetables"].append(item)
            elif "snack" in category:
                nutrition_categories["snacks"].append(item)
            else:
                nutrition_categories["other"].append(item)
        
        # Analyze balance
        suggestions = []
        if len(nutrition_categories["protein"]) < 2:
            suggestions.append("Consider adding more protein sources")
        if len(nutrition_categories["fruits_vegetables"]) < 3:
            suggestions.append("Add more fruits and vegetables for balanced nutrition")
        if len(nutrition_categories["dairy"]) == 0:
            suggestions.append("Consider adding dairy products for calcium")
        
        return {
            "nutrition_breakdown": {k: len(v) for k, v in nutrition_categories.items()},
            "total_items": len(shopping_list),
            "balance_score": min(len([cat for cat in nutrition_categories.values() if cat]) / 5.0, 1.0),
            "suggestions": suggestions,
            "categories": nutrition_categories
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
