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
            - product_discovery: Looking for specific products or asking "what do you have"
            - shopping_list_management: Adding/removing items from shopping list
            - meal_planning: Planning meals, asking for recipes, meal prep
            - budget_analysis: Questions about spending, budget optimization
            - nutrition_analysis: Health-focused queries, dietary needs
            - general_chat: Casual conversation, greetings, general questions, follow-up responses
            - comparison: Comparing products or asking for alternatives
            
            If the user is responding to a previous question or providing additional context,
            consider the conversation history to determine the most appropriate intent.
            
            Respond with ONLY the intent name."""),
            ("human", """
            Conversation History: {chat_history}
            Current Message: {message}
            """)
        ])
        
        # Response generation prompt with conversation history
        self.response_prompt = ChatPromptTemplate.from_messages([
            ("system", Config.AGENT_PERSONALITY),
            ("human", """
            User ID: {user_id}
            User Profile: {user_profile}
            Conversation History: {chat_history}
            Current Message: {current_message}
            Intent: {current_intent}
            
            Retrieved Products: {retrieved_products}
            Current Shopping List: {shopping_list}
            Agent Thoughts: {agent_thoughts}
            Actions Taken: {actions_taken}
            
            Based on the conversation history and current context, provide a helpful and personalized response to the user.
            Be conversational, specific, and actionable. Reference previous parts of the conversation when relevant.
            If you've found products or made changes to their shopping list, mention them specifically.
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
    
    def _build_agent_graph(self) -> StateGraph:
        """Build the LangGraph workflow for the shopping assistant."""
        
        # Define all the node functions
        def analyze_user_intent(state: ShoppingAssistantState) -> ShoppingAssistantState:
            """Analyze user message to determine intent and extract key information."""
            state = self._add_thought(state, f"Analyzing user intent for: '{state['current_message']}'")
            
            try:
                # Format chat history for the prompt
                chat_history_text = ""
                if state.get("chat_history"):
                    history_items = []
                    for msg in state["chat_history"][-6:]:  # Last 6 messages for context
                        role = "User" if msg.get("role") == "user" else "Assistant"
                        content = msg.get("content", "")
                        history_items.append(f"{role}: {content}")
                    chat_history_text = "\n".join(history_items)
                
                # Use LLM to classify intent with conversation context
                logger.info("LLM API call: Intent classification for user message.")
                response = self.llm.invoke(
                    self.intent_prompt.format_messages(
                        chat_history=chat_history_text,
                        message=state["current_message"]
                    )
                )
                intent = response.content.strip().lower()
                
                # Create updated state
                new_state = dict(state)
                new_state["current_intent"] = intent
                new_state["reasoning_step"] = "intent_analysis"
                
                new_state = self._add_thought(new_state, f"Detected intent: {intent}")
                
                # Extract search query for product-related intents or continuation of meal planning
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
                return new_state
        
        async def discover_products(state: ShoppingAssistantState) -> ShoppingAssistantState:
            """Use advanced tools to find and filter relevant products."""
            query = state['search_query']
            logger.info(f"Starting product discovery for query: '{query}'")
            state = self._add_thought(state, f"Searching for products: '{query}'")
            
            try:
                # Get user preferences for filtering
                user_preferences = state.get("user_profile", {})
                dietary_restrictions = user_preferences.get("dietary_restrictions", [])
                budget_limit = user_preferences.get("budget_limit")
                
                logger.info(f"User preferences - Dietary: {dietary_restrictions}, Budget: {budget_limit}")
                
                # Perform semantic search using the tool (correct LangChain tool usage)
                search_params = {
                    "query": query,
                    "max_results": Config.MAX_PRODUCTS_TO_RETRIEVE
                }
                try:
                    raw_products = await search_products_semantic.ainvoke(search_params)
                    log_tool_usage("search_products_semantic", search_params, raw_products)
                    logger.info(f"Semantic search returned {len(raw_products)} products")
                except Exception as e:
                    log_tool_usage("search_products_semantic", search_params, error=str(e))
                    logger.error(f"Semantic search failed: {e}")
                    raw_products = []
                
                new_state = dict(state)
                new_state["retrieved_products"] = raw_products
                new_state = self._add_thought(new_state, f"Found {len(raw_products)} relevant products")
                
                # Apply dietary restrictions filtering
                if dietary_restrictions and raw_products:
                    filter_params = {
                        "products": raw_products, 
                        "restrictions": dietary_restrictions
                    }
                    try:
                        filtered_products = await filter_products_by_dietary_restrictions.ainvoke(filter_params)
                        log_tool_usage("filter_products_by_dietary_restrictions", filter_params, filtered_products)
                        new_state["retrieved_products"] = filtered_products
                        new_state = self._add_thought(new_state, f"Filtered to {len(filtered_products)} products based on dietary preferences")
                        logger.info(f"Applied dietary restrictions filter: {len(raw_products)} -> {len(filtered_products)} products")
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
                
                new_state["reasoning_step"] = "product_discovery"
                logger.info(f"Product discovery completed. Final result: {len(new_state['retrieved_products'])} products")
                return new_state
                
            except Exception as e:
                logger.error(f"Error during product discovery: {e}")
                new_state = dict(state)
                new_state["retrieved_products"] = []
                new_state = self._add_thought(new_state, f"Error during product search: {str(e)}")
                return new_state
                
                # Apply budget filtering if specified
                if budget_limit:
                    budget_filtered = await filter_products_by_budget.ainvoke({
                        "products": new_state["retrieved_products"], 
                        "max_budget": budget_limit
                    })
                    new_state["retrieved_products"] = budget_filtered
                    new_state = self._add_thought(new_state, f"Filtered to {len(budget_filtered)} products within budget")
                
                new_state["reasoning_step"] = "product_discovery"
                return new_state
                
            except Exception as e:
                state = self._add_thought(state, f"Error in product discovery: {str(e)}")
                new_state = dict(state)
                new_state["retrieved_products"] = []
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
                
                # Intent-specific actions with enhanced logging
                if intent in ["shopping_list_management"]:
                    logger.info("Processing shopping list management intent")
                    # Check if user wants to add products
                    if any(keyword in state["current_message"].lower() 
                           for keyword in ["add", "put", "include", "need"]):
                        # Add recommended products to shopping list
                        products_to_add = state.get("retrieved_products", [])[:2]  # Add top 2
                        logger.info(f"Attempting to add {len(products_to_add)} products to shopping list")
                        
                        for product in products_to_add:
                            if product.get("id"):
                                tool_params = {
                                    "user_id": user_id, 
                                    "product_id": product["id"], 
                                    "quantity": 1
                                }
                                try:
                                    result = await add_product_to_list.ainvoke(tool_params)
                                    log_tool_usage("add_product_to_list", tool_params, result)
                                    if result.get("success"):
                                        actions_taken.append(f"Added {product.get('name', 'product')} to shopping list")
                                        logger.info(f"Successfully added product {product.get('name')} to shopping list")
                                    else:
                                        logger.warning(f"Failed to add product {product.get('name')} to shopping list")
                                except Exception as e:
                                    log_tool_usage("add_product_to_list", tool_params, error=str(e))
                                    logger.error(f"Error adding product to shopping list: {e}")
                
                elif intent in ["budget_analysis"]:
                    logger.info("Processing budget analysis intent")
                    # Get spending analytics
                    tool_params = {"user_id": user_id}
                    try:
                        spending_data = await get_spending_breakdown.ainvoke(tool_params)
                        log_tool_usage("get_spending_breakdown", tool_params, spending_data)
                        if "api_responses" not in new_state:
                            new_state["api_responses"] = []
                        new_state["api_responses"].append({"spending_analytics": spending_data})
                        actions_taken.append("Retrieved spending analytics from backend")
                        logger.info("Successfully retrieved spending analytics")
                    except Exception as e:
                        log_tool_usage("get_spending_breakdown", tool_params, error=str(e))
                        logger.error(f"Failed to retrieve spending analytics: {e}")
                    
                    # Optimize shopping list if requested
                    if state.get("shopping_list"):
                        budget_limit = state.get("user_profile", {}).get("budget_limit", 100.0)
                        tool_params = {
                            "shopping_list": state["shopping_list"], 
                            "budget_limit": budget_limit
                        }
                        try:
                            optimized_list = await optimize_shopping_list_for_budget.ainvoke(tool_params)
                            log_tool_usage("optimize_shopping_list_for_budget", tool_params, optimized_list)
                            new_state["recommendations"].append({
                                "type": "budget_optimization",
                                "optimized_list": optimized_list,
                                "reason": f"Optimized for ${budget_limit} budget"
                            })
                            actions_taken.append("Generated budget-optimized shopping list")
                            logger.info(f"Successfully optimized shopping list for ${budget_limit} budget")
                        except Exception as e:
                            log_tool_usage("optimize_shopping_list_for_budget", tool_params, error=str(e))
                            logger.error(f"Failed to optimize shopping list: {e}")
                
                elif intent in ["meal_planning"]:
                    logger.info("Processing meal planning intent")
                    # Generate meal plan
                    dietary_prefs = state.get("user_profile", {}).get("dietary_restrictions", [])
                    budget = state.get("user_profile", {}).get("budget_limit", 100.0)
                    
                    tool_params = {
                        "dietary_preferences": dietary_prefs, 
                        "budget": budget, 
                        "days": 7
                    }
                    try:
                        meal_plan = await generate_meal_plan_suggestions.ainvoke(tool_params)
                        log_tool_usage("generate_meal_plan_suggestions", tool_params, meal_plan)
                        new_state["recommendations"].append({
                            "type": "meal_plan",
                            "meal_suggestions": meal_plan,
                            "reason": "Personalized meal plan based on your preferences"
                        })
                        actions_taken.append("Generated personalized meal plan")
                        logger.info(f"Successfully generated meal plan for {len(dietary_prefs)} dietary preferences")
                    except Exception as e:
                        log_tool_usage("generate_meal_plan_suggestions", tool_params, error=str(e))
                        logger.error(f"Failed to generate meal plan: {e}")
                
                elif intent in ["nutrition_analysis"]:
                    logger.info("Processing nutrition analysis intent")
                    # Analyze nutrition of current shopping list or products
                    items_to_analyze = state.get("retrieved_products", []) or state.get("shopping_list", [])
                    if items_to_analyze:
                        tool_params = {"products": items_to_analyze}
                        try:
                            nutrition_analysis = await analyze_nutrition_profile.ainvoke(tool_params)
                            log_tool_usage("analyze_nutrition_profile", tool_params, nutrition_analysis)
                            new_state["recommendations"].append({
                                "type": "nutrition_analysis",
                                "analysis": nutrition_analysis,
                                "reason": "Nutritional breakdown of your selected items"
                            })
                            actions_taken.append(f"Analyzed nutritional profile of {len(items_to_analyze)} items")
                            logger.info(f"Successfully analyzed nutrition for {len(items_to_analyze)} items")
                        except Exception as e:
                            log_tool_usage("analyze_nutrition_profile", tool_params, error=str(e))
                            logger.error(f"Failed to analyze nutrition: {e}")
                
                elif intent in ["comparison"]:
                    logger.info("Processing product comparison intent")
                    # Find alternatives for comparison
                    if state.get("retrieved_products"):
                        for product in state["retrieved_products"][:1]:  # Compare first product
                            tool_params = {
                                "product_name": product.get("name", ""), 
                                "dietary_restrictions": state.get("user_profile", {}).get("dietary_restrictions", [])
                            }
                            try:
                                alternatives = await find_product_alternatives.ainvoke(tool_params)
                                log_tool_usage("find_product_alternatives", tool_params, alternatives)
                                new_state["recommendations"].append({
                                    "type": "alternatives",
                                    "original_product": product,
                                    "alternatives": alternatives,
                                    "reason": "Alternative products for comparison"
                                })
                                actions_taken.append(f"Found alternatives for {product.get('name', 'product')}")
                                logger.info(f"Successfully found alternatives for {product.get('name')}")
                            except Exception as e:
                                log_tool_usage("find_product_alternatives", tool_params, error=str(e))
                                logger.error(f"Failed to find alternatives for {product.get('name')}: {e}")
                
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
                   chat_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Main chat interface for the shopping assistant.
        
        Args:
            user_message: The user's message
            user_id: Unique identifier for the user
            user_profile: User's profile and preferences
            chat_history: Previous conversation history
            
        Returns:
            Dictionary containing the response and agent thoughts
        """
        session_start = datetime.now()
        logger.info(f"=== CHAT SESSION START ===")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Message: {user_message}")
        logger.info(f"Chat history length: {len(chat_history) if chat_history else 0}")
        logger.info(f"User profile provided: {bool(user_profile)}")
        
        # Initialize state with conversation history
        initial_state = ShoppingAssistantState(
            user_id=user_id,
            user_profile=user_profile or {},
            chat_history=chat_history or [],
            current_message=user_message,
            shopping_list=[],
            current_intent="",
            search_query="",
            retrieved_products=[],
            agent_thoughts=[],
            reasoning_step="",
            recommendations=[],
            actions_taken=[],
            api_responses=[],
            final_response=""
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
                  chat_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Synchronous wrapper for the chat method."""
        return asyncio.run(self.chat(user_message, user_id, user_profile, chat_history))


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
