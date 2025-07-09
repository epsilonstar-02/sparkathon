"""
FastAPI wrapper for the Walmart Shopping Assistant Agent
Provides HTTP endpoints for the React frontend to interact with the agent.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import asyncio
import uvicorn
from collections import defaultdict

from shopping_assistant import WalmartShoppingAssistant

# Initialize FastAPI app
app = FastAPI(
    title="Walmart Shopping Assistant API", 
    description="LangGraph-powered AI shopping assistant with RAG and personalized recommendations",
    version="2.0.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the shopping assistant
shopping_assistant = WalmartShoppingAssistant()

# In-memory session storage for chat history and context
# In production, you'd want to use Redis or a database
session_storage = defaultdict(lambda: {
    "chat_history": [], 
    "recent_products": [], 
    "last_search_context": "",
    "conversation_context": None  # CRITICAL: Store conversation context
})

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    user_id: str
    user_profile: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    chat_history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    response: str
    products: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    actions_taken: List[str]
    agent_thoughts: List[str]
    intent: str
    success: bool
    chat_history: List[Dict[str, str]]
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    message: str
    agent_ready: bool

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Basic check to see if agent is initialized
        agent_ready = shopping_assistant is not None
        return HealthResponse(
            status="healthy",
            message="Walmart Shopping Assistant API is running",
            agent_ready=agent_ready
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            message=f"Health check failed: {str(e)}",
            agent_ready=False
        )

@app.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """
    Chat with the shopping assistant.
    
    Args:
        request: Chat request containing message, user_id, and optional profile
        
    Returns:
        Agent response with products, recommendations, and actions
    """
    try:
        # Determine session key for chat history storage
        session_key = f"{request.user_id}_{request.session_id}" if request.session_id else request.user_id
        
        # Get session data from storage
        session_data = session_storage[session_key]
        chat_history = request.chat_history or session_data["chat_history"]
        recent_products = session_data["recent_products"]
        conversation_context = session_data["conversation_context"]  # CRITICAL: Get persistent context
        
        # Call the agent with chat history, recent products, AND conversation context
        result = await shopping_assistant.chat(
            user_message=request.message,
            user_id=request.user_id,
            user_profile=request.user_profile,
            chat_history=chat_history,
            recent_products=recent_products,  # Pass recent products from session
            conversation_context=conversation_context  # CRITICAL: Pass persistent context
        )
        
        # Update session storage with new data
        if result.get("success", False):
            session_data["chat_history"] = result.get("chat_history", [])
            session_data["conversation_context"] = result.get("conversation_context")  # CRITICAL: Save context
            
            # Store recent products for future use
            current_products = result.get("products", [])
            if current_products:
                # Keep last 20 products to avoid memory bloat
                session_data["recent_products"] = current_products[-20:]
                session_data["last_search_context"] = request.message
            
        return ChatResponse(
            response=result.get("response", ""),
            products=result.get("products", []),
            recommendations=result.get("recommendations", []),
            actions_taken=result.get("actions_taken", []),
            agent_thoughts=result.get("agent_thoughts", []),
            intent=result.get("intent", ""),
            chat_history=result.get("chat_history", []),
            success=True
        )
        
    except Exception as e:
        # Return error response
        return ChatResponse(
            response="I apologize, but I encountered an error processing your request. Please try again.",
            products=[],
            recommendations=[],
            actions_taken=[],
            agent_thoughts=[],
            intent="error",
            chat_history=request.chat_history or [],
            success=False,
            error=str(e)
        )

@app.get("/user/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Get user profile from backend."""
    try:
        from shopping_tools import api_client
        profile = await api_client.get_user_profile(user_id)
        return {"success": True, "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{user_id}/shopping-list")
async def get_shopping_list(user_id: str):
    """Get user's shopping list."""
    try:
        from shopping_tools import api_client
        shopping_list = await api_client.get_shopping_list(user_id)
        return {"success": True, "shopping_list": shopping_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/user/{user_id}/shopping-list")
async def add_to_shopping_list(user_id: str, item: Dict[str, Any]):
    """Add item to user's shopping list."""
    try:
        from shopping_tools import api_client
        result = await api_client.add_to_shopping_list(
            user_id, 
            item.get("product_id"), 
            item.get("quantity", 1)
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/products")
async def search_products(query: str, max_results: int = 10):
    """Search products using semantic search."""
    try:
        from shopping_tools import search_products_semantic
        products = await search_products_semantic(query, max_results)
        return {"success": True, "products": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/meal-plan/generate")
async def generate_meal_plan(preferences: Dict[str, Any]):
    """Generate meal plan suggestions."""
    try:
        from shopping_tools import generate_meal_plan_suggestions
        dietary_prefs = preferences.get("dietary_restrictions", [])
        budget = preferences.get("budget", 100.0)
        days = preferences.get("days", 7)
        
        meal_plan = await generate_meal_plan_suggestions(dietary_prefs, budget, days)
        return {"success": True, "meal_plan": meal_plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/{user_id}/spending")
async def get_spending_analytics(user_id: str):
    """Get user spending analytics."""
    try:
        from shopping_tools import api_client
        analytics = await api_client.get_spending_analytics(user_id)
        return {"success": True, "analytics": analytics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/{user_id}/history")
async def clear_chat_history(user_id: str, session_id: Optional[str] = None):
    """Clear chat history for a user session."""
    try:
        session_key = f"{user_id}_{session_id}" if session_id else user_id
        if session_key in session_storage:
            del session_storage[session_key]
        return {"success": True, "message": "Chat history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/{user_id}/history")
async def get_chat_history(user_id: str, session_id: Optional[str] = None):
    """Get chat history for a user session."""
    try:
        session_key = f"{user_id}_{session_id}" if session_id else user_id
        history = session_storage.get(session_key, [])
        return {"success": True, "chat_history": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/session/{user_id}")
async def debug_session(user_id: str, session_id: Optional[str] = None):
    """Debug endpoint to check session data."""
    session_key = f"{user_id}_{session_id}" if session_id else user_id
    session_data = session_storage[session_key]
    
    return {
        "session_key": session_key,
        "chat_history_length": len(session_data["chat_history"]),
        "recent_products_count": len(session_data["recent_products"]),
        "last_search_context": session_data["last_search_context"],
        "recent_products_preview": [
            {
                "name": p.get("name", "Unknown"),
                "price": p.get("price", "N/A"),
                "id": p.get("id", "N/A")
            }
            for p in session_data["recent_products"][:3]  # Show first 3
        ] if session_data["recent_products"] else []
    }

if __name__ == "__main__":
    print("🚀 Starting Walmart Shopping Assistant API...")
    print("📍 API will be available at: http://localhost:8001")
    print("📖 API docs will be available at: http://localhost:8001/docs")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001
    )
