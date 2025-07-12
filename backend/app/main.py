from fastapi import FastAPI, HTTPException, Depends,UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# OpenAI Whisper (ensure it's installed: pip install openai-whisper)
from gtts import gTTS  # Google TTS (pip install gTTS)
from fastapi.responses import FileResponse, JSONResponse
import tempfile
import whisper
import httpx


from .database import get_db, disconnect_prisma
from .schemas import (
    Product, ProductCreate, ProductUpdate,
    User, UserCreate, UserUpdate, UserWithRelations,
    ShoppingListItem, ShoppingListItemCreate,
    Order, OrderCreate, OrderItem,
    ChatMessage, ChatMessageCreate,
    SpendingAnalytics, StatusResponse
)


# Check if FFmpeg is installed
# import subprocess
# try:
#     subprocess.run(["ffmpeg", "-version"], check=True)
#     print("FFmpeg is installed and working!")
# except Exception as e:
#     print("FFmpeg not found:", e)

# Load environment variables
load_dotenv()


#new added 
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup
    await get_db()
    yield
    # Runs on shutdown
    await disconnect_prisma()


# Create FastAPI app
app = FastAPI(
    title="Walmart AI Shopping Assistant API",
    description="Backend API for personalized AI shopping assistant",
    version="1.0.0",
    lifespan=lifespan
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Add this middleware to force CORS headers
@app.middleware("http")
async def add_cors_header(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:5173"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Walmart AI Shopping Assistant API is running"}

# Product endpoints
# @app.get("/api/products", response_model=List[Product])
# async def get_products(skip: int = 0, limit: int = 100,db=Depends(get_db)):
#     """Get all products."""
#     products = await db.product.find_many(order={"createdAt": "desc"},skip=skip,
#         take=min(limit, 500))
#     return products
@app.get("/api/products", response_model=List[Product])
async def get_products(ids: str = None, skip: int = 0, limit: int = 100, db=Depends(get_db)):
    """Get products with optional filtering by IDs"""
    if ids:
        id_list = ids.split(',')
        products = await db.product.find_many(
            where={"id": {"in": id_list}},
            skip=skip,
            take=min(limit, 500)
        )
    else:
        products = await db.product.find_many(
            order={"createdAt": "desc"},
            skip=skip,
            take=min(limit, 500)
        )
    return products

@app.get("/api/products/{product_id}", response_model=Product)
async def get_product(product_id: str, db=Depends(get_db)):
    """Get a single product by ID."""
    product = await db.product.find_unique(where={"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/api/products", response_model=Product)
async def create_product(product: ProductCreate, db=Depends(get_db)):
    """Create a new product."""
    created_product = await db.product.create(data=product.model_dump())
    return created_product

@app.put("/api/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product: ProductUpdate, db=Depends(get_db)):
    """Update a product."""
    existing_product = await db.product.find_unique(where={"id": product_id})
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    updated_product = await db.product.update(
        where={"id": product_id},
        data=product.model_dump()
    )
    return updated_product

@app.delete("/api/products/{product_id}", response_model=StatusResponse)
async def delete_product(product_id: str, db=Depends(get_db)):
    """Delete a product."""
    existing_product = await db.product.find_unique(where={"id": product_id})
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await db.product.delete(where={"id": product_id})
    return StatusResponse(status="success", message="Product deleted successfully")

# User endpoints
@app.get("/api/users/{user_id}", response_model=UserWithRelations)
async def get_user(user_id: str, db=Depends(get_db)):
    """Get user with profile, orders, and shopping list."""
    user = await db.user.find_unique(
        where={"id": user_id},
        include={
            "shoppingList": {
                "include": {"product": True},
                "order_by": {"addedAt": "desc"}
            },
            "orders": {"order_by": {"createdAt": "desc"}}
        }
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/api/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_update: UserUpdate, db=Depends(get_db)):
    """Update user information."""
    existing_user = await db.user.find_unique(where={"id": user_id})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {k: v for k, v in user_update.model_dump().items() if v is not None}
    updated_user = await db.user.update(
        where={"id": user_id},
        data=update_data
    )
    return updated_user

# Shopping List endpoints
@app.get("/api/users/{user_id}/shopping-list", response_model=List[ShoppingListItem])
async def get_shopping_list(user_id: str, db=Depends(get_db)):
    """Get user's shopping list with product details."""
    shopping_list = await db.shoppinglistitem.find_many(
        where={"userId": user_id},
        include={"product": True},
        order={"addedAt": "desc"}
    )
    return shopping_list

@app.post("/api/users/{user_id}/shopping-list", response_model=ShoppingListItem)
async def add_to_shopping_list(user_id: str, item: ShoppingListItemCreate, db=Depends(get_db)):
    """Add item to shopping list."""
    # Check if user exists
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if product exists
    product = await db.product.find_unique(where={"id": item.productId})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if item already exists in shopping list
    existing_item = await db.shoppinglistitem.find_first(
        where={"userId": user_id, "productId": item.productId}
    )
    
    if existing_item:
        # Update quantity if item already exists
        updated_item = await db.shoppinglistitem.update(
            where={"id": existing_item.id},
            data={"quantity": existing_item.quantity + item.quantity},
            include={"product": True}
        )
        return updated_item
    else:
        # Create new item
        new_item = await db.shoppinglistitem.create(
            data={
                "userId": user_id,
                "productId": item.productId,
                "quantity": item.quantity
            },
            include={"product": True}
        )
        return new_item

@app.delete("/api/users/{user_id}/shopping-list/{item_id}", response_model=StatusResponse)
async def remove_from_shopping_list(user_id: str, item_id: str, db=Depends(get_db)):
    """Remove item from shopping list."""
    item = await db.shoppinglistitem.find_unique(where={"id": item_id})
    if not item or item.userId != user_id:
        raise HTTPException(status_code=404, detail="Shopping list item not found")
    
    await db.shoppinglistitem.delete(where={"id": item_id})
    return StatusResponse(status="success", message="Item removed from shopping list")

# Order endpoints
@app.get("/api/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, db=Depends(get_db)):
    """Get order by ID."""
    order = await db.order.find_unique(where={"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/users/{user_id}/orders", response_model=List[Order])
async def get_user_orders(user_id: str, db=Depends(get_db)):
    """Get all orders for a user."""
    orders = await db.order.find_many(
        where={"userId": user_id},
        order={"createdAt": "desc"}
    )
    return orders

@app.post("/api/orders", response_model=Order)
async def create_order(order: OrderCreate, db=Depends(get_db)):
    """Create a new order."""
    # Check if user exists
    user = await db.user.find_unique(where={"id": order.userId})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate total and validate products
    total = 0.0
    items_data = []
    
    for item in order.items:
        product = await db.product.find_unique(where={"id": item.productId})
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.productId} not found")
        
        if product.availability == "out-of-stock":
            raise HTTPException(status_code=400, detail=f"Product {product.name} is out of stock")
        
        item_total = product.price * item.quantity
        total += item_total
        
        items_data.append({
            "productId": item.productId,
            "quantity": item.quantity,
            "price": product.price,
            "name": product.name,
            "brand": product.brand,
            "thumbnailUrl": product.thumbnailUrl,
            "currencyUnit": product.currencyUnit
        })
    
    # Create order
    created_order = await db.order.create(
        data={
            "userId": order.userId,
            "items": items_data,
            "total": total
        }
    )
    
    return created_order

# Analytics endpoints
@app.get("/api/users/{user_id}/analytics/spending", response_model=Dict[str, float])
async def get_spending_analytics(user_id: str, db=Depends(get_db)):
    """Get spending analytics by category for a user."""
    # Get all orders for the user
    orders = await db.order.find_many(where={"userId": user_id})
    
    # Calculate spending by category
    spending_by_category = {}
    
    for order in orders:
        items = order.items
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    product_id = item.get("productId")
                    quantity = item.get("quantity", 1)
                    price = item.get("price", 0)
                    
                    # Get product to find category
                    product = await db.product.find_unique(where={"id": product_id})
                    if product:
                        category = product.category
                        item_total = price * quantity
                        
                        if category in spending_by_category:
                            spending_by_category[category] += item_total
                        else:
                            spending_by_category[category] = item_total
    
    return spending_by_category

# Chat endpoints
@app.get("/api/chat/history", response_model=List[ChatMessage])
async def get_chat_history(user_id: str = None, db=Depends(get_db)):
    """Get chat history. If user_id provided, get for specific user."""
    if user_id:
        messages = await db.chatmessage.find_many(
            where={"userId": user_id},
            order={"timestamp": "asc"}
        )
    else:
        messages = await db.chatmessage.find_many(order={"timestamp": "desc"})
    
    return messages

@app.post("/api/chat", response_model=ChatMessage)
async def create_chat_message(message: ChatMessageCreate, db=Depends(get_db)):
    """Create a new chat message."""
    # Check if user exists
    user = await db.user.find_unique(where={"id": message.userId})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    created_message = await db.chatmessage.create(
        data={
            "userId": message.userId,
            "content": message.content,
            "isUser": message.isUser
        }
    )
    
    return created_message

# Speech-to-Speech Interaction
import base64
import subprocess

def convert_to_wav(input_path: str) -> str:
    output_path = input_path.replace('.webm', '.wav')
    subprocess.run(["ffmpeg", "-y", "-i", input_path, output_path], check=True)
    return output_path


model = whisper.load_model("base", device="cpu") 
def transcribe_audio(file_path: str) -> str:
    result = model.transcribe(file_path)
    return result["text"]


def generate_tts_audio(text: str) -> str:
    tts = gTTS(text=text, lang='en')
    tts_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    tts.save(tts_path)
    return tts_path

import time
@app.post("/api/talk")
async def talk(
    audio: UploadFile = File(...),
    userId: str = Form(...),
    db = Depends(get_db) 
):
    print(f"Received audio: {audio.filename}, size: {audio.size}")
    print(f"User ID: {userId}")
    # Save uploaded audio to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        audio_bytes = await audio.read()
        temp_audio.write(audio_bytes)
        webm_path = temp_audio.name

    try:
         # Step 2: Convert to WAV
        wav_path = convert_to_wav(webm_path)

        # 1. STT
        text = transcribe_audio(wav_path).strip()
        userId = userId.strip()

        print("Transcribed:", text)
        print("User ID cleaned:", userId)

        if not text:
            raise HTTPException(status_code=400, detail="Transcription returned empty text.")
        if not userId:
            raise HTTPException(status_code=400, detail="Missing userId.")

        print("Saving message with:", {"userId": userId, "content": text})

        try:
            async with httpx.AsyncClient(timeout=100.0) as client:
               
                chat_payload = {
                    "message": text,      # Agent expects "message" not "content"
                    "user_id": userId     # Agent expects "user_id" not "userId"
                }
                start_time = time.time()
                chat_response = await client.post("http://localhost:8001/chat", json=chat_payload)
                print(f"Agent response time: {time.time() - start_time:.2f}s")
                print(f"Agent status: {chat_response.status_code}")
                if chat_response.status_code != 200:
                    print("Agent API error:", chat_response.status_code)
                    print("Agent API response body:", await chat_response.text())
                    raise HTTPException(status_code=chat_response.status_code, detail="Agent response failed")
                reply_data = chat_response.json()
                reply_text = reply_data.get("response", "").strip()
                print(f"Agent response: {reply_data}")

            if not reply_text:
                reply_text = "Sorry, I couldn't understand that."
        except httpx.ReadTimeout:
            reply_text = "The agent is taking longer than expected. Please try again."


        # 5. TTS
        tts_audio_path = generate_tts_audio(reply_text)

        # Read audio file and encode as base64
        with open(tts_audio_path, "rb") as audio_file:
            audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")
        
        # Return both text and audio data
        return JSONResponse(
            content={
                "user_transcription": text,    # User's spoken words
                "agent_text": reply_text,      # Agent's text response
                "audio": audio_base64,
                "content_type": "audio/mpeg"
            },
            headers={"Access-Control-Allow-Origin": "http://localhost:5173"}
        )


    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": "Audio processing error"},
            headers={"Access-Control-Allow-Origin": "http://localhost:5173"}
        )
    finally:
        os.remove(webm_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )