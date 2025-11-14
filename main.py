import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers

def to_serializable(doc):
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d

# Public endpoints

@app.get("/")
def read_root():
    return {"message": "Shop API running"}

@app.get("/products")
def list_products(q: Optional[str] = None, category: Optional[str] = None):
    filt = {}
    if q:
        # simple case-insensitive search on title/description
        filt["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if category:
        filt["category"] = category
    docs = db["product"].find(filt).sort("created_at", -1)
    return [to_serializable(d) for d in docs]

class CartItem(BaseModel):
    product_id: str
    quantity: int

class CheckoutRequest(BaseModel):
    items: List[CartItem]
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None

@app.post("/checkout")
def checkout(payload: CheckoutRequest):
    # Validate products and stock, compute totals
    order_items: List[OrderItem] = []
    total = 0.0

    for item in payload.items:
        try:
            oid = ObjectId(item.product_id)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid product id: {item.product_id}")
        prod = db["product"].find_one({"_id": oid})
        if not prod:
            raise HTTPException(status_code=404, detail=f"Product not found: {item.product_id}")
        if prod.get("stock", 0) < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {prod.get('title')}")
        price = float(prod.get("price", 0))
        subtotal = price * item.quantity
        total += subtotal
        order_items.append(OrderItem(
            product_id=str(prod["_id"]),
            title=prod.get("title"),
            price=price,
            quantity=item.quantity,
            subtotal=subtotal
        ))

    # Decrement stock
    for item in payload.items:
        db["product"].update_one(
            {"_id": ObjectId(item.product_id)},
            {"$inc": {"stock": -item.quantity}, "$set": {"in_stock": True}}
        )

    # Create order document
    order = Order(
        buyer_name=payload.buyer_name,
        buyer_email=payload.buyer_email,
        items=order_items,
        total=round(total, 2),
        status="paid"
    )
    order_id = create_document("order", order)
    return {"order_id": order_id, "total": order.total}

# Owner/Seller endpoints

class ProductCreate(Product):
    pass

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    in_stock: Optional[bool] = None

@app.post("/admin/products")
def create_product(payload: ProductCreate):
    pid = create_document("product", payload)
    return {"id": pid}

@app.patch("/admin/products/{product_id}")
def update_product(product_id: str, payload: ProductUpdate):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")
    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    update["updated_at"] = db["product"].find_one({"_id": oid}).get("updated_at")
    res = db["product"].update_one({"_id": oid}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"updated": True}

@app.get("/admin/orders")
def list_orders():
    docs = db["order"].find().sort("created_at", -1)
    return [to_serializable(d) for d in docs]

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
