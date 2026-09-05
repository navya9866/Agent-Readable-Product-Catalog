"""
Agent-Readable Product Catalog API
Razorpay AI Buildathon - Track 1
Build an agent that grows revenue for a merchant by making their catalog discoverable.
"""

from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import csv
import io
import logging

# ==================== CONFIGURATION ====================
DATABASE_URL = "sqlite:///./catalog.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Logging for audit trail
logging.basicConfig(level=logging.INFO)
audit_logger = logging.getLogger("audit")
audit_file_handler = logging.FileHandler("audit.log")
audit_logger.addHandler(audit_file_handler)

app = FastAPI(
    title="Agent-Readable Product Catalog",
    description="Razorpay Track 1: AI Growth & Agentic Commerce",
    version="1.0.0"
)

# CORS for agents
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== DATABASE MODELS ====================

class Product(Base):
    """Product in the catalog"""
    __tablename__ = "products"
    
    id = Column(String, primary_key=True)  # SKU
    name = Column(String, index=True)
    category = Column(String, index=True)
    price = Column(Float)
    currency = Column(String, default="INR")
    description = Column(Text)
    image_url = Column(String)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Audit trail for all API actions"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String)  # search, get_details, check_availability
    agent_id = Column(String)
    resource = Column(String)  # product ID
    details = Column(Text)  # JSON
    status = Column(String)  # success, error
    

# Create tables
Base.metadata.create_all(bind=engine)

# ==================== PYDANTIC MODELS (API SCHEMAS) ====================

class ProductSchema(BaseModel):
    id: str
    name: str
    category: str
    price: float
    currency: str
    description: str
    image_url: str
    stock: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """What agents get when they search"""
    total_results: int
    page: int
    page_size: int
    results: List[ProductSchema]
    next_page_url: Optional[str]


class ProductDetailsResponse(BaseModel):
    """What agents get when they request full details"""
    id: str
    name: str
    category: str
    price: float
    currency: str
    description: str
    image_url: str
    stock: int
    in_stock: bool
    created_at: datetime
    updated_at: datetime


class AvailabilityCheckRequest(BaseModel):
    product_id: str
    quantity: int


class AvailabilityCheckResponse(BaseModel):
    """Agents use this to decide if they can complete a transaction"""
    available: bool
    requested_quantity: int
    actual_stock: int
    reason: Optional[str]
    timestamp: datetime


class AuditLogSchema(BaseModel):
    timestamp: datetime
    action: str
    agent_id: str
    resource: str
    details: dict
    status: str


# ==================== HELPER FUNCTIONS ====================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def normalize_sku(sku: str) -> str:
    """Normalize SKU to handle inconsistent formats from merchants"""
    # Remove prefixes, lowercase, strip whitespace
    sku = sku.lower().strip()
    # Remove common prefixes
    for prefix in ["sku-", "product-", "item-"]:
        if sku.startswith(prefix):
            sku = sku[len(prefix):]
    return sku


def log_audit(action: str, agent_id: str, resource: str, details: dict, status: str):
    """Write audit log"""
    db = SessionLocal()
    try:
        log_entry = AuditLog(
            action=action,
            agent_id=agent_id,
            resource=resource,
            details=json.dumps(details),
            status=status
        )
        db.add(log_entry)
        db.commit()
        audit_logger.info(f"[{action}] Agent: {agent_id}, Resource: {resource}, Status: {status}")
    except Exception as e:
        audit_logger.error(f"Failed to log audit: {str(e)}")
    finally:
        db.close()


# ==================== SEED DATA ====================

def seed_database():
    """Initialize database with sample products"""
    db = SessionLocal()
    try:
        # Check if data already exists
        count = db.query(Product).count()
        if count > 0:
            return
        
        sample_products = [
            Product(
                id="SKU-LAPTOP-001",
                name="Dell XPS 13",
                category="Electronics",
                price=94999.00,
                currency="INR",
                description="High-performance ultrabook with Intel i7, 16GB RAM, 512GB SSD",
                image_url="https://via.placeholder.com/300x300?text=Dell+XPS+13",
                stock=25
            ),
            Product(
                id="SKU-LAPTOP-002",
                name="MacBook Pro 14",
                category="Electronics",
                price=199900.00,
                currency="INR",
                description="Apple M3 Pro, 18GB RAM, 512GB SSD",
                image_url="https://via.placeholder.com/300x300?text=MacBook+Pro",
                stock=12
            ),
            Product(
                id="SKU-PHONE-001",
                name="iPhone 15 Pro",
                category="Electronics",
                price=129900.00,
                currency="INR",
                description="6.1-inch Super Retina XDR, A17 Pro, 256GB",
                image_url="https://via.placeholder.com/300x300?text=iPhone+15+Pro",
                stock=40
            ),
            Product(
                id="SKU-MONITOR-001",
                name="LG 4K Monitor 27-inch",
                category="Electronics",
                price=35999.00,
                currency="INR",
                description="4K UHD, 60Hz, USB-C, HDR10",
                image_url="https://via.placeholder.com/300x300?text=LG+Monitor",
                stock=15
            ),
            Product(
                id="SKU-HEADPHONES-001",
                name="Sony WH-1000XM5",
                category="Audio",
                price=29990.00,
                currency="INR",
                description="Wireless noise-cancelling headphones, 30-hour battery",
                image_url="https://via.placeholder.com/300x300?text=Sony+Headphones",
                stock=50
            ),
            Product(
                id="SKU-KEYBOARD-001",
                name="Mechanical Keyboard - RGB",
                category="Accessories",
                price=8999.00,
                currency="INR",
                description="Mechanical switches, RGB backlit, USB-C",
                image_url="https://via.placeholder.com/300x300?text=Mechanical+Keyboard",
                stock=0  # Out of stock - for failure handling demo
            ),
        ]
        
        db.add_all(sample_products)
        db.commit()
        print("✓ Database seeded with sample products")
    except Exception as e:
        print(f"✗ Error seeding database: {str(e)}")
    finally:
        db.close()


# ==================== API ENDPOINTS ====================

@app.get("/", tags=["Health"])
def root():
    """Health check endpoint"""
    return {
        "status": "operational",
        "service": "Agent-Readable Product Catalog",
        "track": "Razorpay AI Buildathon - Track 1",
        "docs": "/docs"
    }


@app.post("/api/v1/catalog/upload", tags=["Admin"])
async def upload_catalog(file: UploadFile = File(...)):
    """
    Admin endpoint: Upload CSV to populate catalog.
    CSV format: id, name, category, price, currency, description, image_url, stock
    """
    try:
        contents = await file.read()
        stream = io.StringIO(contents.decode("utf8"))
        csv_reader = csv.DictReader(stream)
        
        db = SessionLocal()
        added = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Normalize SKU
                sku = normalize_sku(row.get("id", ""))
                
                # Check if product exists
                existing = db.query(Product).filter(Product.id == sku).first()
                if existing:
                    existing.name = row.get("name", existing.name)
                    existing.category = row.get("category", existing.category)
                    existing.price = float(row.get("price", existing.price))
                    existing.stock = int(row.get("stock", existing.stock))
                    existing.description = row.get("description", existing.description)
                else:
                    product = Product(
                        id=sku,
                        name=row.get("name", ""),
                        category=row.get("category", ""),
                        price=float(row.get("price", 0)),
                        currency=row.get("currency", "INR"),
                        description=row.get("description", ""),
                        image_url=row.get("image_url", ""),
                        stock=int(row.get("stock", 0))
                    )
                    db.add(product)
                    added += 1
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        db.commit()
        db.close()
        
        return {
            "status": "success",
            "message": f"Uploaded {added} products",
            "errors": errors if errors else None
        }
    except Exception as e:
        log_audit("upload", "admin", "catalog", {"error": str(e)}, "error")
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")


@app.get("/api/v1/catalog/search", tags=["Agent APIs"])
def search_products(
    query: Optional[str] = Query(None, description="Search by product name or category"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    agent_id: str = Query("anonymous"),
):
    """
    AGENT ENDPOINT: Search products with filters.
    
    This is what agents call to find products.
    Every search is logged for audit trail.
    """
    try:
        db = SessionLocal()
        
        # Build query
        q = db.query(Product)
        
        if query:
            q = q.filter(
                (Product.name.ilike(f"%{query}%")) |
                (Product.description.ilike(f"%{query}%"))
            )
        
        if category:
            q = q.filter(Product.category.ilike(f"%{category}%"))
        
        if min_price is not None:
            q = q.filter(Product.price >= min_price)
        
        if max_price is not None:
            q = q.filter(Product.price <= max_price)
        
        # Count total
        total = q.count()
        
        # Paginate
        offset = (page - 1) * limit
        products = q.offset(offset).limit(limit).all()
        
        db.close()
        
        # Log the search
        log_audit(
            action="search",
            agent_id=agent_id,
            resource="catalog",
            details={
                "query": query,
                "category": category,
                "results_count": len(products),
                "page": page
            },
            status="success"
        )
        
        return SearchResponse(
            total_results=total,
            page=page,
            page_size=limit,
            results=[ProductSchema.from_orm(p) for p in products],
            next_page_url=f"/api/v1/catalog/search?query={query or ''}&page={page+1}&limit={limit}" if offset + limit < total else None
        )
    
    except Exception as e:
        log_audit("search", agent_id, "catalog", {"error": str(e)}, "error")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/v1/catalog/products/{product_id}", tags=["Agent APIs"])
def get_product_details(product_id: str, agent_id: str = Query("anonymous")):
    """
    AGENT ENDPOINT: Get full product details.
    
    Used by agents to retrieve comprehensive info before making a purchase decision.
    Graceful handling: Returns 404 with helpful error if product doesn't exist.
    """
    try:
        db = SessionLocal()
        
        # Normalize SKU
        normalized_id = normalize_sku(product_id)
        
        product = db.query(Product).filter(Product.id == normalized_id).first()
        db.close()
        
        if not product:
            log_audit(
                action="get_details",
                agent_id=agent_id,
                resource=product_id,
                details={"error": "Product not found"},
                status="error"
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Product not found",
                    "product_id": product_id,
                    "normalized_id": normalized_id,
                    "suggestion": "Check the product ID or use /search to discover products"
                }
            )
        
        log_audit(
            action="get_details",
            agent_id=agent_id,
            resource=product_id,
            details={"price": product.price, "stock": product.stock},
            status="success"
        )
        
        return ProductDetailsResponse(
            id=product.id,
            name=product.name,
            category=product.category,
            price=product.price,
            currency=product.currency,
            description=product.description,
            image_url=product.image_url,
            stock=product.stock,
            in_stock=product.stock > 0,
            created_at=product.created_at,
            updated_at=product.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log_audit(
            action="get_details",
            agent_id=agent_id,
            resource=product_id,
            details={"error": str(e)},
            status="error"
        )
        raise HTTPException(status_code=500, detail=f"Failed to retrieve product: {str(e)}")


@app.post("/api/v1/catalog/check-availability", tags=["Agent APIs"])
def check_availability(
    request: AvailabilityCheckRequest,
    agent_id: str = Query("anonymous")
):
    """
    AGENT ENDPOINT: Check if a quantity can be fulfilled.
    
    Critical for agent purchasing logic. Must be accurate and fast.
    Gracefully handles out-of-stock with fallback suggestions.
    Bounded response: Yes/No + reason.
    """
    try:
        db = SessionLocal()
        
        normalized_id = normalize_sku(request.product_id)
        product = db.query(Product).filter(Product.id == normalized_id).first()
        
        if not product:
            log_audit(
                action="check_availability",
                agent_id=agent_id,
                resource=request.product_id,
                details={"error": "Product not found", "quantity": request.quantity},
                status="error"
            )
            db.close()
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Product not found",
                    "product_id": request.product_id
                }
            )
        
        available = product.stock >= request.quantity
        reason = None
        
        if not available:
            if product.stock == 0:
                reason = f"Out of stock. Similar products available in {product.category}."
            else:
                reason = f"Requested {request.quantity} units but only {product.stock} available."
        
        log_audit(
            action="check_availability",
            agent_id=agent_id,
            resource=request.product_id,
            details={
                "requested": request.quantity,
                "available": product.stock,
                "can_fulfill": available
            },
            status="success"
        )
        
        db.close()
        
        return AvailabilityCheckResponse(
            available=available,
            requested_quantity=request.quantity,
            actual_stock=product.stock,
            reason=reason,
            timestamp=datetime.utcnow()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log_audit(
            action="check_availability",
            agent_id=agent_id,
            resource=request.product_id,
            details={"error": str(e), "quantity": request.quantity},
            status="error"
        )
        raise HTTPException(status_code=500, detail=f"Availability check failed: {str(e)}")


@app.get("/api/v1/audit-logs", tags=["Admin"])
def get_audit_logs(
    action: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500)
):
    """
    ADMIN ENDPOINT: Retrieve audit trail.
    
    Shows every action taken on the catalog:
    - Who (agent_id)
    - What (action)
    - When (timestamp)
    - Success/failure status
    """
    try:
        db = SessionLocal()
        q = db.query(AuditLog)
        
        if action:
            q = q.filter(AuditLog.action == action)
        if agent_id:
            q = q.filter(AuditLog.agent_id == agent_id)
        
        logs = q.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        db.close()
        
        return {
            "total": len(logs),
            "logs": [
                {
                    "timestamp": log.timestamp,
                    "action": log.action,
                    "agent_id": log.agent_id,
                    "resource": log.resource,
                    "details": json.loads(log.details),
                    "status": log.status
                }
                for log in logs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")


@app.get("/api/v1/catalog/stats", tags=["Admin"])
def get_catalog_stats():
    """Admin endpoint: Catalog statistics"""
    db = SessionLocal()
    try:
        total_products = db.query(Product).count()
        total_stock = db.query(Product).with_entities(
            db.func.sum(Product.stock)
        ).scalar() or 0
        
        out_of_stock = db.query(Product).filter(Product.stock == 0).count()
        categories = db.query(Product.category).distinct().count()
        
        db.close()
        
        return {
            "total_products": total_products,
            "total_stock_units": int(total_stock),
            "out_of_stock_products": out_of_stock,
            "unique_categories": categories,
            "catalog_value_inr": db.query(
                db.func.sum(Product.price * Product.stock)
            ).scalar() or 0.0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    seed_database()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
