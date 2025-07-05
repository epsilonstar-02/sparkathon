# ChromaDB Vector Database for Product RAG

A production-ready ChromaDB setup for ingesting product data and enabling Retrieval-Augmented Generation (RAG) applications.

## Overview

This system provides semantic search capabilities for product data using ChromaDB vector embeddings, designed to complement your PostgreSQL backend for RAG applications.

- **PostgreSQL** (backend): Structured data, transactions, user management
- **ChromaDB** (Agent): Vector embeddings, semantic search, RAG context

## Quick Start

### 1. Install Dependencies
```bash
cd Agent
uv sync
```

### 2. Ingest Products
```bash
uv run python ingest_products.py
```

### 3. Test Search
```bash
uv run python query_products.py
```

### 4. Test RAG
```bash
uv run python rag_demo.py
```

## Files

- `ingest_products.py` - Ingests products into ChromaDB with embeddings
- `query_products.py` - Interactive search interface
- `rag_demo.py` - RAG workflow demonstration
- `chroma_db/` - Vector database (created after ingestion)

## Usage

### Search Products
```python
from query_products import ProductSearcher

searcher = ProductSearcher()
results = searcher.search("gaming console", n_results=5)
```

### RAG Integration
```python
from rag_demo import ProductRAG

rag = ProductRAG()
context = rag.retrieve_context("gaming console for kids")
prompt = rag.generate_response_prompt("gaming console for kids", context)
# Send prompt to your LLM API
```

### Backend Integration
```python
# In your FastAPI routes
from Agent.query_products import ProductSearcher

searcher = ProductSearcher("../Agent/chroma_db")

@app.get("/api/search/semantic")
async def semantic_search(query: str):
    results = searcher.search(query, n_results=10)
    return {"products": results}
```

## Data Structure

Each product contains:
- **Text**: Combined product name, brand, category, description
- **Metadata**: ID, category, brand, price, rating, availability

## Integration Architecture

```
User Query → ChromaDB Search → Retrieve Context → LLM Prompt → Response
```

## Performance

- Ingestion: ~1 minute for 694 products
- Search: <1 second per query
- Model: `all-MiniLM-L6-v2` embeddings

## Setup and Installation

### Prerequisites
- Python 3.12+
- UV package manager

### Installation

1. Install dependencies using UV:
```bash
uv sync
```

2. Run the data ingestion:
```bash
uv run python ingest.py
```

## What the Script Does

The `ingest.py` script will:

1. **Load Data**: Read `Walmart_data_cleaned.csv` containing product information
2. **Clean Data**: Handle missing values and validate required fields
3. **Generate Embeddings**: Create vector embeddings using the all-MiniLM-L6-v2 model from Hugging Face
4. **Populate SQL Database**: Create `walmart_products.db` with structured product data
5. **Populate Vector Database**: Create `chroma_db/` directory with semantic embeddings
6. **Verify**: Ensure both databases are properly populated

## Output Files

After running `python ingest.py`, you'll have:

- `walmart_products.db` - SQLite database with product information
- `chroma_db/` - ChromaDB directory with vector embeddings

## Database Schema

### SQLite (`walmart_products.db`)
- **products** table with columns:
  - id, keyword, page, position, type, name, brand
  - average_rating, short_description, thumbnail_url
  - price, currency_unit, created_at

### ChromaDB (`chroma_db/`)
- **Collection**: `walmart_products`
- **Metadata**: Includes category, brand, name, price, rating for efficient filtering
- **Documents**: Combined product information for semantic search

## Usage in API

The databases are ready for use in an API server that can:
- Perform semantic search using ChromaDB
- Filter by category directly in ChromaDB metadata
- Query structured data using SQLite
- Combine both for hybrid search capabilities

## Categories Available

The dataset includes products from categories like:
- Canned & Jarred Foods (Beans, Meats, Vegetables)
- Electronics (Tablets, Cell Phones, Laptops)
- Furniture (Sofas, Loveseats, Sectionals)
- Gaming (Video Game Consoles, Handheld Games)
- Appliances (Refrigerators, Ceiling Fans)