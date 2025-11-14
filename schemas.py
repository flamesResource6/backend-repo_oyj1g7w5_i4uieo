"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    stock: int = Field(0, ge=0, description="Units available in inventory")
    image_url: Optional[str] = Field(None, description="Image URL for the product")
    in_stock: bool = Field(True, description="Whether product is generally available")

class OrderItem(BaseModel):
    product_id: str = Field(..., description="Referenced product _id as string")
    title: str = Field(..., description="Snapshot of product title at purchase time")
    price: float = Field(..., ge=0, description="Unit price at purchase time")
    quantity: int = Field(..., ge=1, description="Quantity purchased")
    subtotal: float = Field(..., ge=0, description="price * quantity")

class Order(BaseModel):
    """
    Orders collection schema
    Collection name: "order"
    """
    buyer_name: Optional[str] = Field(None, description="Buyer name")
    buyer_email: Optional[str] = Field(None, description="Buyer email")
    items: List[OrderItem] = Field(default_factory=list, description="Purchased items")
    total: float = Field(..., ge=0, description="Order total amount")
    status: str = Field("paid", description="Order status")
