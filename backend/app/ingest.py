import asyncio
import pandas as pd
import os
from dotenv import load_dotenv
from .database import get_prisma
import json


load_dotenv()


DEMO_USER_PROFILE = {
    "user_id": "david123",
    "name": "David",
    "persona_summary": "Health-conscious professional who values convenience and quality. Prefers organic options when available and enjoys cooking at home.",
    "explicit_preferences": {
        "dietary_restrictions": ["low-sodium"],
        "preferred_brands": ["Great Value", "Tyson", "Tropicana"],
        "shopping_frequency": "weekly",
        "budget_range": "moderate",
        "preferred_shopping_time": "evening"
    },
    "implicit_insights": {
        "frequently_bought_categories": ["Produce", "Meat", "Dairy"],
        "price_sensitivity": "medium",
        "brand_loyalty": "moderate",
        "impulse_buying_tendency": "low",
        "seasonal_preferences": {
            "summer": ["fresh fruits", "beverages"],
            "winter": ["comfort foods", "hot beverages"]
        }
    },
    "purchase_history_summary": {
        "total_orders": 24,
        "average_order_value": 67.50,
        "favorite_products": [
            {"name": "Tyson Chicken Breast", "frequency": 18},
            {"name": "Great Value Milk", "frequency": 20},
            {"name": "Bananas", "frequency": 22}
        ],
        "spending_by_category": {
            "Produce": 180.50,
            "Meat": 245.75,
            "Dairy": 125.25,
            "Snacks": 89.50,
            "Drinks": 67.25
        }
    },
    "transaction_log": [
        {
            "date": "2024-01-15",
            "items": ["Chicken Breast", "Milk", "Bananas"],
            "total": 18.74,
            "notes": "Weekly grocery run"
        },
        {
            "date": "2024-01-08",
            "items": ["Greek Yogurt", "Apples", "Orange Juice"],
            "total": 14.94,
            "notes": "Healthy breakfast items"
        }
    ]
}

async def load_products_from_csv():
    """Load products from CSV file into database."""
    print("Loading products from CSV...")
    
    
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "products.csv")
    df = pd.read_csv(csv_path)
    
   
    db = await get_prisma()
    
   
    await db.product.delete_many()
    print("Cleared existing products")
    
    
    products_created = 0
    for _, row in df.iterrows():
        try:
         
            await db.product.create(
                data={
                    "name": row["name"],
                    "brand": row["brand"] if pd.notna(row["brand"]) else None,
                    "averageRating": float(row["averageRating"]) if pd.notna(row["averageRating"]) else None,
                    "shortDescription": row["shortDescription"] if pd.notna(row["shortDescription"]) else None,
                    "thumbnailUrl": row["thumbnailUrl"] if pd.notna(row["thumbnailUrl"]) else None,
                    "price": float(row["price"]),
                    "currencyUnit": row["currencyUnit"] if pd.notna(row["currencyUnit"]) else "USD",
                    "category": row["category"],
                    "aisle": row["aisle"],
                    "availability": row["availability"] if pd.notna(row["availability"]) else "in-stock"
                }
            )
            products_created += 1
        except Exception as e:
            print(f"Error creating product {row['name']}: {e}")
    
    print(f"Created {products_created} products")
    return products_created

async def create_demo_user():
    """Create demo user with profile."""
    print("Creating demo user...")
    
    db = await get_prisma()
    
   
    existing_user = await db.user.find_unique(where={"email": "david@example.com"})
    if existing_user:
        print("Demo user already exists, updating profile...")
        await db.user.update(
            where={"id": existing_user.id},
            data={
                "name": "David",
                "profile": json.dumps(DEMO_USER_PROFILE)
            }
        )
        return existing_user.id
    
    
    demo_user = await db.user.create(
        data={
            "name": "David",
            "email": "david@example.com",
            "profile": json.dumps(DEMO_USER_PROFILE)
        }
    )
    
   
    profile_data = demo_user.profile
    print(f"Demo user created with ID: {profile_data}")

    print(f"Created demo user with ID: {demo_user.id}")
    return demo_user.id

async def create_sample_data(user_id: str):
    """Create sample shopping list and orders for demo user."""
    print("Creating sample data...")
    
    db = await get_prisma()
    
    
    products = await db.product.find_many(take=5)
    if not products:
        print("No products found, skipping sample data creation")
        return
    
    
    await db.shoppinglistitem.delete_many(where={"userId": user_id})
    await db.order.delete_many(where={"userId": user_id})
    await db.chatmessage.delete_many(where={"userId": user_id})
    
    
    for i, product in enumerate(products[:3]):
        await db.shoppinglistitem.create(
            data={
                "userId": user_id,
                "productId": product.id,
                "quantity": i + 1
            }
        )
    
    print("Created sample shopping list")
    
    
    sample_orders = [
        {
            "items": [
                {
                    "productId": products[0].id, 
                    "quantity": 2, 
                    "price": products[0].price, 
                    "name": products[0].name,
                    "brand": products[0].brand,
                    "thumbnailUrl": products[0].thumbnailUrl
                },
                {
                    "productId": products[1].id, 
                    "quantity": 1, 
                    "price": products[1].price, 
                    "name": products[1].name,
                    "brand": products[1].brand,
                    "thumbnailUrl": products[1].thumbnailUrl
                }
            ],
            "total": products[0].price * 2 + products[1].price
        },
        {
            "items": [
                {
                    "productId": products[2].id, 
                    "quantity": 3, 
                    "price": products[2].price, 
                    "name": products[2].name,
                    "brand": products[2].brand,
                    "thumbnailUrl": products[2].thumbnailUrl
                }
            ],
            "total": products[2].price * 3
        }
    ]
    
    for order_data in sample_orders:
        await db.order.create(
            data={
                "userId": user_id,
                "items": json.dumps(order_data["items"]),
                "total": order_data["total"]
            }
        )
    
    print("Created sample orders")
    
    
    sample_messages = [
        {"content": "Hi, I need help planning my groceries.", "isUser": True},
        {"content": "Of course! What meals are you planning this week?", "isUser": False},
        {"content": "I want to make chicken stir fry and need ingredients.", "isUser": True},
        {"content": "Great choice! I can help you find chicken breast, vegetables, and sauce. Let me add those to your list.", "isUser": False}
    ]
    
    for msg in sample_messages:
        await db.chatmessage.create(
            data={
                "userId": user_id,
                "content": msg["content"],
                "isUser": msg["isUser"]
            }
        )
    
    print("Created sample chat messages")

async def main():
    """Main ingestion function."""
    print("Starting data ingestion...")
    
    try:
        
        # await load_products_from_csv()
        
        user_id = await create_demo_user()
        
       
        await create_sample_data(user_id)
        
        print("Data ingestion completed successfully!")
        
    except Exception as e:
        print(f"Error during data ingestion: {e}")
        raise
    
    finally:
       
        from .database import disconnect_prisma
        await disconnect_prisma()

if __name__ == "__main__":
    asyncio.run(main())