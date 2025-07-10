"""
LangGraph Shopping Assistant - Core Agent Implementation
A sophisticated AI shopping assistant that uses RAG and user preferences 
to provide personalized Walmart shopping experiences.
"""

import warnings
import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime

warnings.filterwarnings("ignore", category=DeprecationWarning)

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
            ("system", """You are an intelligent intent classifier for a shopping assistant. 
            Analyze the user's message and conversation context to determine their primary intent.
            
            Available intents:
            - product_discovery: Looking for products, ingredients, or asking what's available
            - shopping_list_management: Adding/removing/viewing items in cart/list
            - meal_planning: Planning meals, recipes, or meal prep
            - budget_analysis: Questions about spending or budget optimization
            - nutrition_analysis: Health-focused queries or dietary needs
            - general_chat: Greetings, thanks, casual conversation
            - comparison: Comparing products or requesting alternatives
            
            CONTEXT AWARENESS:
            - If conversation shows recent product recommendations and user says referential terms like "add those", "add them", "the mario ones" -> shopping_list_management
            - If user mentions specific dishes/meals they want to make -> product_discovery (they need ingredients)
            - If user asks about their spending or budget -> budget_analysis
            - If user wants to plan meals for the week -> meal_planning
            
            Analyze the INTENT behind the message, not just keywords.
            Respond with ONLY the intent name, no explanation."""),
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
        async def analyze_user_intent(state: ShoppingAssistantState) -> ShoppingAssistantState:
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

                # Use LLM to determine if this is a contextual add request
                contextual_analysis_prompt = f"""
                Analyze this user message to determine if they're referring to items from recent conversation:
                
                Message: "{state['current_message']}"
                Chat History: {chat_history_text}
                Context Score: {context_score:.2f}
                
                Look for phrases that indicate they want to add previously discussed items:
                - References like "those", "these", "them", "the ones we talked about"
                - Adding phrases like "add", "put in cart", "I'll take"
                - Contextual references to ingredients, items, or products mentioned earlier
                
                Respond with:
                - "CONTEXTUAL_ADD" if they're clearly referring to previous items
                - "NEW_REQUEST" if this is a new request
                - "UNCLEAR" if ambiguous
                """
                
                contextual_decision = await self._make_agentic_decision(contextual_analysis_prompt)
                is_contextual_add = contextual_decision == "CONTEXTUAL_ADD"
                
                if is_contextual_add:
                    new_state = self._add_thought(new_state, f"LLM detected contextual add request with context score {context_score:.2f}")

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
                    new_state = self._add_thought(new_state, f"Context override: LLM detected contextual add with score {context_score:.2f}")

                # Validate intent classification
                valid_intents = ["product_discovery", "shopping_list_management", "meal_planning",
                               "budget_analysis", "nutrition_analysis", "general_chat", "comparison"]
                
                if intent not in valid_intents:
                    # Use LLM for fallback classification instead of hardcoded patterns
                    fallback_prompt = f"""
                    The initial classification failed. Re-analyze this message for shopping intent:
                    Message: "{state['current_message']}"
                    
                    Choose the BEST intent from: {', '.join(valid_intents)}
                    
                    Consider:
                    - Are they asking for products/items? -> product_discovery
                    - Are they managing their cart/list? -> shopping_list_management  
                    - Are they planning meals? -> meal_planning
                    - Are they asking about money/budget? -> budget_analysis
                    - General conversation? -> general_chat
                    
                    Respond with ONLY the intent name.
                    """
                    
                    try:
                        fallback_intent = await self._make_agentic_decision(fallback_prompt)
                        if fallback_intent.lower() in valid_intents:
                            intent = fallback_intent.lower()
                            new_state = self._add_thought(new_state, f"Fallback classification: {intent}")
                        else:
                            intent = "general_chat"
                            new_state = self._add_thought(new_state, "Defaulting to general_chat")
                    except Exception as e:
                        logger.error(f"Fallback intent classification failed: {e}")
                        intent = "general_chat"
                        new_state = self._add_thought(new_state, f"Intent classification error, defaulting to general_chat")
                
                # Update state
                new_state["current_intent"] = intent
                new_state["reasoning_step"] = "intent_analysis"
                
                new_state = self._add_thought(new_state, f"Final intent: {intent}")
                
                # Intelligently determine search query
                if intent in ["product_discovery", "comparison", "meal_planning"]:
                    new_state["search_query"] = state["current_message"]
                elif intent == "shopping_list_management" and not new_state.get("search_query"):
                    # For list management, we might not need a new search
                    new_state["search_query"] = ""
                
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
                
                # Use LLM to assess query complexity and determine search strategy
                complexity_prompt = f"""
                Analyze this shopping query for complexity and determine the best search strategy:
                
                Query: "{query}"
                User dietary restrictions: {dietary_restrictions}
                
                Is this:
                1. SIMPLE: A single product/category request (e.g., "find snacks", "laptop")
                2. COMPLEX: A dish/meal that needs multiple ingredients (e.g., "chicken salad ingredients", "pasta dinner")
                
                For COMPLEX queries, identify:
                - Main ingredient/component
                - Supporting ingredients needed
                
                Respond in this format:
                TYPE: SIMPLE or COMPLEX
                MAIN: [primary item to search for]
                SUPPORTING: [item1, item2, item3] (only for COMPLEX)
                """
                
                try:
                    complexity_analysis = await self._make_agentic_decision(complexity_prompt)
                    logger.info(f"Query complexity analysis: {complexity_analysis}")
                    
                    is_complex = "COMPLEX" in complexity_analysis
                    
                    if not is_complex:
                        # Simple product search
                        state = self._add_thought(state, "Simple query - direct search approach")
                        
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
                            return new_state
                    
                    else:
                        # Complex query analysis and decomposition
                        state = self._add_thought(state, "Complex query - using multi-step search approach")
                        
                        # Parse complexity analysis for main and supporting items
                        main_item = query  # fallback
                        supporting_items = []
                        
                        try:
                            for line in complexity_analysis.split('\n'):
                                if line.startswith('MAIN:'):
                                    main_item = line.replace('MAIN:', '').strip()
                                elif line.startswith('SUPPORTING:'):
                                    supporting_text = line.replace('SUPPORTING:', '').strip()
                                    if supporting_text and supporting_text != '[]':
                                        # Clean up the parsing - remove brackets and split properly
                                        supporting_text = supporting_text.replace('[', '').replace(']', '')
                                        supporting_items = [item.strip() for item in supporting_text.split(',') if item.strip()]
                        except Exception as e:
                            logger.warning(f"Could not parse complexity analysis: {e}, using fallback")
                        
                        # Execute searches
                        all_products = []
                        search_log = []
                        
                        # Search for main item
                        if main_item:
                            main_params = {"query": main_item, "max_results": 5}
                            try:
                                main_products = await search_products_semantic.ainvoke(main_params)
                                log_tool_usage("search_products_semantic (main)", main_params, main_products)
                                all_products.extend(main_products)
                                search_log.append(f"Main: {main_item}")
                                logger.info(f"Main search '{main_item}' found {len(main_products)} products")
                            except Exception as e:
                                log_tool_usage("search_products_semantic (main)", main_params, error=str(e))
                                logger.error(f"Main search failed: {e}")
                        
                        # Search for supporting items
                        for item in supporting_items[:3]:  # Limit to 3 supporting items
                            if item:
                                support_params = {"query": item, "max_results": 2}
                                try:
                                    support_products = await search_products_semantic.ainvoke(support_params)
                                    log_tool_usage("search_products_semantic (support)", support_params, support_products)
                                    all_products.extend(support_products)
                                    search_log.append(f"Support: {item}")
                                    logger.info(f"Support search '{item}' found {len(support_products)} products")
                                except Exception as e:
                                    log_tool_usage("search_products_semantic (support)", support_params, error=str(e))
                                    logger.error(f"Support search for '{item}' failed: {e}")
                        
                        # Remove duplicates and limit results
                        unique_products = []
                        seen_ids = set()
                        for product in all_products:
                            prod_id = product.get("id")
                            if prod_id and prod_id not in seen_ids:
                                unique_products.append(product)
                                seen_ids.add(prod_id)
                        
                        new_state = dict(state)
                        new_state["retrieved_products"] = unique_products[:Config.MAX_PRODUCTS_TO_RETRIEVE]
                        new_state["search_strategy"] = "complex_multi_search"
                        new_state["is_dish_request"] = True
                        new_state["primary_search"] = main_item
                        new_state["secondary_searches"] = search_log
                        
                        # Update conversation context
                        if new_state.get("conversation_context"):
                            new_state["conversation_context"].update_products(unique_products, state.get("current_intent", ""))
                            new_state = self._add_thought(new_state, f"Updated context with {len(unique_products)} products from multi-search")
                        
                        logger.info(f"Complex search completed: {len(unique_products)} unique products found")
                
                except Exception as e:
                    logger.error(f"Error in complexity analysis: {e}")
                    # Fallback to simple search
                    state = self._add_thought(state, "Complexity analysis failed, using simple search")
                    
                    try:
                        simple_params = {"query": query, "max_results": Config.MAX_PRODUCTS_TO_RETRIEVE}
                        simple_products = await search_products_semantic.ainvoke(simple_params)
                        
                        new_state = dict(state)
                        new_state["retrieved_products"] = simple_products
                        new_state["search_strategy"] = "fallback_simple_search"
                        new_state["is_dish_request"] = False
                        new_state["primary_search"] = query
                        new_state["secondary_searches"] = []
                        
                        if new_state.get("conversation_context"):
                            new_state["conversation_context"].update_products(simple_products, state.get("current_intent", ""))
                    except Exception as fallback_error:
                        logger.error(f"Fallback search also failed: {fallback_error}")
                        new_state = dict(state)
                        new_state["retrieved_products"] = []
                
                # Apply user preference filters if products were found
                if new_state.get("retrieved_products"):
                    filtered_products = new_state["retrieved_products"]
                    
                    # Apply dietary restrictions filter if specified
                    if dietary_restrictions:
                        try:
                            filter_params = {"products": filtered_products, "restrictions": dietary_restrictions}
                            filtered_products = await filter_products_by_dietary_restrictions.ainvoke(filter_params)
                            log_tool_usage("filter_products_by_dietary_restrictions", filter_params, filtered_products)
                            new_state = self._add_thought(new_state, f"Applied dietary filters: {dietary_restrictions}")
                        except Exception as e:
                            logger.error(f"Dietary filtering failed: {e}")
                    
                    # Apply budget filter if specified  
                    if budget_limit:
                        try:
                            budget_params = {"products": filtered_products, "max_budget": budget_limit}
                            filtered_products = await filter_products_by_budget.ainvoke(budget_params)
                            log_tool_usage("filter_products_by_budget", budget_params, filtered_products)
                            new_state = self._add_thought(new_state, f"Applied budget filter: ${budget_limit}")
                        except Exception as e:
                            logger.error(f"Budget filtering failed: {e}")
                    
                    new_state["retrieved_products"] = filtered_products

                logger.info("Product discovery completed.")
                new_state = self._add_thought(new_state, f"Product discovery complete: {len(new_state.get('retrieved_products', []))} final products")
                return new_state
                
            except Exception as e:
                logger.error(f"Error in product discovery: {e}")
                error_state = dict(state)
                error_state["retrieved_products"] = []
                error_state = self._add_thought(error_state, f"Product discovery failed: {str(e)}")
                return error_state
        
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
                    if state.get("chat_history"):
                        history_items = []
                        for msg in state["chat_history"][-6:]:  # Last 6 messages for context
                            role = "User" if msg.get("role") == "user" else "Assistant"
                            content = msg.get("content", "")
                            history_items.append(f"{role}: {content}")
                        
                        chat_history_text = "\n".join(history_items)
                    
                    # Enhanced LLM decision making with better context understanding
                    shopping_action_prompt = f"""
                    Analyze this user message and recent conversation to determine what shopping list action they want:
                    
                    Recent conversation history:
                    {chat_history_text}
                    
                    Current user message: "{state["current_message"]}"
                    Current shopping list has: {len(new_state["shopping_list"])} items
                    Available products from current search: {len(state.get("retrieved_products", []))} items
                    
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
                    - ADD_CONTEXTUAL_PRODUCTS: if they want to add items from recent conversation/search results
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
                    
                    elif shopping_action == "ADD_CONTEXTUAL_PRODUCTS":
                        logger.info("Executing ADD_CONTEXTUAL_PRODUCTS action with intelligent product selection")
                        
                        # Use LLM to intelligently determine which products to add based on context
                        context_products = new_state.get("retrieved_products", [])
                        conversation_products = []
                        
                        # Get products from conversation context if available
                        if new_state.get("conversation_context") and new_state["conversation_context"].has_valid_context():
                            conversation_products = new_state["conversation_context"].get_contextual_products()
                        
                        # Combine available products
                        all_available_products = context_products + conversation_products
                        
                        # Remove duplicates by ID
                        seen_ids = set()
                        unique_products = []
                        for product in all_available_products:
                            product_id = product.get("id")
                            if product_id and product_id not in seen_ids:
                                unique_products.append(product)
                                seen_ids.add(product_id)
                        
                        if unique_products:
                            # Use LLM to intelligently select which products to add
                            product_selection_prompt = f"""
                            The user said: "{state['current_message']}"
                            
                            They are asking for specific items. Available products from recent searches:
                            {chr(10).join([f"- {p.get('name', 'Unknown')} (ID: {p.get('id', 'no-id')}, Category: {p.get('category', 'Unknown')})" for p in unique_products[:15]])}
                            
                            IMPORTANT: Only select products that ACTUALLY match what the user is asking for.
                            
                            User wants: {state['current_message']}
                            
                            Look for products that contain the actual items they mentioned:
                            - If they said "oatmeal", only select oatmeal products
                            - If they said "bananas", only select banana products  
                            - If they said "chicken", only select chicken products
                            - Do NOT select random or unrelated items
                            
                            Respond with a JSON array of product IDs that ACTUALLY match their request: ["id1", "id2"]
                            If NO products match what they specifically asked for, respond with: []
                            
                            Be strict - better to return [] than wrong products.
                            """
                            
                            try:
                                selection_response = await self._make_agentic_decision(product_selection_prompt)
                                logger.info(f"LLM product selection response: {selection_response}")
                                
                                # Parse the JSON response more robustly
                                import json
                                import re
                                try:
                                    # Extract JSON array from response
                                    json_match = re.search(r'\[.*?\]', selection_response)
                                    if json_match:
                                        selected_ids = json.loads(json_match.group())
                                    elif selection_response.strip() == '[]':
                                        selected_ids = []
                                    else:
                                        # If no JSON found, try to extract product IDs mentioned in text
                                        selected_ids = []
                                        for product in unique_products:
                                            product_id = product.get('id', '')
                                            product_name = product.get('name', '').lower()
                                            user_message_lower = state['current_message'].lower()
                                            
                                            # Check if this product name contains words from user message
                                            user_words = [word for word in user_message_lower.split() if len(word) > 3]
                                            if any(word in product_name for word in user_words):
                                                selected_ids.append(product_id)
                                                break  # Only take first match to avoid random additions
                                except (json.JSONDecodeError, AttributeError) as e:
                                    logger.error(f"Failed to parse LLM selection response: {e}")
                                    selected_ids = []  # Don't add random products on parse failure
                                
                                # Find selected products
                                products_to_add = []
                                for product in unique_products:
                                    if product.get('id') in selected_ids:
                                        products_to_add.append(product)
                                
                                if products_to_add:
                                    actions_taken.append(f"🧠 Intelligently selected {len(products_to_add)} products based on our conversation")
                                    logger.info(f"LLM selected {len(products_to_add)} products for addition")
                                else:
                                    # Enhanced fallback: Use LLM to extract specific items mentioned by user
                                    logger.info("LLM selection was empty, using LLM to extract specific items mentioned")
                                    
                                    item_extraction_prompt = f"""
                                    The user said: "{state['current_message']}"
                                    
                                    Recent conversation context:
                                    {chat_history_text}
                                    
                                    The user is asking to add items to their cart. Based on the conversation context and their request:
                                    
                                    1. If they mention "other ingredients" or "additional ingredients", look at what dish/meal they were discussing
                                    2. If they previously mentioned making a specific dish (like "chicken salad"), suggest the missing ingredients for that dish
                                    3. Extract specific grocery items they explicitly mention
                                    
                                    For common dishes, suggest these ingredients:
                                    - Chicken salad: mayonnaise, celery, bread
                                    - Pasta dish: pasta sauce, cheese, seasonings
                                    - Breakfast: eggs, milk, bread, butter
                                    - Sandwich: bread, condiments, vegetables
                                    
                                    Return as a JSON list of specific search terms:
                                    ["item1", "item2", "item3"]
                                    
                                    Examples:
                                    - If they previously mentioned "chicken salad" and now say "add other ingredients" -> ["mayonnaise", "celery", "bread"]
                                    - "add oatmeal and bananas" -> ["oatmeal", "bananas"]
                                    - "I need pasta with meatballs and beans" -> ["pasta with meatballs", "baked beans"]
                                    
                                    If the request is too vague and no dish context is available, return: ["ingredients"]
                                    """
                                    
                                    try:
                                        extraction_response = await self._make_agentic_decision(item_extraction_prompt)
                                        logger.info(f"LLM item extraction response: {extraction_response}")
                                        
                                        # Parse the JSON response
                                        import json
                                        import re
                                        
                                        # Clean up the response and extract JSON
                                        clean_response = extraction_response.strip()
                                        json_match = re.search(r'\[.*?\]', clean_response, re.DOTALL)
                                        
                                        if json_match:
                                            try:
                                                extracted_items = json.loads(json_match.group())
                                                logger.info(f"Successfully extracted items: {extracted_items}")
                                            except json.JSONDecodeError:
                                                # Fallback: split by common separators
                                                extracted_items = [item.strip() for item in clean_response.replace('[', '').replace(']', '').replace('"', '').split(',')]
                                                extracted_items = [item for item in extracted_items if item and len(item) > 1]
                                        else:
                                            # Last resort: extract from original message
                                            extracted_items = []
                                            user_message_lower = state["current_message"].lower()
                                            
                                            # Look for food-related patterns
                                            if "pasta" in user_message_lower and "meatball" in user_message_lower:
                                                extracted_items.append("pasta with meatballs")
                                            elif "pasta" in user_message_lower:
                                                extracted_items.append("pasta")
                                            
                                            if "bean" in user_message_lower:
                                                if "baked" in user_message_lower:
                                                    extracted_items.append("baked beans")
                                                else:
                                                    extracted_items.append("beans")
                                            
                                            # Add other common items
                                            food_keywords = ["oatmeal", "oats", "banana", "bananas", "milk", "bread", "eggs", "chicken", "rice", "yogurt"]
                                            for keyword in food_keywords:
                                                if keyword in user_message_lower:
                                                    extracted_items.append(keyword)
                                        
                                        if extracted_items:
                                            # Search for each extracted item
                                            logger.info(f"Searching for extracted items: {extracted_items}")
                                            for item in extracted_items[:4]:  # Limit to avoid too many searches
                                                try:
                                                    search_params = {"query": item, "max_results": 2}
                                                    item_results = await search_products_semantic.ainvoke(search_params)
                                                    if item_results:
                                                        # Add the best match for each item
                                                        best_match = item_results[0]  # Take the top result
                                                        products_to_add.append(best_match)
                                                        logger.info(f"Found item: {best_match.get('name')} for request: {item}")
                                                except Exception as e:
                                                    logger.error(f"Failed to search for item '{item}': {e}")
                                            
                                            if products_to_add:
                                                actions_taken.append(f"🔍 Found {len(products_to_add)} specific items you mentioned")
                                            else:
                                                actions_taken.append("⚠️ Could not find the specific items you mentioned. Please try being more specific.")
                                        else:
                                            actions_taken.append("⚠️ Could not identify specific items to add. Please specify what you'd like to add to your cart.")
                                    
                                    except Exception as e:
                                        logger.error(f"Error in item extraction: {e}")
                                        actions_taken.append("⚠️ Could not understand what items to add. Please try again with specific product names.")
                                
                            except Exception as e:
                                logger.error(f"Error in intelligent product selection: {e}")
                                # Fallback to heuristic selection
                                if new_state.get("is_dish_request"):
                                    products_to_add = unique_products[:6]
                                    actions_taken.append(f"🍽️ Adding ingredients for your dish (fallback selection)")
                                else:
                                    products_to_add = unique_products[:3]
                                    actions_taken.append(f"🛒 Adding products from search results (fallback selection)")
                        else:
                            actions_taken.append("⚠️ No products found from recent conversation to add. Please search for items first.")
                            products_to_add = []
                        
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
                    
                    Look carefully at the specific meal they want to plan:
                    - "plan a breakfast" or "breakfast meal" -> BREAKFAST_PLAN (just breakfast)
                    - "plan a lunch" or "lunch meal" -> LUNCH_PLAN (just lunch)  
                    - "plan a dinner" or "dinner meal" -> DINNER_PLAN (just dinner)
                    - "plan meals for the week" or "weekly meal plan" -> FULL_MEAL_PLAN (multiple days/meals)
                    - "meal prep" or "prep meals" -> MEAL_PREP
                    - "quick recipe" or "what can I make" -> QUICK_RECIPE
                    - mentions specific dietary needs -> DIETARY_MEALS
                    - wants ingredients for specific dish -> INGREDIENT_LIST
                    
                    Respond with ONLY one of these actions:
                    - BREAKFAST_PLAN: for single breakfast planning
                    - LUNCH_PLAN: for single lunch planning
                    - DINNER_PLAN: for single dinner planning
                    - FULL_MEAL_PLAN: for complete weekly meal planning
                    - QUICK_RECIPE: if they need a quick recipe for today/tonight
                    - INGREDIENT_LIST: if they want ingredients for a specific dish
                    - DIETARY_MEALS: if they want meals that fit specific dietary needs
                    - MEAL_PREP: if they want meal prep suggestions
                    - NO_ACTION: if no specific meal planning action is needed
                    """
                    
                    meal_action = await self._make_agentic_decision(meal_action_prompt)
                    
                    # Execute determined meal planning action
                    if meal_action in ["BREAKFAST_PLAN", "LUNCH_PLAN", "DINNER_PLAN"]:
                        logger.info(f"Executing {meal_action} action based on agentic decision")
                        
                        # For specific meal planning, use the products we already found during discovery
                        available_products = state.get("retrieved_products", [])
                        if available_products:
                            # Filter products to be appropriate for the requested meal
                            meal_type = meal_action.replace("_PLAN", "").lower()
                            
                            # Create a focused meal plan recommendation
                            new_state["recommendations"].append({
                                "type": "single_meal_plan",
                                "meal_type": meal_type,
                                "ingredients": available_products,
                                "reason": f"Personalized {meal_type} ingredients based on your request"
                            })
                            
                            # Store the meal plan products for potential shopping list addition
                            new_state["retrieved_products"] = available_products
                            
                            actions_taken.append(f"🍽️ Created {meal_type} meal plan with {len(available_products)} ingredients")
                            actions_taken.append(f"📋 Found {len(available_products)} ingredients you can add to your shopping list")
                            logger.info(f"Successfully created {meal_type} meal plan with {len(available_products)} ingredients")
                        else:
                            actions_taken.append(f"⚠️ No suitable ingredients found for {meal_type} planning")
                    
                    elif meal_action in ["FULL_MEAL_PLAN", "MEAL_PREP", "DIETARY_MEALS"]:
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
                            # Filter products to get appropriate ones for the meal type
                            products = state["retrieved_products"]
                            user_message_lower = state["current_message"].lower()
                            
                            # Smart filtering based on meal type mentioned
                            if "breakfast" in user_message_lower:
                                # Prioritize breakfast-appropriate items
                                breakfast_products = []
                                for product in products:
                                    product_name = product.get("name", "").lower()
                                    category = product.get("category", "").lower()
                                    
                                    # Look for breakfast-appropriate items
                                    if any(breakfast_term in product_name or breakfast_term in category 
                                          for breakfast_term in ["egg", "bread", "bacon", "sausage", "cereal", 
                                                               "oat", "milk", "yogurt", "fruit", "banana", "berry"]):
                                        breakfast_products.append(product)
                                
                                if breakfast_products:
                                    products = breakfast_products[:3]  # Top 3 breakfast items
                                else:
                                    products = products[:3]  # Fallback to any products
                            else:
                                products = products[:3]  # Default for non-specific requests
                            
                            product_names = [p.get("name", "unknown") for p in products]
                            meal_type = "breakfast" if "breakfast" in user_message_lower else "meal"
                            actions_taken.append(f"🍳 Found {meal_type} recipe ideas using: {', '.join(product_names)}")
                            new_state["recommendations"].append({
                                "type": "quick_recipe",
                                "ingredients": products,
                                "meal_type": meal_type,
                                "reason": f"Quick {meal_type} recipe based on available ingredients"
                            })
                            logger.info(f"Generated quick {meal_type} recipe suggestions with {len(products)} ingredients")
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
            """Intelligently route based on intent and existing context."""
            intent = state.get("current_intent", "general_chat")
            
            # Smart routing based on intent and context
            if intent in ["product_discovery", "comparison", "meal_planning"]:
                return "discover_products"
            elif intent == "shopping_list_management":
                # For shopping list management, prioritize using existing context over new discovery
                context = state.get("conversation_context")
                message = state.get("current_message", "").lower()
                
                # If we have valid conversation context and the request seems contextual, use it
                if context and context.has_valid_context():
                    # Check for contextual phrases that reference previous conversation
                    contextual_phrases = ["those", "them", "these", "it", "all", "other", "rest", "more", "additional"]
                    if any(phrase in message for phrase in contextual_phrases):
                        return "execute_actions"  # Use existing context
                
                # Check for specific new product requests that need discovery
                if any(phrase in message for phrase in ["find", "search for", "look for"]) and not any(ref in message for ref in ["those", "them", "these"]):
                    return "discover_products"
                
                # Check for viewing/management actions that don't need discovery
                if any(action in message for action in ["show", "view", "see", "list", "remove", "delete", "clear"]):
                    return "execute_actions"
                
                # Default to using context if available, otherwise discovery
                return "execute_actions" if context and context.has_valid_context() else "discover_products"
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
                "chat_history": chat_history or [],
                "conversation_context": conversation_context,  # CRITICAL: Return context even on error
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
