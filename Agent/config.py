"""
LangGraph Shopping Assistant Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

class Config:
    """Application configuration."""
    # LLM Configuration (Gemini)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
    
    # Backend API Configuration
    BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
    
    # ChromaDB Configuration
    CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    
    # Agent Configuration
    AGENT_NAME = os.getenv("AGENT_NAME", "Walmart Shopping Assistant")
    AGENT_DESCRIPTION = os.getenv("AGENT_DESCRIPTION", "AI-powered personalized shopping assistant")
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))
    MAX_PRODUCTS_TO_RETRIEVE = 10
    MAX_CONVERSATION_HISTORY = 20
    BUDGET_WARNING_THRESHOLD = 0.8
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Agent Personality
    AGENT_PERSONALITY = """You are a friendly and knowledgeable Walmart shopping assistant. You help customers:
- Discover products that match their needs and preferences
- Create personalized shopping lists
- Find the best deals and alternatives
- Plan meals and suggest recipes
- Manage budgets and track spending
- Learn from their preferences to improve recommendations

Always be helpful, concise, and focus on practical solutions. 
Ask clarifying questions when needed and explain your reasoning."""

# Legacy configuration for backward compatibility
BACKEND_API_URL = Config.BACKEND_BASE_URL
GEMINI_API_KEY = Config.GEMINI_API_KEY
LLM_MODEL = Config.GEMINI_MODEL
LLM_TEMPERATURE = Config.DEFAULT_TEMPERATURE
CHROMA_DB_PATH = Config.CHROMA_PERSIST_DIRECTORY
EMBEDDING_MODEL = Config.EMBEDDING_MODEL
MAX_PRODUCTS_TO_RETRIEVE = Config.MAX_PRODUCTS_TO_RETRIEVE
MAX_CONVERSATION_HISTORY = Config.MAX_CONVERSATION_HISTORY
BUDGET_WARNING_THRESHOLD = Config.BUDGET_WARNING_THRESHOLD

# User Preference Categories
USER_PREFERENCE_CATEGORIES = [
    "dietary_restrictions",  # vegan, vegetarian, gluten-free, etc.
    "health_goals",         # weight_loss, muscle_gain, heart_healthy, etc.
    "budget_range",         # weekly/monthly budget limits
    "household_size",       # number of people
    "cooking_frequency",    # daily, weekly, rarely
    "preferred_brands",     # brand preferences
    "disliked_ingredients", # ingredients to avoid
    "meal_types",          # breakfast, lunch, dinner, snacks
    "shopping_frequency",   # weekly, bi-weekly, monthly
]

# Intent Categories
INTENT_CATEGORIES = [
    "product_discovery",     # "I need protein powder"
    "meal_planning",        # "Plan my week's meals"
    "budget_optimization",  # "I need to stay under $100"
    "nutrition_analysis",   # "Is my cart healthy?"
    "list_management",      # "Add milk to my list"
    "product_comparison",   # "Compare these cereals"
    "deal_hunting",        # "Show me the best deals"
    "recipe_suggestion",   # "What can I make with chicken?"
    "general_chat",        # Casual conversation
]
