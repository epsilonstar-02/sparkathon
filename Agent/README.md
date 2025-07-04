# Product Data Ingestion System

This project processes Walmart product data and creates both vector and SQL databases for efficient search and retrieval.

## Features

- **Vector Database**: ChromaDB with semantic search capabilities using all-MiniLM-L6-v2 embeddings
- **SQL Database**: SQLite for structured data queries and filtering
- **Category Filtering**: ChromaDB metadata includes categories for efficient filtering
- **Batch Processing**: Efficient processing of large datasets

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