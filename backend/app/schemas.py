from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Product schemas
class ProductBase(BaseModel):
    name: str
    brand: Optional[str] = None
    averageRating: Optional[float] = None
    shortDescription: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    price: float
    currencyUnit: str = "USD"
    category: str
    aisle: str
    availability: str = "in-stock"

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class Product(ProductBase):
    id: str
    createdAt: datetime
    
    class Config:
        from_attributes = True

# User schemas
class UserBase(BaseModel):
    name: str
    email: str
    profile: Optional[Dict[str, Any]] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None

class User(UserBase):
    id: str
    createdAt: datetime
    
    class Config:
        from_attributes = True

# Shopping List schemas
class ShoppingListItemBase(BaseModel):
    productId: str = Field(..., alias="product_id")
    quantity: int = 1

class ShoppingListItemCreate(ShoppingListItemBase):
    pass

class ShoppingListItem(ShoppingListItemBase):
    id: str
    userId: str
    addedAt: datetime
    product: Product
    
    class Config:
        from_attributes = True
        populate_by_name = True

# Order schemas
class OrderItem(BaseModel):
    productId: str = Field(..., alias="product_id")
    quantity: int

class OrderCreate(BaseModel):
    userId: str = Field(..., alias="user_id")
    items: List[OrderItem]

class Order(BaseModel):
    id: str
    userId: str
    items: List[Dict[str, Any]]
    total: float
    createdAt: datetime
    
    class Config:
        from_attributes = True

# Chat schemas
class ChatMessageCreate(BaseModel):
    userId: str = Field(..., alias="user_id")
    content: str
    isUser: bool = Field(..., alias="is_user")

class ChatMessage(BaseModel):
    id: str
    userId: str
    content: str
    isUser: bool
    timestamp: datetime
    
    class Config:
        from_attributes = True

# Analytics schemas
class SpendingAnalytics(BaseModel):
    spending_by_category: Dict[str, float]

# Response schemas
class StatusResponse(BaseModel):
    status: str
    message: Optional[str] = None

# User with relations
class UserWithRelations(User):
    shoppingList: List[ShoppingListItem] = []
    orders: List[Order] = []