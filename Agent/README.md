# Walmart Shopping Assistant Agent

A sophisticated LangGraph-powered AI shopping assistant that provides personalized shopping experiences for Walmart customers using RAG (Retrieval-Augmented Generation) and advanced reasoning capabilities.

## 🏗️ Architecture

The assistant is built using:
- **LangGraph**: For complex workflow orchestration and multi-step reasoning
- **ChromaDB**: For semantic product search and RAG capabilities
- **FastAPI**: For backend integration and API endpoints
- **Gemini**: For natural language understanding and generation

## 🚀 Features

### Core Capabilities
- **Intelligent Product Discovery**: Semantic search through Walmart's product catalog
- **Personalized Recommendations**: Based on user preferences, dietary restrictions, and budget
- **Shopping List Management**: Add, remove, and optimize shopping lists
- **Meal Planning**: Generate weekly meal plans with shopping lists
- **Budget Optimization**: Suggest alternatives and optimize costs
- **Nutrition Analysis**: Analyze nutritional balance of shopping choices
- **Multi-turn Conversations**: Maintain context across chat sessions

### Advanced Workflows
- **Intent Classification**: Understand what users want (product search, meal planning, etc.)
- **Multi-step Reasoning**: Complex decision making across multiple nodes
- **Tool Integration**: Seamless integration with backend APIs and databases
- **Preference Learning**: Adapt to user preferences over time

## 📁 Project Structure

```
Agent/
├── shopping_assistant.py      # Core LangGraph agent implementation
├── shopping_tools.py          # Tools for backend/RAG integration
├── config.py                  # Configuration and settings
├── agent_api.py               # FastAPI wrapper for frontend integration
├── query_products.py          # ChromaDB product search utilities
├── ingest_products.py         # Data ingestion for ChromaDB
├── pyproject.toml             # Dependencies and project metadata
├── uv.lock                    # Dependency lock file
├── requirements.txt           # Python dependencies
├── README.md                  # This documentation
├── .env                       # Environment variables (create this)
├── .gitignore                 # Git ignore rules
└── chroma_db/                 # ChromaDB vector database
```

## 🛠️ Setup and Installation

### Prerequisites
- Python 3.12+
- GEMINI API key
- Access to the backend API (FastAPI + PostgreSQL)
- ChromaDB with ingested product data

### Installation

1. **Install dependencies using uv:**
```bash
cd Agent
uv sync
```

2. **Set up environment variables:**
Create a `.env` file in the Agent directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
BACKEND_BASE_URL=http://localhost:8000
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

3. **Initialize ChromaDB with product data:**
```bash
uv run python ingest_products.py
```

## 🎯 Usage


### API Interface

Start the FastAPI server for frontend integration:

```bash
uv run python agent_api.py
```

The API will be available at:
- **Base URL**: `http://localhost:8001`
- **Interactive docs**: `http://localhost:8001/docs`

**Key endpoints:**
- `POST /chat` - Main chat interface
- `GET /user/{user_id}/profile` - Get user profile
- `GET /user/{user_id}/shopping-list` - Get shopping list
- `POST /meal-plan/generate` - Generate meal plans
- `GET /search/products` - Search products


## 🧠 Agent Architecture

### State Schema
The agent maintains rich state throughout the conversation:

```python
class ShoppingAssistantState(TypedDict):
    # User context
    user_id: str
    user_profile: Dict[str, Any]
    chat_history: List[Dict[str, Any]]
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
```

### Workflow Graph
The agent uses a multi-node workflow:

1. **Analyze Intent** → Classify user intent and extract key information
2. **Discover Products** → Search ChromaDB for relevant products
3. **Execute Actions** → Perform intent-specific actions (add to list, get analytics)
4. **Generate Recommendations** → Create personalized suggestions
5. **Formulate Response** → Generate natural language response

### Available Tools
- `search_products_semantic` - Semantic product search
- `get_user_shopping_list` - Retrieve shopping list
- `add_product_to_list` - Add items to shopping list
- `get_user_preferences` - Get user profile
- `get_spending_breakdown` - Analytics and insights
- `generate_meal_plan_suggestions` - Meal planning
- `analyze_nutrition_profile` - Nutrition analysis
- `find_product_alternatives` - Product comparisons
- `optimize_shopping_list_for_budget` - Budget optimization

## 🔄 Integration with Backend

The agent integrates seamlessly with the existing FastAPI backend:


### Database Integration
The agent works with your existing:
- User profiles and preferences
- Shopping lists and history
- Product catalog and pricing
- Order history and analytics

## 🎨 Frontend Integration

### React Frontend
The agent API is designed to work with the existing React frontend:


### WebSocket Support (Future)
For real-time chat experiences, WebSocket support can be added to the API.


## API Testing
Use the FastAPI docs interface at `http://localhost:8001/docs` for API testing.

## 🔧 Configuration

### Environment Variables
```env
# Required
GEMINI_API_KEY=your_gemini_api_key

# Optional (with defaults)
BACKEND_BASE_URL=http://localhost:8000
CHROMA_PERSIST_DIRECTORY=./chroma_db
GEMINI_API_KEY=your_gemini_api_key
DEFAULT_TEMPERATURE=0.7
MAX_PRODUCTS_TO_RETRIEVE=10
```

### Customization
Modify `config.py` to adjust:
- Agent personality and prompts
- Search parameters
- Model settings
- API endpoints

## 📊 Performance Considerations

- **Caching**: ChromaDB provides efficient vector caching
- **Async**: All operations are asynchronous for better performance
- **Streaming**: Supports streaming responses for real-time UX
- **Rate Limiting**: Built-in Gemini rate limiting handling

## 🚀 Deployment

### Production Deployment
1. Set up environment variables
2. Deploy ChromaDB with product data
3. Configure backend API endpoints
4. Deploy the agent API using Docker or cloud services

### Docker Deployment
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
CMD ["uv", "run", "python", "agent_api.py"]
```

## 📄 License

This project is part of the Walmart Sparkathon submission.

## 🆘 Troubleshooting

### Common Issues

**ChromaDB not initialized:**
```bash
uv run python ingest_products.py
```

**Missing Gemini API key:**
```bash
export GEMINI_API_KEY=your_gemini_api_key_here
```

**Backend API not accessible:**
- Check backend is running on correct port
- Verify `BACKEND_BASE_URL` in config

**Agent not responding:**
- Check Gemini API key validity and quota
- Ensure all dependencies are installed (`uv sync`)
- Review error logs in the console for stack traces
- Confirm backend and ChromaDB services are running
- Verify network connectivity between agent and backend

### Getting Help

For issues with the agent:
1. Check the error logs in the console
2. Verify all environment variables are set
3. Check the ChromaDB data is properly ingested

---

**Built with ❤️ for Walmart Sparkathon 2025**