"""
LangGraph Shopping Assistant - Core Agent Implementation
A sophisticated AI shopping assistant that uses RAG and user preferences 
to provide personalized Walmart shopping experiences.
"""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


import logging
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
import json
import asyncio

# Set up comprehensive logging for the shopping assistant
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('shopping_assistant.log', encoding='utf-8')
    ]
)

# Create specific loggers for different components
logger = logging.getLogger("ShoppingAssistant")
tool_logger = logging.getLogger("ToolUsage")
api_logger = logging.getLogger("BackendAPI")

# Set up logging for LLM API calls (existing)
llm_logger = logging.getLogger("llm_api_calls")
llm_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
if not llm_logger.hasHandlers():
    llm_logger.addHandler(handler)
from pydantic import BaseModel, Field

# Import our existing components
from query_products import ProductSearcher
from config import Config

# Import all the shopping tools
from shopping_tools import (
    search_products_semantic,
    get_user_shopping_list,
    add_product_to_list,
    remove_product_from_list,
    clear_shopping_list,
    get_user_preferences,
    get_spending_breakdown,
    filter_products_by_dietary_restrictions,
    filter_products_by_budget,
    generate_meal_plan_suggestions,
    analyze_nutrition_profile,
    find_product_alternatives,
    optimize_shopping_list_for_budget,
    api_client
)
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# Helper function to log tool usage
def log_tool_usage(tool_name: str, params: Dict[str, Any], result: Any = None, error: str = None):
    """Log tool usage with parameters and results."""
    if error:
        tool_logger.error(f"Tool '{tool_name}' failed with params {params}: {error}")
    else:
        tool_logger.info(f"Tool '{tool_name}' called with params: {params}")
        if result:
            # Log a summary of the result, not the full data to avoid log spam
            if isinstance(result, list):
                tool_logger.info(f"Tool '{tool_name}' returned {len(result)} items")
            elif isinstance(result, dict):
                tool_logger.info(f"Tool '{tool_name}' returned: {list(result.keys())}")
            else:
                tool_logger.info(f"Tool '{tool_name}' returned: {type(result).__name__}")

# State schema for the agent
class ConversationState:
    """Manages conversation context for better shopping assistance continuity."""

    def __init__(self):
        self.last_products = []
        self.last_search_intent = ""
        self.last_recommendations = []
        self.last_action_context = {}
        self.context_score = 0.0

    def update_products(self, products, intent):
        """Update product context with recent search results."""
        self.last_products = products[-10:] if products else []  # Keep last 10
        self.last_search_intent = intent
        self.context_score = 1.0  # Fresh context

    def update_recommendations(self, recommendations):
        """Update recommendation context."""
        self.last_recommendations = recommendations[-5:] if recommendations else []

    def update_action_context(self, action, items):
        """Track the last action taken for better context."""
        self.last_action_context = {
            "action": action,
            "items": items,
            "timestamp": datetime.now().isoformat()
        }

    def get_contextual_products(self):
        """Get products from recent context with relevance scoring."""
        if self.context_score > 0.3:  # Context is still relevant
            return self.last_products
        return []

    def decay_context(self):
        """Gradually reduce context relevance over time."""
        self.context_score *= 0.8  # Decay factor

    def has_valid_context(self):
        """Check if context is still valid for reference resolution."""
        return self.context_score > 0.3 and len(self.last_products) > 0

# State schema for the agent
class ShoppingAssistantState(TypedDict):
    """State schema for the shopping assistant agent."""
    # User context
    user_id: str
    user_profile: Dict[str, Any]
    chat_history: List[Dict[str, str]]  # Keep as simple dict format
    current_message: str
    
    # Shopping context
    shopping_list: List[Dict[str, Any]]
    current_intent: str
    search_query: str
    retrieved_products: List[Dict[str, Any]]
    
    # Agent reasoning
    agent_thoughts: List[str]
    reasoning_step: str
    recommendations: List[Dict[str, Any]]
    
    # Task execution
    actions_taken: List[str]
    api_responses: List[Dict[str, Any]]
    final_response: str

    # Context persistence (new)
    conversation_context: Optional[ConversationState]

class WalmartShoppingAssistant:
    """
    LangGraph-powered personalized shopping assistant for Walmart.
    Provides autonomous conversation, product discovery, and shopping list curation.
    """
    
    def __init__(self):
        """Initialize the shopping assistant with all necessary components."""
        # Initialize LLM (Gemini)
        self.llm = ChatGoogleGenerativeAI(
            model=Config.GEMINI_MODEL,
            temperature=Config.DEFAULT_TEMPERATURE,
            google_api_key=Config.GEMINI_API_KEY
        )
        
        # Initialize RAG components
        self.product_searcher = ProductSearcher(Config.CHROMA_PERSIST_DIRECTORY)
        
        # Initialize tools with the shared searcher
        from shopping_tools import initialize_tools
        initialize_tools(self.product_searcher)
        
        # Build the agent graph
        self.agent_graph = self._build_agent_graph()
        
        # Intent classification prompt with conversation context
        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intent classifier for a shopping assistant. 
            Analyze the user's message and determine their primary intent, considering the conversation history.
            
            Possible intents:
            - product_discovery: Looking for specific products, asking "what do you have", or requesting ingredients for dishes/meals
            - shopping_list_management: Adding/removing/clearing items from shopping list, viewing list
            - meal_planning: Planning meals, asking for recipes, meal prep
            - budget_analysis: Questions about spending, budget optimization
            - nutrition_analysis: Health-focused queries, dietary needs
            - general_chat: Casual conversation, greetings, general questions, follow-up responses
            - comparison: Comparing products or asking for alternatives
            
            IMPORTANT CLASSIFICATION RULES:
            
            For PRODUCT_DISCOVERY (includes ingredient requests):
            - "I want chicken salad" = product_discovery (searching for ingredients)
            - "Find me pasta ingredients" = product_discovery
            - "What snacks do you have" = product_discovery
            - "I need ingredients for dinner" = product_discovery
            
            For SHOPPING_LIST_MANAGEMENT:
            - Clear/empty/reset my list
            - I don't need these anymore
            - Start fresh / Remove everything
            - Show me my list / View my cart
            - Add these to my cart/list
            - Add those items to my cart
            - Put those in my cart
            - "Add them all" or "add the ingredients"
            
            CONTEXT AWARENESS: If the conversation history shows that the assistant just provided:
            - Product recommendations or ingredient lists
            - A meal plan, recipes, or meal suggestions
            
            And the user now says something like:
            - "add those to my cart" / "add these items" / "put those in my list"
            - "I'll take those" / "add them to my cart" / "add everything"
            - "add the ingredients" / "add all of those"
            
            Then classify this as "shopping_list_management" because they're referring to previously mentioned items.
            
            Respond with ONLY the intent name."""),
            ("human", """
            Conversation History: {chat_history}
            Current Message: {message}
            """)
        ])
        
        self.response_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful Walmart shopping assistant. Your role is to provide personalized, clear, and actionable responses to users about their shopping needs.

            CORE PRINCIPLES:
            1. Be conversational and friendly
            2. Explain your reasoning clearly
            3. When you find products, specify what search strategy you used
            4. If you add items to cart, explain what you added and why
            5. For dish requests (like "chicken salad"), explain that you searched for the complete set of ingredients
            6. Always be specific about what actions you took
            
            RESPONSE GUIDELINES:
            - If you performed a comprehensive search for a dish, mention the main ingredient and supporting ingredients
            - If you added items to their cart, list the key items and explain the reasoning
            - If you filtered results, mention the filters applied (dietary restrictions, budget)
            - Use emojis appropriately to make responses engaging
            - Always end with an offer to help further or adjust the selection"""),
            ("human", """
            User ID: {user_id}
            User Profile: {user_profile}
            Conversation History: {chat_history}
            Current Message: {current_message}
            Intent: {current_intent}
            
            Search Strategy Used: {search_strategy}
            Is Dish Request: {is_dish_request}
            Primary Search: {primary_search}
            Secondary Searches: {secondary_searches}
            
            Retrieved Products: {retrieved_products}
            Current Shopping List: {shopping_list}
            Agent Thoughts: {agent_thoughts}
            Actions Taken: {actions_taken}
            
            Based on the conversation history and current context, provide a helpful and personalized response to the user.
            Be conversational, specific, and actionable. Reference previous parts of the conversation when relevant.
            Explain your search strategy and what you found. If you've made changes to their shopping list, mention them specifically.
            """)
        ])
    
    def _add_thought(self, state: ShoppingAssistantState, thought: str) -> ShoppingAssistantState:
        """Add a thought to the agent's reasoning stream."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_thought = f"[{timestamp}] {thought}"
        
        # Create a new state dict with the updated thoughts
        new_state = dict(state)
        new_state["agent_thoughts"] = state["agent_thoughts"] + [formatted_thought]
        print(f"🤔 Agent Thought: {formatted_thought}")
        return new_state
    
    async def _make_agentic_decision(self, prompt: str, context: str = "") -> str:
        """
        Make an agentic decision using the LLM for intelligent action determination.
        
        Args:
            prompt: The decision prompt for the LLM
            context: Additional context for the decision
            
        Returns:
            The LLM's decision as a string
        """
        try:
            full_prompt = f"{prompt}\n\nContext: {context}" if context else prompt
            logger.info("LLM API call: Making agentic decision.")
            response = self.llm.invoke([HumanMessage(content=full_prompt)])
            decision = response.content.strip().upper()
            logger.info(f"LLM agentic decision: {decision}")
            return decision
        except Exception as e:
            logger.error(f"Error in agentic decision making: {e}")
            return "FALLBACK"
    
    def _build_agent_graph(self) -> StateGraph:
        """Build the LangGraph workflow for the shopping assistant."""
        
        # Define all the node functions
        def analyze_user_intent(state: ShoppingAssistantState) -> ShoppingAssistantState:
            """Analyze user message to determine intent and extract key information."""
            state = self._add_thought(state, f"Analyzing user intent for: '{state['current_message']}'")
            
            try:
                # Initialize conversation context if not present
                if not state.get("conversation_context"):
                    new_state = dict(state)
                    new_state["conversation_context"] = ConversationState()
                else:
                    new_state = dict(state)
                    # Decay context over time
                    new_state["conversation_context"].decay_context()

                # Format chat history for the prompt
                chat_history_text = ""
                if state.get("chat_history"):
                    history_items = []
                    for msg in state["chat_history"][-6:]:  # Last 6 messages for context
                        role = "User" if msg.get("role") == "user" else "Assistant"
                        content = msg.get("content", "")
                        history_items.append(f"{role}: {content}")
                    chat_history_text = "\n".join(history_items)
                
                # Enhanced intent classification with context scoring
                message_lower = state["current_message"].lower()
                context_score = 0.0

                # Check if we have valid conversation context
                if new_state["conversation_context"].has_valid_context():
                    context_score = new_state["conversation_context"].context_score
                    state = self._add_thought(state, f"Valid context available (score: {context_score:.2f})")

                # Enhanced pattern matching for context-aware phrases
                contextual_add_phrases = [
                    "add those", "add these", "add them", "put those", "put these",
                    "add the ingredients", "add everything", "i'll take those",
                    "add all of those", "put them in my cart", "add to my list"
                ]

                is_contextual_add = any(phrase in message_lower for phrase in contextual_add_phrases)

                # Use LLM to classify intent with conversation context
                logger.info("LLM API call: Enhanced intent classification with context.")
                response = self.llm.invoke(
                    self.intent_prompt.format_messages(
                        chat_history=chat_history_text,
                        message=state["current_message"]
                    )
                )
                intent = response.content.strip().lower()
                
                # Apply context-weighted intent scoring
                if is_contextual_add and context_score > 0.3:
                    # Override LLM decision if we have strong context and contextual language
                    intent = "shopping_list_management"
                    new_state = self._add_thought(new_state, f"Context override: detected contextual add with score {context_score:.2f}")

                # Enhanced fallback pattern matching
                if intent not in ["product_discovery", "shopping_list_management", "meal_planning",
                                "budget_analysis", "nutrition_analysis", "general_chat", "comparison"]:
                    # Apply enhanced pattern matching as fallback
                    if any(keyword in message_lower for keyword in ["clear", "empty", "remove", "delete shopping list", "reset list"]):
                        intent = "shopping_list_management"
                    elif is_contextual_add:
                        intent = "shopping_list_management"
                    elif any(keyword in message_lower for keyword in ["meal", "recipe", "dinner", "breakfast", "lunch", "plan meals"]):
                        intent = "meal_planning"
                    elif any(keyword in message_lower for keyword in ["hello", "hi", "hey", "thank", "thanks"]):
                        intent = "general_chat"
                    elif any(keyword in message_lower for keyword in ["budget", "spend", "cost", "money"]):
                        intent = "budget_analysis"
                    elif any(food_phrase in message_lower for food_phrase in ["chicken salad", "pasta dinner", "sandwich ingredients", "breakfast bowl"]):
                        intent = "product_discovery"  # These are complex food requests
                    elif any(keyword in message_lower for keyword in ["snack", "food", "product", "find", "buy", "need", "want", "ingredients", "salad"]):
                        intent = "product_discovery"
                    else:
                        intent = "general_chat"
                
                # Update state
                new_state["current_intent"] = intent
                new_state["reasoning_step"] = "intent_analysis"
                
                new_state = self._add_thought(new_state, f"Detected intent: {intent}")
                
                # Extract search query for product-related intents
                if intent in ["product_discovery", "comparison", "meal_planning"]:
                    new_state["search_query"] = state["current_message"]
                elif intent == "general_chat" and chat_history_text and "meal" in chat_history_text.lower():
                    # If this is general chat but previous conversation was about meals, continue meal planning
                    new_state["current_intent"] = "meal_planning"
                    new_state["search_query"] = f"oatmeal breakfast {state['current_message']}"
                    new_state = self._add_thought(new_state, "Continuing meal planning conversation with oatmeal focus")
                
                return new_state
                    
            except Exception as e:
                state = self._add_thought(state, f"Error in intent analysis: {str(e)}")
                new_state = dict(state)
                new_state["current_intent"] = "general_chat"
                if not new_state.get("conversation_context"):
                    new_state["conversation_context"] = ConversationState()
                return new_state
        
        async def discover_products(state: ShoppingAssistantState) -> ShoppingAssistantState:
            """Use advanced tools to find and filter relevant products with intelligent query decomposition."""
            query = state['search_query']
            logger.info(f"Starting intelligent product discovery for query: '{query}'")
            state = self._add_thought(state, f"Analyzing and decomposing query: '{query}'")
            
            try:
                # Get user preferences for filtering
                user_preferences = state.get("user_profile", {})
                dietary_restrictions = user_preferences.get("dietary_restrictions", [])
                budget_limit = user_preferences.get("budget_limit")
                
                logger.info(f"User preferences - Dietary: {dietary_restrictions}, Budget: {budget_limit}")
                
                # Assess query complexity to avoid over-processing simple requests
                query_lower = query.lower()
                simple_indicators = ["i need", "find me", "show me", "buy", "get me"]
                complex_indicators = ["ingredients for", "make", "recipe", "meal plan", "dinner"]

                is_simple_query = any(indicator in query_lower for indicator in simple_indicators) and not any(complex in query_lower for complex in complex_indicators)

                if is_simple_query and len(query.split()) <= 3:
                    # Simple product search - don't over-analyze
                    logger.info("Detected simple query - using direct search approach")
                    state = self._add_thought(state, "Simple query detected - direct search approach")

                    primary_params = {
                        "query": query,
                        "max_results": Config.MAX_PRODUCTS_TO_RETRIEVE
                    }
                    try:
                        primary_products = await search_products_semantic.ainvoke(primary_params)
                        log_tool_usage("search_products_semantic (simple)", primary_params, primary_products)
                        logger.info(f"Simple search '{query}' returned {len(primary_products)} products")

                        new_state = dict(state)
                        new_state["retrieved_products"] = primary_products
                        new_state["search_strategy"] = "simple_product_search"
                        new_state["is_dish_request"] = False
                        new_state["primary_search"] = query
                        new_state["secondary_searches"] = []

                        # Update conversation context with found products
                        if new_state.get("conversation_context"):
                            new_state["conversation_context"].update_products(primary_products, state.get("current_intent", ""))
                            new_state = self._add_thought(new_state, f"Updated context with {len(primary_products)} products")

                    except Exception as e:
                        log_tool_usage("search_products_semantic (simple)", primary_params, error=str(e))
                        logger.error(f"Simple search failed: {e}")
                        new_state = dict(state)
                        new_state["retrieved_products"] = []

                else:
                    # Complex query analysis and decomposition
                    # STEP 1: Intelligent Query Analysis & Decomposition
                    query_analysis_prompt = f"""
                    Analyze this user query for shopping and determine the search strategy:
                    
                    Query: "{query}"
                    User dietary restrictions: {dietary_restrictions}
                    
                    Is this a complete dish/meal request that needs multiple ingredients? 
                    Examples of complete dishes: "chicken salad", "pasta dinner", "breakfast bowl", "sandwich", "stir fry"
                    
                    If YES, list the core ingredients needed:
                    - Primary item (main ingredient)
                    - Secondary items (supporting ingredients)
                    - Optional items (extras that would complete the dish)
                    
                    If NO, it's a simple product search.
                    
                    Respond in this exact format:
                    DISH_REQUEST: YES or NO
                    PRIMARY: [main ingredient to search for]
                    SECONDARY: [ingredient1, ingredient2, ingredient3] (comma separated, max 4 items)
                    OPTIONAL: [optional1, optional2] (comma separated, max 2 items)
                    
                    Example for "chicken salad":
                    DISH_REQUEST: YES
                    PRIMARY: canned chicken
                    SECONDARY: lettuce, mayonnaise, celery, bread
                    OPTIONAL: tomatoes, onions
                    """

                    # Use LLM to analyze and decompose the query
                    analysis_response = await self._make_agentic_decision(query_analysis_prompt)

                    # Parse the response
                    is_dish_request = False
                    primary_search = query
                    secondary_searches = []
                    optional_searches = []

                    try:
                        lines = analysis_response.strip().split('\n')
                        for line in lines:
                            if line.startswith('DISH_REQUEST:'):
                                is_dish_request = 'YES' in line.upper()
                            elif line.startswith('PRIMARY:'):
                                primary_search = line.split(':', 1)[1].strip()
                            elif line.startswith('SECONDARY:'):
                                secondary_items = line.split(':', 1)[1].strip()
                                if secondary_items and secondary_items != '[]':
                                    secondary_searches = [item.strip() for item in secondary_items.split(',') if item.strip()]
                            elif line.startswith('OPTIONAL:'):
                                optional_items = line.split(':', 1)[1].strip()
                                if optional_items and optional_items != '[]':
                                    optional_searches = [item.strip() for item in optional_items.split(',') if item.strip()]
                    except Exception as parse_error:
                        logger.warning(f"Failed to parse query analysis, using simple search: {parse_error}")
                        is_dish_request = False

                    logger.info(f"Query analysis - Dish request: {is_dish_request}, Primary: '{primary_search}', Secondary: {secondary_searches}, Optional: {optional_searches}")
                    state = self._add_thought(state, f"Query decomposed - Primary: '{primary_search}', {len(secondary_searches)} secondary items")

                    # STEP 2: Execute Comprehensive Search Strategy
                    all_products = []

                    # Primary search (always performed)
                    primary_params = {
                        "query": primary_search,
                        "max_results": Config.MAX_PRODUCTS_TO_RETRIEVE
                    }
                    try:
                        primary_products = await search_products_semantic.ainvoke(primary_params)
                        log_tool_usage("search_products_semantic (primary)", primary_params, primary_products)
                        logger.info(f"Primary search '{primary_search}' returned {len(primary_products)} products")
                        all_products.extend(primary_products)
                    except Exception as e:
                        log_tool_usage("search_products_semantic (primary)", primary_params, error=str(e))
                        logger.error(f"Primary search failed: {e}")

                    # Secondary searches (for dish requests)
                    if is_dish_request and secondary_searches:
                        for secondary_item in secondary_searches:
                            secondary_params = {
                                "query": secondary_item,
                                "max_results": 2  # Limit secondary items to avoid overwhelming
                            }
                            try:
                                secondary_products = await search_products_semantic.ainvoke(secondary_params)
                                log_tool_usage("search_products_semantic (secondary)", secondary_params, secondary_products)
                                logger.info(f"Secondary search '{secondary_item}' returned {len(secondary_products)} products")
                                all_products.extend(secondary_products)
                            except Exception as e:
                                log_tool_usage("search_products_semantic (secondary)", secondary_params, error=str(e))
                                logger.error(f"Secondary search for '{secondary_item}' failed: {e}")

                    # Optional searches (for dish requests, only if we have room)
                    if is_dish_request and optional_searches and len(all_products) < Config.MAX_PRODUCTS_TO_RETRIEVE:
                        remaining_slots = Config.MAX_PRODUCTS_TO_RETRIEVE - len(all_products)
                        for optional_item in optional_searches[:remaining_slots]:
                            optional_params = {
                                "query": optional_item,
                                "max_results": 1  # Just one option for optional items
                            }
                            try:
                                optional_products = await search_products_semantic.ainvoke(optional_params)
                                log_tool_usage("search_products_semantic (optional)", optional_params, optional_products)
                                logger.info(f"Optional search '{optional_item}' returned {len(optional_products)} products")
                                all_products.extend(optional_products)
                            except Exception as e:
                                log_tool_usage("search_products_semantic (optional)", optional_params, error=str(e))
                                logger.error(f"Optional search for '{optional_item}' failed: {e}")

                    # Remove duplicates while preserving order
                    seen_ids = set()
                    raw_products = []
                    for product in all_products:
                        product_id = product.get("id")
                        if product_id and product_id not in seen_ids:
                            seen_ids.add(product_id)
                            raw_products.append(product)

                    logger.info(f"Comprehensive search completed: {len(raw_products)} unique products found")

                    new_state = dict(state)
                    new_state["retrieved_products"] = raw_products
                    new_state = self._add_thought(new_state, f"Found {len(raw_products)} relevant products from comprehensive search")

                    # Mark the search strategy used for better response generation
                    new_state["search_strategy"] = "comprehensive_dish_search" if is_dish_request else "simple_product_search"
                    new_state["is_dish_request"] = is_dish_request
                    new_state["primary_search"] = primary_search
                    new_state["secondary_searches"] = secondary_searches

                # STEP 3: Apply Intelligent Filtering
                # Apply dietary restrictions filtering
                if dietary_restrictions and new_state["retrieved_products"]:
                    filter_params = {
                        "products": new_state["retrieved_products"],
                        "restrictions": dietary_restrictions
                    }
                    try:
                        filtered_products = await filter_products_by_dietary_restrictions.ainvoke(filter_params)
                        log_tool_usage("filter_products_by_dietary_restrictions", filter_params, filtered_products)
                        new_state["retrieved_products"] = filtered_products
                        new_state = self._add_thought(new_state, f"Filtered to {len(filtered_products)} products based on dietary preferences")
                        logger.info(f"Applied dietary restrictions filter: {len(new_state['retrieved_products'])} -> {len(filtered_products)} products")
                    except Exception as e:
                        log_tool_usage("filter_products_by_dietary_restrictions", filter_params, error=str(e))
                        logger.error(f"Dietary filtering failed: {e}")
                elif dietary_restrictions:
                    logger.info("No products to filter for dietary restrictions")
                
                # Apply budget filtering if budget limit is specified
                if budget_limit and new_state["retrieved_products"]:
                    budget_params = {
                        "products": new_state["retrieved_products"], 
                        "budget_limit": budget_limit
                    }
                    try:
                        budget_filtered = await filter_products_by_budget.ainvoke(budget_params)
                        log_tool_usage("filter_products_by_budget", budget_params, budget_filtered)
                        original_count = len(new_state["retrieved_products"])
                        new_state["retrieved_products"] = budget_filtered
                        new_state = self._add_thought(new_state, f"Filtered to {len(budget_filtered)} products within ${budget_limit} budget")
                        logger.info(f"Applied budget filter: {original_count} -> {len(budget_filtered)} products within ${budget_limit}")
                    except Exception as e:
                        log_tool_usage("filter_products_by_budget", budget_params, error=str(e))
                        logger.error(f"Budget filtering failed: {e}")
                elif budget_limit:
                    logger.info("No products to filter for budget limit")
                
                # Update conversation context with final products
                if new_state.get("conversation_context"):
                    new_state["conversation_context"].update_products(new_state["retrieved_products"], state.get("current_intent", ""))
                    new_state = self._add_thought(new_state, f"Context updated with {len(new_state['retrieved_products'])} final products")

                new_state["reasoning_step"] = "product_discovery"
                
                logger.info(f"Product discovery completed. Final result: {len(new_state['retrieved_products'])} products using {new_state.get('search_strategy', 'unknown')}")
                return new_state
                
            except Exception as e:
                logger.error(f"Error during product discovery: {e}")
                new_state = dict(state)
                new_state["retrieved_products"] = []
                new_state = self._add_thought(new_state, f"Error during product search: {str(e)}")
                return new_state
        
        async def execute_actions(state: ShoppingAssistantState) -> ShoppingAssistantState:
            """Execute advanced actions based on intent using the tools."""
            intent = state.get("current_intent", "")
            logger.info(f"Starting action execution for intent: {intent}")
            state = self._add_thought(state, f"Executing actions for intent: {intent}")
            
            try:
                user_id = state.get("user_id", "")
                actions_taken = []
                new_state = dict(state)
                
                # Load user profile if not already loaded
                if not state.get("user_profile"):
                    logger.info(f"Loading user profile for user_id: {user_id}")
                    tool_params = {"user_id": user_id}
                    try:
                        user_profile = await get_user_preferences.ainvoke(tool_params)
                        log_tool_usage("get_user_preferences", tool_params, user_profile)
                        new_state["user_profile"] = user_profile
                        actions_taken.append("Loaded user profile from backend API")
                        logger.info(f"Successfully loaded user profile: {list(user_profile.keys()) if user_profile else 'empty'}")
                    except Exception as e:
                        log_tool_usage("get_user_preferences", tool_params, error=str(e))
                        actions_taken.append("Failed to load user profile from backend")
                        logger.warning(f"Failed to load user profile: {e}")
                
                # Get current shopping list
                logger.info(f"Retrieving shopping list for user_id: {user_id}")
                tool_params = {"user_id": user_id}
                try:
                    current_shopping_list = await get_user_shopping_list.ainvoke(tool_params)
                    log_tool_usage("get_user_shopping_list", tool_params, current_shopping_list)
                    new_state["shopping_list"] = current_shopping_list
                    actions_taken.append(f"Retrieved shopping list ({len(current_shopping_list)} items)")
                    logger.info(f"Successfully retrieved shopping list with {len(current_shopping_list)} items")
                except Exception as e:
                    log_tool_usage("get_user_shopping_list", tool_params, error=str(e))
                    actions_taken.append("Failed to retrieve shopping list from backend")
                    logger.warning(f"Failed to retrieve shopping list: {e}")
                    new_state["shopping_list"] = []
                
                # Initialize recommendations if not present
                if "recommendations" not in new_state:
                    new_state["recommendations"] = []
                
                # Intent-specific actions with enhanced agentic decision making
                if intent in ["shopping_list_management"]:
                    logger.info("Processing shopping list management intent with comprehensive context analysis")
                    
                    # Enhanced context awareness for shopping list actions
                    chat_history_text = ""
                    recent_assistant_mentions = []
                    if state.get("chat_history"):
                        history_items = []
                        for msg in state["chat_history"][-6:]:  # Last 6 messages for context
                            role = "User" if msg.get("role") == "user" else "Assistant"
                            content = msg.get("content", "")
                            history_items.append(f"{role}: {content}")
                            
                            # Extract items mentioned by assistant in recent messages
                            if role == "Assistant":
                                # Look for food items, ingredients, or product mentions
                                content_lower = content.lower()
                                food_keywords = ["chicken", "lettuce", "mayonnaise", "bread", "tomato", "celery", "onion", 
                                               "pasta", "rice", "milk", "eggs", "cheese", "yogurt", "banana", "apple",
                                               "oatmeal", "spinach", "olive oil", "garlic", "salt", "pepper"]
                                mentioned_items = [item for item in food_keywords if item in content_lower]
                                recent_assistant_mentions.extend(mentioned_items)
                        
                        chat_history_text = "\n".join(history_items)
                    
                    # Enhanced LLM decision making with better context understanding
                    shopping_action_prompt = f"""
                    Analyze this user message and recent conversation to determine what shopping list action they want:
                    
                    Recent conversation history:
                    {chat_history_text}
                    
                    Current user message: "{state["current_message"]}"
                    Current shopping list has: {len(new_state["shopping_list"])} items
                    Available products from current search: {len(state.get("retrieved_products", []))} items
                    Recent food items mentioned by assistant: {recent_assistant_mentions}
                    
                    Context analysis guidelines:
                    - Did the assistant just provide a meal plan, recipe, ingredient list, or product recommendations?
                    - Is the user now asking to add "those items", "these products", "the meal ingredients", etc.?
                    - Are they referring to a complete dish mentioned earlier (like "chicken salad")?
                    - Do they want to add ALL ingredients for a complete dish, not just the main item?
                    
                    Key phrases that indicate adding contextual items:
                    - "add those to my cart/list" 
                    - "add these items"
                    - "put those in my list"  
                    - "I'll take those"
                    - "add them all"
                    - "add the ingredients"
                    - "add everything for the salad/meal"
                    
                    Respond with ONLY one of these actions:
                    - CLEAR_LIST: if they want to empty/clear/reset their shopping list
                    - ADD_ALL_CONTEXT: if they want to add ALL items from recent conversation (complete dish ingredients)
                    - ADD_CURRENT_PRODUCTS: if they want to add currently found/searched products
                    - ADD_SPECIFIC_ITEMS: if they're mentioning specific items to add
                    - REMOVE_SPECIFIC: if they want to remove specific items
                    - VIEW_LIST: if they just want to see their current list
                    - NO_ACTION: if no clear shopping list action is needed
                    """
                    
                    shopping_action = await self._make_agentic_decision(shopping_action_prompt)
                    logger.info(f"Enhanced shopping action decision: {shopping_action}")
                    
                    # Execute the determined action with comprehensive item handling
                    if shopping_action == "CLEAR_LIST":
                        logger.info("Executing CLEAR_LIST action based on agentic decision")
                        tool_params = {"user_id": user_id}
                        try:
                            result = await clear_shopping_list.ainvoke(tool_params)
                            log_tool_usage("clear_shopping_list", tool_params, result)
                            if result.get("success"):
                                actions_taken.append(f"✅ {result.get('message', 'Shopping list cleared successfully')}")
                                new_state["shopping_list"] = []  # Update local state
                                logger.info(f"Successfully cleared shopping list: {result.get('message')}")
                            else:
                                actions_taken.append(f"⚠️ Partial clear: {result.get('message', 'Some items may not have been removed')}")
                                logger.warning(f"Partial clear result: {result.get('message')}")
                        except Exception as e:
                            log_tool_usage("clear_shopping_list", tool_params, error=str(e))
                            logger.error(f"Error clearing shopping list: {e}")
                            actions_taken.append("❌ Failed to clear shopping list due to technical error")
                    
                    elif shopping_action in ["ADD_ALL_CONTEXT", "ADD_CURRENT_PRODUCTS", "ADD_SPECIFIC_ITEMS"]:
                        logger.info(f"Executing {shopping_action} action based on agentic decision")
                        
                        products_to_add = []
                        
                        # Determine which products to add based on the action
                        if shopping_action == "ADD_ALL_CONTEXT":
                            # Look for items from conversation context and current search results
                            context_items = recent_assistant_mentions
                            current_products = new_state.get("retrieved_products", [])
                            
                            # If we have current products (from recent search), prioritize those
                            if current_products:
                                products_to_add = current_products
                                logger.info(f"Using {len(current_products)} products from recent search for context addition")
                            elif context_items:
                                # Search for mentioned items from conversation
                                logger.info(f"Searching for {len(context_items)} items mentioned in conversation: {context_items}")
                                for item in context_items[:6]:  # Limit to prevent overwhelming
                                    search_params = {"query": item, "max_results": 1}
                                    try:
                                        item_products = await search_products_semantic.ainvoke(search_params)
                                        if item_products and not any(p.get("error") for p in item_products):
                                            products_to_add.extend(item_products)
                                    except Exception as e:
                                        logger.error(f"Failed to search for context item '{item}': {e}")
                            
                            if products_to_add:
                                actions_taken.append(f"🔍 Found {len(products_to_add)} items from our conversation context")
                            else:
                                actions_taken.append("⚠️ I couldn't find the specific items we discussed. Could you clarify what you'd like to add?")
                        
                        elif shopping_action == "ADD_CURRENT_PRODUCTS":
                            all_products = new_state.get("retrieved_products", [])
                            
                            if all_products:
                                # Smart product selection: filter and prioritize the best matches
                                logger.info(f"Intelligently selecting from {len(all_products)} available products")
                                
                                # Sort products by relevance score and filter out poor matches
                                good_products = []
                                for product in all_products:
                                    relevance_score = product.get("relevance_score", 0)
                                    category = product.get("category", "").lower()
                                    
                                    # Skip products with very low relevance scores
                                    if relevance_score < 0.4:
                                        logger.info(f"Skipping low-relevance product: {product.get('name')} (score: {relevance_score:.3f})")
                                        continue
                                    
                                    # Skip obviously irrelevant categories for food searches
                                    if any(bad_cat in category for bad_cat in ['cell phone', 'electronics', 'tools']):
                                        logger.info(f"Skipping non-food product: {product.get('name')} (category: {category})")
                                        continue
                                    
                                    good_products.append(product)
                                
                                # Sort by relevance score (highest first)
                                good_products.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
                                
                                # For dish requests, try to get one from each ingredient category
                                if new_state.get("is_dish_request"):
                                    logger.info("Dish request detected - selecting diverse ingredients")
                                    
                                    # Group products by category to ensure diversity
                                    category_groups = {}
                                    for product in good_products:
                                        category = product.get("category", "Unknown")
                                        if category not in category_groups:
                                            category_groups[category] = []
                                        category_groups[category].append(product)
                                    
                                    # Take the best product from each category (max 6 categories)
                                    products_to_add = []
                                    for category, products in category_groups.items():
                                        if len(products_to_add) < 6:  # Reasonable limit for ingredients
                                            best_product = max(products, key=lambda x: x.get('relevance_score', 0))
                                            products_to_add.append(best_product)
                                            logger.info(f"Selected from {category}: {best_product.get('name')} (score: {best_product.get('relevance_score', 0):.3f})")
                                else:
                                    # For simple searches, take top 3 most relevant products
                                    products_to_add = good_products[:3]
                                
                                if products_to_add:
                                    actions_taken.append(f"🛒 Adding {len(products_to_add)} carefully selected products from your search")
                                    logger.info(f"Selected {len(products_to_add)} products out of {len(all_products)} available")
                                else:
                                    actions_taken.append("⚠️ No suitable products found from recent search to add")
                            else:
                                actions_taken.append("⚠️ No products found from recent search to add")
                        
                        elif shopping_action == "ADD_SPECIFIC_ITEMS":
                            # CRITICAL FIX: Check conversation context FIRST for recent products
                            user_message = state["current_message"].lower()
                            
                            # Check if user is referring to recent products in context
                            context_products = []
                            if new_state.get("conversation_context") and new_state["conversation_context"].has_valid_context():
                                context_products = new_state["conversation_context"].get_contextual_products()
                                logger.info(f"Found {len(context_products)} products in conversation context")
                            
                            # Check if they're referring to a specific product by name
                            specific_product_match = None
                            product_name_phrases = ["asus vivobook", "laptop", "macbook", "dell", "hp"]
                            
                            for phrase in product_name_phrases:
                                if phrase in user_message:
                                    # Search in context products first
                                    for product in context_products:
                                        if phrase.lower() in product.get("name", "").lower():
                                            specific_product_match = product
                                            logger.info(f"Found specific product match in context: {product.get('name')}")
                                            break
                                    break
                            
                            if specific_product_match:
                                # User is referring to a specific product from recent search
                                products_to_add = [specific_product_match]
                                actions_taken.append(f"🎯 Found the specific product you mentioned: {specific_product_match.get('name')}")
                            elif context_products and any(phrase in user_message for phrase in ["those", "these", "them", "that one"]):
                                # User is referring to context products with generic terms
                                products_to_add = context_products[:3]  # Take top 3 from context
                                actions_taken.append(f"📋 Adding {len(products_to_add)} products from our previous search")
                            else:
                                # Extract specific items mentioned in the current message (fallback)
                                specific_items = []
                                food_terms = ["chicken", "lettuce", "mayonnaise", "bread", "tomato", "celery", "onion",
                                            "pasta", "rice", "milk", "eggs", "cheese", "yogurt", "banana", "apple"]
                                
                                # Look for food terms in the message
                                mentioned_foods = [term for term in food_terms if term in user_message]
                                
                                # Also check if they mentioned complete dishes
                                dish_terms = {"salad": ["lettuce", "tomato", "cucumber"], 
                                            "sandwich": ["bread", "lettuce", "tomato"],
                                            "pasta": ["pasta", "sauce", "cheese"]}
                                
                                for dish, ingredients in dish_terms.items():
                                    if dish in user_message:
                                        mentioned_foods.extend(ingredients)
                                
                                # Remove duplicates
                                mentioned_foods = list(set(mentioned_foods))
                            
                                # Remove duplicates
                                mentioned_foods = list(set(mentioned_foods))
                                
                                if mentioned_foods:
                                    logger.info(f"Searching for specific items mentioned: {mentioned_foods}")
                                    for item in mentioned_foods[:5]:  # Limit to 5 items
                                        search_params = {"query": item, "max_results": 1}
                                        try:
                                            item_products = await search_products_semantic.ainvoke(search_params)
                                            if item_products and not any(p.get("error") for p in item_products):
                                                products_to_add.extend(item_products)
                                        except Exception as e:
                                            logger.error(f"Failed to search for specific item '{item}': {e}")
                                    
                                    actions_taken.append(f"🔍 Found {len(products_to_add)} items matching: {', '.join(mentioned_foods[:3])}")
                                else:
                                    actions_taken.append("⚠️ Please specify which items you'd like me to add to your cart")
                        
                        # Add products to shopping list with better error handling
                        if products_to_add:
                            added_count = 0
                            failed_count = 0
                            added_items = []
                            skipped_items = []
                            
                            logger.info(f"Attempting to add {len(products_to_add)} selected products to shopping list")
                            
                            for product in products_to_add:
                                product_id = product.get("id")
                                product_name = product.get("name", "Unknown item")
                                category = product.get("category", "Unknown")
                                
                                # Additional safety check to avoid obviously wrong products
                                if any(bad_term in product_name.lower() for bad_term in ['cell phone', 'mobile', 'electronic']):
                                    skipped_items.append(f"{product_name} (not food)")
                                    logger.info(f"Skipping non-food item: {product_name}")
                                    continue
                                
                                if product_id:
                                    tool_params = {
                                        "user_id": user_id, 
                                        "product_id": product_id, 
                                        "quantity": 1
                                    }
                                    try:
                                        result = await add_product_to_list.ainvoke(tool_params)
                                        log_tool_usage("add_product_to_list", tool_params, result)
                                        if result.get("success"):
                                            added_count += 1
                                            added_items.append(product_name)
                                            logger.info(f"Successfully added product {product_name} (ID: {product_id}) to shopping list")
                                        else:
                                            failed_count += 1
                                            logger.warning(f"Failed to add product {product_name}: {result.get('error')}")
                                    except Exception as e:
                                        failed_count += 1
                                        log_tool_usage("add_product_to_list", tool_params, error=str(e))
                                        logger.error(f"Error adding product {product_name} to shopping list: {e}")
                                else:
                                    failed_count += 1
                                    logger.warning(f"Product {product_name} has no ID - cannot add to shopping list")
                            
                            # Provide comprehensive feedback
                            if added_count > 0:
                                items_summary = ", ".join(added_items[:3])  # Show first 3 items
                                if len(added_items) > 3:
                                    items_summary += f" and {len(added_items) - 3} more"
                                actions_taken.append(f"✅ Added {added_count} items to your cart: {items_summary}")
                                
                                # If this was a dish request, mention completeness
                                if new_state.get("is_dish_request"):
                                    dish_name = new_state.get("primary_search", "dish")
                                    actions_taken.append(f"🍽️ Your {dish_name} ingredients are ready!")
                            
                            if failed_count > 0:
                                actions_taken.append(f"⚠️ {failed_count} products could not be added (backend issue)")
                            
                            if skipped_items:
                                actions_taken.append(f"⏭️ Skipped {len(skipped_items)} irrelevant items")
                                
                        else:
                            actions_taken.append("⚠️ No suitable items found to add. Please be more specific about what you'd like.")
                    
                    elif shopping_action == "VIEW_LIST":
                        actions_taken.append(f"📋 Your shopping list contains {len(new_state['shopping_list'])} items")
                        logger.info("User requested to view their current shopping list")
                    
                    elif shopping_action == "REMOVE_SPECIFIC":
                        actions_taken.append("🔧 Specific item removal feature coming soon!")
                        logger.info("User requested specific item removal (not yet implemented)")
                    
                    else:  # NO_ACTION, FALLBACK, or unknown
                        logger.info(f"No specific shopping list action needed for decision: {shopping_action}")
                        actions_taken.append("📝 I'm ready to help with your shopping list")
                
                elif intent in ["budget_analysis"]:
                    logger.info("Processing budget analysis intent with agentic decision making")
                    
                    # Use LLM to determine what specific budget analysis is needed
                    budget_action_prompt = f"""
                    Analyze this user message about budget and determine what specific analysis they want:
                    
                    User message: "{state["current_message"]}"
                    Current shopping list has: {len(new_state["shopping_list"])} items
                    User budget limit: {state.get("user_profile", {}).get("budget_limit", "not set")}
                    
                    Respond with ONLY one of these actions:
                    - GET_SPENDING: if they want to see their spending history/analytics
                    - OPTIMIZE_LIST: if they want to optimize their current shopping list for budget
                    - SET_BUDGET: if they want to set or change their budget limit
                    - BUDGET_ADVICE: if they want general budget advice
                    - NO_ACTION: if no specific budget action is needed
                    """
                    
                    budget_action = await self._make_agentic_decision(budget_action_prompt)
                    
                    # Execute determined budget action with robust error handling
                    if budget_action == "GET_SPENDING":
                        logger.info("Executing GET_SPENDING action based on agentic decision")
                        tool_params = {"user_id": user_id}
                        try:
                            spending_data = await get_spending_breakdown.ainvoke(tool_params)
                            log_tool_usage("get_spending_breakdown", tool_params, spending_data)
                            if "api_responses" not in new_state:
                                new_state["api_responses"] = []
                            new_state["api_responses"].append({"spending_analytics": spending_data})
                            actions_taken.append("📊 Retrieved your spending analytics")
                            logger.info("Successfully retrieved spending analytics")
                        except Exception as e:
                            log_tool_usage("get_spending_breakdown", tool_params, error=str(e))
                            logger.error(f"Failed to retrieve spending analytics: {e}")
                            actions_taken.append("❌ Unable to retrieve spending data at this time")
                    
                    elif budget_action == "OPTIMIZE_LIST":
                        logger.info("Executing OPTIMIZE_LIST action based on agentic decision")
                        if new_state.get("shopping_list"):
                            budget_limit = state.get("user_profile", {}).get("budget_limit", 100.0)
                            tool_params = {
                                "shopping_list": new_state["shopping_list"], 
                                "max_budget": budget_limit
                            }
                            try:
                                optimized_list = await optimize_shopping_list_for_budget.ainvoke(tool_params)
                                log_tool_usage("optimize_shopping_list_for_budget", tool_params, optimized_list)
                                
                                if optimized_list.get("error"):
                                    actions_taken.append("❌ Unable to optimize your shopping list at this time")
                                    logger.error(f"Budget optimization failed: {optimized_list.get('error')}")
                                else:
                                    new_state["recommendations"].append({
                                        "type": "budget_optimization",
                                        "optimized_list": optimized_list,
                                        "reason": f"Optimized for ${budget_limit} budget"
                                    })
                                    savings = optimized_list.get("savings", 0)
                                    actions_taken.append(f"💰 Optimized your list - potential savings: ${savings:.2f}")
                                    logger.info(f"Successfully optimized shopping list with ${savings:.2f} savings")
                            except Exception as e:
                                log_tool_usage("optimize_shopping_list_for_budget", tool_params, error=str(e))
                                logger.error(f"Failed to optimize shopping list: {e}")
                                actions_taken.append("❌ Unable to optimize your shopping list due to technical error")
                        else:
                            actions_taken.append("⚠️ No items in your shopping list to optimize")
                            logger.info("No shopping list items available for budget optimization")
                    
                    elif budget_action == "SET_BUDGET":
                        actions_taken.append("🔧 Budget setting feature - please specify your desired budget amount")
                        logger.info("User wants to set/change budget limit (feature to be enhanced)")
                    
                    elif budget_action == "BUDGET_ADVICE":
                        actions_taken.append("💡 Added budget advice to recommendations")
                        new_state["recommendations"].append({
                            "type": "budget_advice",
                            "advice": "Consider setting a weekly budget limit and tracking your spending by category",
                            "reason": "General budget management guidance"
                        })
                        logger.info("Provided general budget advice")
                    
                    else:  # NO_ACTION, FALLBACK, or unknown
                        logger.info(f"No specific budget action needed for decision: {budget_action}")
                        actions_taken.append("📋 Reviewed your budget preferences")
                
                elif intent in ["meal_planning"]:
                    logger.info("Processing meal planning intent with agentic decision making")
                    
                    # Use LLM to determine specific meal planning needs
                    meal_action_prompt = f"""
                    Analyze this user message about meal planning and determine what they specifically need:
                    
                    User message: "{state["current_message"]}"
                    User dietary restrictions: {state.get("user_profile", {}).get("dietary_restrictions", [])}
                    User budget: {state.get("user_profile", {}).get("budget_limit", "not set")}
                    Available products from search: {len(state.get("retrieved_products", []))} items
                    
                    Respond with ONLY one of these actions:
                    - FULL_MEAL_PLAN: if they want a complete weekly meal plan with shopping list
                    - QUICK_RECIPE: if they need a quick recipe for today/tonight
                    - INGREDIENT_LIST: if they want ingredients for a specific dish
                    - DIETARY_MEALS: if they want meals that fit specific dietary needs
                    - MEAL_PREP: if they want meal prep suggestions
                    - NO_ACTION: if no specific meal planning action is needed
                    """
                    
                    meal_action = await self._make_agentic_decision(meal_action_prompt)
                    
                    # Execute determined meal planning action
                    if meal_action in ["FULL_MEAL_PLAN", "MEAL_PREP", "DIETARY_MEALS"]:
                        logger.info(f"Executing {meal_action} action based on agentic decision")
                        dietary_prefs = state.get("user_profile", {}).get("dietary_restrictions", [])
                        budget = state.get("user_profile", {}).get("budget_limit", 100.0)
                        
                        # Adjust days based on action type
                        days = 7 if meal_action == "FULL_MEAL_PLAN" else 3 if meal_action == "MEAL_PREP" else 5
                        
                        tool_params = {
                            "dietary_preferences": dietary_prefs, 
                            "budget": budget, 
                            "days": days
                        }
                        try:
                            meal_plan = await generate_meal_plan_suggestions.ainvoke(tool_params)
                            log_tool_usage("generate_meal_plan_suggestions", tool_params, meal_plan)
                            
                            if meal_plan.get("error"):
                                actions_taken.append("❌ Unable to generate meal plan at this time")
                                logger.error(f"Meal plan generation failed: {meal_plan.get('error')}")
                            else:
                                plan_type = "weekly" if days == 7 else "meal prep" if days == 3 else "dietary-focused"
                                new_state["recommendations"].append({
                                    "type": "meal_plan",
                                    "meal_suggestions": meal_plan,
                                    "reason": f"Personalized {plan_type} meal plan based on your preferences"
                                })
                                
                                # Extract all products from meal plan and store them in retrieved_products
                                # so they can be added to shopping list when user requests it
                                meal_plan_products = []
                                meal_suggestions = meal_plan.get("meal_plan", {})
                                for meal_type, products in meal_suggestions.items():
                                    if isinstance(products, list):
                                        meal_plan_products.extend(products)
                                
                                # Store the meal plan products for potential shopping list addition
                                new_state["retrieved_products"] = meal_plan_products
                                
                                estimated_cost = meal_plan.get("estimated_cost", 0)
                                actions_taken.append(f"🍽️ Generated {plan_type} meal plan (estimated cost: ${estimated_cost:.2f})")
                                actions_taken.append(f"📋 Found {len(meal_plan_products)} ingredients you can add to your shopping list")
                                logger.info(f"Successfully generated meal plan for {len(dietary_prefs)} dietary preferences")
                                logger.info(f"Extracted {len(meal_plan_products)} products from meal plan for potential shopping list addition")
                        except Exception as e:
                            log_tool_usage("generate_meal_plan_suggestions", tool_params, error=str(e))
                            logger.error(f"Failed to generate meal plan: {e}")
                            actions_taken.append("❌ Unable to generate meal plan due to technical error")
                    
                    elif meal_action == "QUICK_RECIPE":
                        logger.info("Executing QUICK_RECIPE action based on agentic decision")
                        if state.get("retrieved_products"):
                            # Use found products to suggest a quick recipe
                            products = state["retrieved_products"][:3]
                            product_names = [p.get("name", "unknown") for p in products]
                            actions_taken.append(f"🍳 Found quick recipe ideas using: {', '.join(product_names)}")
                            new_state["recommendations"].append({
                                "type": "quick_recipe",
                                "ingredients": products,
                                "reason": "Quick recipe based on available ingredients"
                            })
                            logger.info("Generated quick recipe suggestions")
                        else:
                            actions_taken.append("🔍 No specific ingredients found - would you like me to search for something?")
                    
                    elif meal_action == "INGREDIENT_LIST":
                        logger.info("Executing INGREDIENT_LIST action based on agentic decision")
                        if state.get("retrieved_products"):
                            products = state["retrieved_products"]
                            actions_taken.append(f"📝 Found {len(products)} ingredients for your dish")
                            new_state["recommendations"].append({
                                "type": "ingredient_list",
                                "ingredients": products,
                                "reason": "Ingredients for your requested dish"
                            })
                        else:
                            actions_taken.append("⚠️ Please specify what dish you'd like ingredients for")
                    
                    else:  # NO_ACTION, FALLBACK, or unknown
                        logger.info(f"No specific meal planning action needed for decision: {meal_action}")
                        actions_taken.append("🍽️ Ready to help with your meal planning needs")
                
                elif intent in ["nutrition_analysis"]:
                    logger.info("Processing nutrition analysis intent with agentic decision making")
                    
                    # Use LLM to determine specific nutrition analysis needs
                    nutrition_action_prompt = f"""
                    Analyze this user message about nutrition and determine what specific analysis they want:
                    
                    User message: "{state["current_message"]}"
                    Shopping list items: {len(new_state.get("shopping_list", []))} items
                    Found products: {len(state.get("retrieved_products", []))} items
                    User dietary restrictions: {state.get("user_profile", {}).get("dietary_restrictions", [])}
                    
                    Respond with ONLY one of these actions:
                    - ANALYZE_SHOPPING_LIST: if they want nutrition analysis of their shopping list
                    - ANALYZE_PRODUCTS: if they want nutrition analysis of found/searched products
                    - HEALTH_RECOMMENDATIONS: if they want health-focused product recommendations
                    - DIETARY_CHECK: if they want to check if items meet their dietary needs
                    - NUTRITION_EDUCATION: if they want general nutrition information
                    - NO_ACTION: if no specific nutrition analysis is needed
                    """
                    
                    nutrition_action = await self._make_agentic_decision(nutrition_action_prompt)
                    
                    # Execute determined nutrition action
                    if nutrition_action == "ANALYZE_SHOPPING_LIST":
                        logger.info("Executing ANALYZE_SHOPPING_LIST action based on agentic decision")
                        if new_state.get("shopping_list"):
                            tool_params = {"shopping_list": new_state["shopping_list"]}
                            try:
                                nutrition_analysis = await analyze_nutrition_profile.ainvoke(tool_params)
                                log_tool_usage("analyze_nutrition_profile", tool_params, nutrition_analysis)
                                
                                if nutrition_analysis.get("error"):
                                    actions_taken.append("❌ Unable to analyze nutrition of your shopping list")
                                    logger.error(f"Nutrition analysis failed: {nutrition_analysis.get('error')}")
                                else:
                                    balance_score = nutrition_analysis.get("balance_score", 0)
                                    suggestions_count = len(nutrition_analysis.get("suggestions", []))
                                    new_state["recommendations"].append({
                                        "type": "nutrition_analysis",
                                        "analysis": nutrition_analysis,
                                        "reason": "Nutritional breakdown of your shopping list"
                                    })
                                    actions_taken.append(f"🥗 Analyzed your shopping list nutrition (balance score: {balance_score:.1%}, {suggestions_count} suggestions)")
                                    logger.info(f"Successfully analyzed nutrition for shopping list")
                            except Exception as e:
                                log_tool_usage("analyze_nutrition_profile", tool_params, error=str(e))
                                logger.error(f"Failed to analyze nutrition: {e}")
                                actions_taken.append("❌ Unable to analyze nutrition due to technical error")
                        else:
                            actions_taken.append("⚠️ Your shopping list is empty - add some items first")
                    
                    elif nutrition_action == "ANALYZE_PRODUCTS":
                        logger.info("Executing ANALYZE_PRODUCTS action based on agentic decision")
                        products_to_analyze = state.get("retrieved_products", [])
                        if products_to_analyze:
                            tool_params = {"shopping_list": products_to_analyze}
                            try:
                                nutrition_analysis = await analyze_nutrition_profile.ainvoke(tool_params)
                                log_tool_usage("analyze_nutrition_profile", tool_params, nutrition_analysis)
                                
                                if nutrition_analysis.get("error"):
                                    actions_taken.append("❌ Unable to analyze nutrition of found products")
                                else:
                                    new_state["recommendations"].append({
                                        "type": "nutrition_analysis",
                                        "analysis": nutrition_analysis,
                                        "reason": "Nutritional breakdown of found products"
                                    })
                                    actions_taken.append(f"🥗 Analyzed nutrition of {len(products_to_analyze)} found products")
                                    logger.info(f"Successfully analyzed nutrition for {len(products_to_analyze)} products")
                            except Exception as e:
                                log_tool_usage("analyze_nutrition_profile", tool_params, error=str(e))
                                logger.error(f"Failed to analyze product nutrition: {e}")
                                actions_taken.append("❌ Unable to analyze product nutrition due to technical error")
                        else:
                            actions_taken.append("⚠️ No products found to analyze - try searching for specific items")
                    
                    elif nutrition_action == "HEALTH_RECOMMENDATIONS":
                        logger.info("Executing HEALTH_RECOMMENDATIONS action based on agentic decision")
                        dietary_restrictions = state.get("user_profile", {}).get("dietary_restrictions", [])
                        new_state["recommendations"].append({
                            "type": "health_recommendations",
                            "suggestions": [
                                "Add more fruits and vegetables to your diet",
                                "Include lean proteins for muscle health",
                                "Choose whole grains over refined grains",
                                "Stay hydrated with plenty of water"
                            ],
                            "dietary_considerations": dietary_restrictions,
                            "reason": "General health and nutrition recommendations"
                        })
                        actions_taken.append("💚 Generated personalized health recommendations")
                        logger.info("Provided health-focused recommendations")
                    
                    elif nutrition_action == "DIETARY_CHECK":
                        logger.info("Executing DIETARY_CHECK action based on agentic decision")
                        dietary_restrictions = state.get("user_profile", {}).get("dietary_restrictions", [])
                        if dietary_restrictions:
                            items_to_check = state.get("retrieved_products", []) or new_state.get("shopping_list", [])
                            if items_to_check:
                                # Use existing dietary filter tool to check compatibility
                                tool_params = {"products": items_to_check, "restrictions": dietary_restrictions}
                                try:
                                    filtered_products = await filter_products_by_dietary_restrictions.ainvoke(tool_params)
                                    compatible_count = len(filtered_products)
                                    total_count = len(items_to_check)
                                    incompatible_count = total_count - compatible_count
                                    
                                    if incompatible_count > 0:
                                        actions_taken.append(f"⚠️ Found {incompatible_count} items that may not meet your dietary needs")
                                    else:
                                        actions_taken.append(f"✅ All {total_count} items are compatible with your dietary restrictions")
                                    logger.info(f"Dietary compatibility check: {compatible_count}/{total_count} items compatible")
                                except Exception as e:
                                    logger.error(f"Failed dietary check: {e}")
                                    actions_taken.append("❌ Unable to check dietary compatibility")
                            else:
                                actions_taken.append("⚠️ No items to check against your dietary restrictions")
                        else:
                            actions_taken.append("📝 No dietary restrictions set in your profile")
                    
                    elif nutrition_action == "NUTRITION_EDUCATION":
                        logger.info("Executing NUTRITION_EDUCATION action based on agentic decision")
                        actions_taken.append("📚 Added nutrition education to recommendations")
                        new_state["recommendations"].append({
                            "type": "nutrition_education",
                            "topics": [
                                "Understanding macronutrients (proteins, carbs, fats)",
                                "Importance of micronutrients and vitamins",
                                "Reading nutrition labels effectively",
                                "Building balanced meals"
                            ],
                            "reason": "Nutrition education and awareness"
                        })
                        logger.info("Provided nutrition education content")
                    
                    else:  # NO_ACTION, FALLBACK, or unknown
                        logger.info(f"No specific nutrition action needed for decision: {nutrition_action}")
                        actions_taken.append("🥗 Ready to help with your nutrition questions")
                
                elif intent in ["comparison"]:
                    logger.info("Processing product comparison intent with agentic decision making")
                    
                    # Use LLM to determine specific comparison needs
                    comparison_action_prompt = f"""
                    Analyze this user message about product comparison and determine what they specifically want:
                    
                    User message: "{state["current_message"]}"
                    Found products: {len(state.get("retrieved_products", []))} items
                    User dietary restrictions: {state.get("user_profile", {}).get("dietary_restrictions", [])}
                    User budget: {state.get("user_profile", {}).get("budget_limit", "not set")}
                    
                    Respond with ONLY one of these actions:
                    - FIND_ALTERNATIVES: if they want alternatives to specific products
                    - PRICE_COMPARISON: if they want to compare prices of similar items
                    - FEATURE_COMPARISON: if they want to compare features/specs
                    - BRAND_COMPARISON: if they want to compare different brands
                    - DIETARY_ALTERNATIVES: if they want alternatives that meet dietary needs
                    - NO_ACTION: if no specific comparison is needed
                    """
                    
                    comparison_action = await self._make_agentic_decision(comparison_action_prompt)
                    
                    # Execute determined comparison action
                    if comparison_action in ["FIND_ALTERNATIVES", "DIETARY_ALTERNATIVES", "BRAND_COMPARISON"]:
                        logger.info(f"Executing {comparison_action} action based on agentic decision")
                        if state.get("retrieved_products"):
                            alternatives_found = 0
                            for product in state["retrieved_products"][:2]:  # Compare top 2 products
                                product_name = product.get("name", "")
                                if product_name:
                                    dietary_restrictions = state.get("user_profile", {}).get("dietary_restrictions", []) if comparison_action == "DIETARY_ALTERNATIVES" else []
                                    
                                    tool_params = {
                                        "product_name": product_name, 
                                        "dietary_restrictions": dietary_restrictions
                                    }
                                    try:
                                        alternatives = await find_product_alternatives.ainvoke(tool_params)
                                        log_tool_usage("find_product_alternatives", tool_params, alternatives)
                                        
                                        if alternatives and not any(alt.get("error") for alt in alternatives):
                                            alternatives_found += len([alt for alt in alternatives if not alt.get("error")])
                                            comparison_type = "dietary-friendly" if comparison_action == "DIETARY_ALTERNATIVES" else "brand" if comparison_action == "BRAND_COMPARISON" else "general"
                                            new_state["recommendations"].append({
                                                "type": "alternatives",
                                                "original_product": product,
                                                "alternatives": alternatives,
                                                "reason": f"{comparison_type.title()} alternatives for comparison"
                                            })
                                            logger.info(f"Successfully found alternatives for {product_name}")
                                        else:
                                            logger.warning(f"No alternatives found for {product_name}")
                                    except Exception as e:
                                        log_tool_usage("find_product_alternatives", tool_params, error=str(e))
                                        logger.error(f"Failed to find alternatives for {product_name}: {e}")
                            
                            if alternatives_found > 0:
                                actions_taken.append(f"🔍 Found {alternatives_found} alternative products for comparison")
                            else:
                                actions_taken.append("⚠️ No suitable alternatives found for your products")
                        else:
                            actions_taken.append("⚠️ No products found to compare - try searching for specific items first")
                    
                    elif comparison_action == "PRICE_COMPARISON":
                        logger.info("Executing PRICE_COMPARISON action based on agentic decision")
                        if state.get("retrieved_products"):
                            products = state["retrieved_products"]
                            # Sort by price for comparison
                            priced_products = [p for p in products if p.get("price") is not None]
                            if priced_products:
                                priced_products.sort(key=lambda x: x.get("price", 0))
                                lowest_price = priced_products[0].get("price", 0)
                                highest_price = priced_products[-1].get("price", 0)
                                price_range = highest_price - lowest_price
                                
                                new_state["recommendations"].append({
                                    "type": "price_comparison",
                                    "products": priced_products,
                                    "price_range": price_range,
                                    "lowest_price": lowest_price,
                                    "highest_price": highest_price,
                                    "reason": "Price comparison of found products"
                                })
                                actions_taken.append(f"💰 Price comparison: ${lowest_price:.2f} - ${highest_price:.2f} (range: ${price_range:.2f})")
                                logger.info(f"Generated price comparison for {len(priced_products)} products")
                            else:
                                actions_taken.append("⚠️ No pricing information available for comparison")
                        else:
                            actions_taken.append("⚠️ No products found for price comparison")
                    
                    elif comparison_action == "FEATURE_COMPARISON":
                        logger.info("Executing FEATURE_COMPARISON action based on agentic decision")
                        if state.get("retrieved_products"):
                            products = state["retrieved_products"][:3]  # Compare top 3
                            new_state["recommendations"].append({
                                "type": "feature_comparison",
                                "products": products,
                                "features": ["price", "rating", "brand", "category"],
                                "reason": "Feature comparison of selected products"
                            })
                            actions_taken.append(f"📊 Generated feature comparison for {len(products)} products")
                            logger.info(f"Generated feature comparison for {len(products)} products")
                        else:
                            actions_taken.append("⚠️ No products found for feature comparison")
                    
                    else:  # NO_ACTION, FALLBACK, or unknown
                        logger.info(f"No specific comparison action needed for decision: {comparison_action}")
                        actions_taken.append("🔍 Ready to help you compare products")
                
                new_state["actions_taken"] = actions_taken
                new_state["reasoning_step"] = "action_execution"
                
                logger.info(f"Action execution completed. {len(actions_taken)} actions taken: {actions_taken}")
                new_state = self._add_thought(new_state, f"Completed {len(actions_taken)} actions")
                return new_state
                
            except Exception as e:
                logger.error(f"Error during action execution: {e}")
                state = self._add_thought(state, f"Error executing actions: {str(e)}")
                new_state = dict(state)
                new_state["actions_taken"] = ["Error occurred during action execution"]
                return new_state
        
        async def generate_recommendations(state: ShoppingAssistantState) -> ShoppingAssistantState:
            """Generate personalized recommendations based on context and executed actions."""
            state = self._add_thought(state, "Generating personalized recommendations")
            
            try:
                new_state = dict(state)
                # If we don't have recommendations from actions, generate basic ones
                if not state.get("recommendations"):
                    recommendations = []
                    
                    # Create recommendations from retrieved products
                    for product in state.get("retrieved_products", [])[:3]:
                        recommendations.append({
                            "type": "product_recommendation",
                            "product": product,
                            "reason": f"Matches your search for '{state['search_query']}'"
                        })
                    
                    new_state["recommendations"] = recommendations
                
                new_state = self._add_thought(new_state, f"Generated {len(new_state.get('recommendations', []))} recommendations")
                return new_state
                
            except Exception as e:
                state = self._add_thought(state, f"Error generating recommendations: {str(e)}")
                new_state = dict(state)
                if not new_state.get("recommendations"):
                    new_state["recommendations"] = []
                return new_state
        
        def formulate_response(state: ShoppingAssistantState) -> ShoppingAssistantState:
            """Generate final response with recommendations and actions taken."""
            state = self._add_thought(state, "Formulating final response")
            
            try:
                # Format chat history for context
                chat_history_text = ""
                if state.get("chat_history"):
                    history_items = []
                    for msg in state["chat_history"][-6:]:  # Last 6 messages for context
                        role = "User" if msg.get("role") == "user" else "Assistant"
                        content = msg.get("content", "")
                        history_items.append(f"{role}: {content}")
                    chat_history_text = "\n".join(history_items)
                
                # Prepare context for response generation
                context = {
                    "user_id": state.get("user_id", ""),
                    "user_profile": json.dumps(state.get("user_profile", {})),
                    "chat_history": chat_history_text,
                    "current_message": state.get("current_message", ""),
                    "current_intent": state.get("current_intent", ""),
                    "search_strategy": state.get("search_strategy", "simple_search"),
                    "is_dish_request": state.get("is_dish_request", False),
                    "primary_search": state.get("primary_search", ""),
                    "secondary_searches": json.dumps(state.get("secondary_searches", [])),
                    "retrieved_products": json.dumps(state.get("retrieved_products", [])[:3]),
                    "shopping_list": json.dumps(state.get("shopping_list", [])),
                    "agent_thoughts": "\n".join(state.get("agent_thoughts", [])),
                    "actions_taken": json.dumps(state.get("actions_taken", []))
                }
                
                # Generate response using LLM
                logger.info("LLM API call: Response generation for user message.")
                response = self.llm.invoke(
                    self.response_prompt.format_messages(**context)
                )
                
                new_state = dict(state)
                new_state["final_response"] = response.content
                new_state["reasoning_step"] = "response_generation"
                
                new_state = self._add_thought(new_state, "Response generated successfully")
                return new_state
                
            except Exception as e:
                state = self._add_thought(state, f"Error formulating response: {str(e)}")
                new_state = dict(state)
                new_state["final_response"] = "I apologize, but I encountered an error. Please try again."
                return new_state
        
        def route_by_intent(state: ShoppingAssistantState) -> str:
            """Route to appropriate node based on detected intent."""
            intent = state.get("current_intent", "general_chat")
            
            # All intents go through product discovery first except general chat
            if intent in ["product_discovery", "comparison", "meal_planning"]:
                return "discover_products"
            else:
                return "execute_actions"
        
        def route_after_discovery(state: ShoppingAssistantState) -> str:
            """Route after product discovery to execute actions."""
            return "execute_actions"
        
        # Build the graph
        workflow = StateGraph(ShoppingAssistantState)
        
        # Add nodes
        workflow.add_node("analyze_intent", analyze_user_intent)
        workflow.add_node("discover_products", discover_products)
        workflow.add_node("execute_actions", execute_actions)
        workflow.add_node("generate_recommendations", generate_recommendations)
        workflow.add_node("formulate_response", formulate_response)
        
        # Define workflow
        workflow.set_entry_point("analyze_intent")
        
        # Add conditional routing from intent analysis
        workflow.add_conditional_edges(
            "analyze_intent",
            route_by_intent,
            {
                "discover_products": "discover_products",
                "execute_actions": "execute_actions"
            }
        )
        
        # Connect discovery to actions
        workflow.add_edge("discover_products", "execute_actions")
        workflow.add_edge("execute_actions", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "formulate_response")
        
        # End at response formulation
        workflow.add_edge("formulate_response", END)
        
        return workflow.compile()
    
    async def chat(self, user_message: str, user_id: str = "default_user", 
                   user_profile: Optional[Dict] = None, 
                   chat_history: Optional[List[Dict]] = None,
                   recent_products: Optional[List[Dict]] = None,
                   conversation_context: Optional[ConversationState] = None) -> Dict[str, Any]:
        """
        Main chat interface for the shopping assistant.
        
        Args:
            user_message: The user's message
            user_id: Unique identifier for the user
            user_profile: User's profile and preferences
            chat_history: Previous conversation history
            recent_products: Products from recent searches
            conversation_context: CRITICAL - Persistent conversation context for "add those" functionality
            
        Returns:
            Dictionary containing the response and agent thoughts
        """
        session_start = datetime.now()
        logger.info(f"=== CHAT SESSION START ===")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Message: {user_message}")
        logger.info(f"Chat history length: {len(chat_history) if chat_history else 0}")
        logger.info(f"User profile provided: {bool(user_profile)}")
        
        # CRITICAL FIX: Reuse existing conversation context or create new one
        if conversation_context is None:
            conversation_context = ConversationState()
            logger.info("Created new conversation context")
        else:
            logger.info(f"Reusing conversation context with {len(conversation_context.last_products)} products")
        
        # Initialize state with conversation history and recent products
        initial_state = ShoppingAssistantState(
            user_id=user_id,
            user_profile=user_profile or {},
            chat_history=chat_history or [],
            current_message=user_message,
            shopping_list=[],
            current_intent="",
            search_query="",
            retrieved_products=recent_products or [],  # Start with recent products from session
            agent_thoughts=[],
            reasoning_step="",
            recommendations=[],
            actions_taken=[],
            api_responses=[],
            final_response="",
            conversation_context=conversation_context  # FIXED: Use persistent context
        )
        
        print(f"\n🛒 Walmart Shopping Assistant")
        print(f"👤 User: {user_message}")
        print(f"🔄 Processing...")
        
        try:
            logger.info("Starting agent workflow execution")
            # Run the agent workflow
            final_state = await self.agent_graph.ainvoke(initial_state)
            
            session_duration = (datetime.now() - session_start).total_seconds()
            logger.info(f"Agent workflow completed in {session_duration:.2f} seconds")
            logger.info(f"Final intent: {final_state.get('current_intent', 'unknown')}")
            logger.info(f"Products found: {len(final_state.get('retrieved_products', []))}")
            logger.info(f"Actions taken: {len(final_state.get('actions_taken', []))}")
            logger.info(f"Recommendations: {len(final_state.get('recommendations', []))}")
            
            print(f"🤖 Assistant: {final_state['final_response']}")
            
            result = {
                "response": final_state["final_response"],
                "products": final_state.get("retrieved_products", []),
                "recommendations": final_state.get("recommendations", []),
                "actions_taken": final_state.get("actions_taken", []),
                "agent_thoughts": final_state["agent_thoughts"],
                "intent": final_state.get("current_intent", ""),
                "chat_history": final_state.get("chat_history", []) + [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": final_state["final_response"]}
                ],
                "conversation_context": final_state.get("conversation_context"),  # CRITICAL: Return context
                "success": True
            }
            
            logger.info(f"=== CHAT SESSION END (SUCCESS) === Duration: {session_duration:.2f}s")
            return result
            
        except Exception as e:
            session_duration = (datetime.now() - session_start).total_seconds()
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            logger.error(f"Chat session failed after {session_duration:.2f}s: {e}")
            logger.error(f"=== CHAT SESSION END (ERROR) === Duration: {session_duration:.2f}s")
            print(f"❌ Error: {error_msg}")
            
            return {
                "response": error_msg,
                "products": [],
                "recommendations": [],
 "actions_taken": ["Error occurred during processing"],
                "agent_thoughts": ["Error occurred during processing"],
                "intent": "error",
                "success": False
            }
    
    def chat_sync(self, user_message: str, user_id: str = "default_user", 
                  user_profile: Optional[Dict] = None, 
                  chat_history: Optional[List[Dict]] = None,
                  recent_products: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Synchronous wrapper for the chat method."""
        return asyncio.run(self.chat(user_message, user_id, user_profile, chat_history, recent_products))


# Example usage and testing
async def main():
    """Test the shopping assistant with various scenarios."""
    assistant = WalmartShoppingAssistant()
    
    # Test scenarios
    test_scenarios = [
        {
            "message": "Hi! I'm looking for healthy snacks for my kids.",
            "user_profile": {
                "dietary_restrictions": ["no nuts"],
                "budget_limit": 50.0,
                "family_size": 4
            }
        },
        {
            "message": "I need ingredients for a quick pasta dinner tonight.",
            "user_profile": {
                "dietary_restrictions": ["vegetarian"],
                "cooking_skill": "beginner"
            }
        },
        {
            "message": "What gaming consoles do you have for under $300?",
            "user_profile": {
                "age_range": "teen",
                "budget_limit": 300.0
            }
        }
    ]
    
    print("🚀 Testing Walmart Shopping Assistant")
    print("=" * 60)
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📝 Test Scenario {i}:")
        print(f"Message: {scenario['message']}")
        print(f"Profile: {scenario['user_profile']}")
        print("-" * 60)
        
        result = await assistant.chat(
            scenario["message"],
            user_id=f"test_user_{i}",
            user_profile=scenario["user_profile"]
        )
        
        print(f"✅ Success: {result['success']}")
        print(f"🎯 Intent: {result['intent']}")
        print(f"📦 Products Found: {len(result['products'])}")
        print(f"💡 Recommendations: {len(result['recommendations'])}")
        
        if result["recommendations"]:
            for rec in result["recommendations"]:
                product = rec.get('product', {})
                print(f"   • {product.get('name', 'Unknown')} - ${product.get('price', 'N/A')}")
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
