
# Walmart AI Shopping Assistant Backend

FastAPI backend with PostgreSQL and Prisma for the Personalized AI Shopping Assistant.

## Features

- **FastAPI** with async/await support
- **PostgreSQL** database with **Prisma ORM**
- **RESTful API** endpoints for products, users, shopping lists, orders, and chat
- **Analytics** endpoints for spending insights
- **CORS** enabled for frontend integration
- **Data ingestion** script with sample data

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- PostgreSQL database
- Node.js (for Prisma)

### 2. Environment Setup

```bash
# Clone and navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Update .env file with your PostgreSQL connection string
DATABASE_URL="postgresql://username:password@localhost:5432/walmart_ai"

# Install Prisma CLI
npm install -g prisma

# Generate Prisma client
prisma generate

# Run database migrations
prisma db push
```

### 4. Data Ingestion

```bash
# Run the data ingestion script
python run_ingest.py
```

This will:
- Load products from `data/products.csv`
- Create a demo user with comprehensive profile
- Generate sample shopping lists, orders, and chat messages

### 5. Start the Server

```bash
# Development mode
python -m app.main

# Or with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API Endpoints

### Products
- `GET /api/products` - List all products
- `GET /api/products/{id}` - Get single product
- `POST /api/products` - Create product
- `PUT /api/products/{id}` - Update product
- `DELETE /api/products/{id}` - Delete product

### Users
- `GET /api/users/{user_id}` - Get user with profile
- `PUT /api/users/{user_id}` - Update user

### Shopping List
- `GET /api/users/{user_id}/shopping-list` - Get shopping list
- `POST /api/users/{user_id}/shopping-list` - Add to list
- `DELETE /api/users/{user_id}/shopping-list/{item_id}` - Remove item

### Orders
- `GET /api/orders/{id}` - Get order
- `GET /api/users/{user_id}/orders` - Get user orders
- `POST /api/orders` - Create order

### Analytics
- `GET /api/users/{user_id}/analytics/spending` - Spending by category

### Chat
- `GET /api/chat/history` - Get chat history
- `POST /api/chat` - Create chat message

## Sample Requests

### Add to Shopping List
```bash
curl -X POST "http://localhost:8000/api/users/david123/shopping-list" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "prod_123", "quantity": 2}'
```

### Create Order
```bash
curl -X POST "http://localhost:8000/api/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "david123",
    "items": [
      {"product_id": "prod_123", "quantity": 2},
      {"product_id": "prod_456", "quantity": 1}
    ]
  }'
```

### Get Analytics
```bash
curl "http://localhost:8000/api/users/david123/analytics/spending"
```

## Database Schema

The database includes these main models:
- **Product**: Store inventory with pricing and stock status
- **User**: Customer profiles with JSON-stored preferences
- **ShoppingListItem**: User's current shopping list
- **Order**: Purchase history with item details
- **ChatMessage**: Conversation history with AI assistant

## Development

### Database Migrations

```bash
# After schema changes
prisma db push

# Generate new client
prisma generate
```

### Adding New Endpoints

1. Define Pydantic schemas in `app/schemas.py`
2. Add endpoint logic in `app/main.py`
3. Update this README with new endpoint documentation

## Production Deployment

1. Set production environment variables
2. Use a production WSGI server like Gunicorn
3. Set up proper database connection pooling
4. Configure logging and monitoring
5. Set up SSL/TLS termination

```bash
# Production server example
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
