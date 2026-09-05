# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       AI Agent Buyers                           │
│        (Razorpay Commerce Platform or External Agents)         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
         ┌──────▼────┐   ┌──────▼────┐   ┌────▼──────┐
         │  Search   │   │  Details  │   │ Availability
         │  Endpoint │   │ Endpoint  │   │ Endpoint
         └──────┬────┘   └──────┬────┘   └────┬──────┘
                │               │               │
                └───────────────┼───────────────┘
                                │
                        ┌───────▼────────┐
                        │   FastAPI      │
                        │   Server       │
                        │  Port: 8000    │
                        └───────┬────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
   ┌────▼─────┐          ┌──────▼──────┐         ┌────▼─────┐
   │  SQLite   │          │  Audit      │         │  SKU      │
   │  Database │          │  Log File   │         │  Normaliz │
   │           │          │             │         │           │
   │ Products  │          │ audit.log   │         │  Handler  │
   │ Inventory │          │             │         │           │
   └───────────┘          └─────────────┘         └───────────┘
        │
   ┌────▼──────────┐
   │  6 Sample     │
   │  Products     │
   │  Pre-Loaded   │
   └───────────────┘
```

## Request Flow

### Example 1: Agent Search

```
Agent Request
    │
    ├─ GET /api/v1/catalog/search?query=laptop&agent_id=agent-001
    │
    ▼
FastAPI Receives Request
    │
    ├─ Validate input (query, filters, pagination)
    │
    ├─ Build database query (filter by name, category, price, etc.)
    │
    ├─ Query SQLite database
    │    └─ SELECT * FROM products WHERE name LIKE '%laptop%'
    │
    ├─ Serialize results to JSON
    │
    ├─ Log to audit trail
    │    ├─ timestamp: 2024-09-05T10:10:00
    │    ├─ action: "search"
    │    ├─ agent_id: "agent-001"
    │    ├─ resource: "catalog"
    │    ├─ details: {"query": "laptop", "results": 2}
    │    └─ status: "success"
    │
    ▼
Return JSON Response
    │
    └─ {
         "total_results": 2,
         "page": 1,
         "results": [
           {
             "id": "SKU-LAPTOP-001",
             "name": "Dell XPS 13",
             "price": 94999.0,
             "stock": 25,
             ...
           }
         ]
       }
```

### Example 2: Check Availability (Graceful Failure)

```
Agent Request
    │
    ├─ POST /api/v1/catalog/check-availability
    │  {"product_id": "SKU-KEYBOARD-001", "quantity": 1}
    │  agent_id: "agent-001"
    │
    ▼
FastAPI Receives Request
    │
    ├─ Normalize SKU
    │    └─ "sku-keyboard-001" (handles different formats)
    │
    ├─ Query database for product
    │    └─ SELECT * FROM products WHERE id = "sku-keyboard-001"
    │
    ├─ Check stock vs. requested quantity
    │    ├─ Stock: 0
    │    ├─ Requested: 1
    │    └─ Result: NOT AVAILABLE
    │
    ├─ Log to audit trail
    │    ├─ action: "check_availability"
    │    ├─ status: "success" (operation succeeded, even though product unavailable)
    │    └─ details: {"requested": 1, "actual": 0, "available": false}
    │
    ▼
Return JSON Response (Graceful Failure)
    │
    └─ {
         "available": false,
         "requested_quantity": 1,
         "actual_stock": 0,
         "reason": "Out of stock. Similar products available in Accessories.",
         "timestamp": "2024-09-05T10:15:00"
       }
```

## Database Schema

### Products Table

```sql
CREATE TABLE products (
    id VARCHAR PRIMARY KEY,              -- Normalized SKU
    name VARCHAR INDEXED,                -- Product name (searchable)
    category VARCHAR INDEXED,            -- Product category (searchable)
    price FLOAT,                         -- Price in INR
    currency VARCHAR,                    -- Currency code
    description TEXT,                    -- Full product description
    image_url VARCHAR,                   -- Product image URL
    stock INTEGER,                       -- Current inventory level
    created_at DATETIME,                 -- When product was added
    updated_at DATETIME                  -- When product was last modified
);
```

**Indexes:**
- PRIMARY KEY on `id` (fast SKU lookups)
- INDEX on `name` (fast search by name)
- INDEX on `category` (fast category filtering)

### Audit Logs Table

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,  -- When action occurred
    action VARCHAR,                                 -- search, get_details, check_availability
    agent_id VARCHAR,                               -- Which agent made the request
    resource VARCHAR,                               -- What was accessed (product ID or "catalog")
    details TEXT,                                   -- JSON with request/response details
    status VARCHAR                                  -- success or error
);
```

**Why this design?**
- Immutable (audit logs are append-only, never deleted)
- Fast insertion (no complex joins)
- Easy filtering (by action, agent_id, timestamp)
- Compliant (shows agent activity for Razorpay merchants)

## Core Components

### 1. SKU Normalizer (Lines 121–131)

**Problem:** Merchants upload inconsistent SKU formats:
- `SKU-001`, `sku-001`, `PRODUCT-001`, `001`

**Solution:**
```python
def normalize_sku(sku: str) -> str:
    sku = sku.lower().strip()
    for prefix in ["sku-", "product-", "item-"]:
        if sku.startswith(prefix):
            sku = sku[len(prefix):]
    return sku
```

**Impact:** Search is forgiving to real-world messy data

### 2. Database ORM (Lines 41–69)

Uses SQLAlchemy ORM for:
- Type safety (prevent SQL injection)
- Atomic operations (prevent race conditions)
- Transaction management (consistent state)

### 3. Audit Logger (Lines 77–94)

Logs every action with:
```python
log_audit(
    action="search",
    agent_id="agent-001",
    resource="catalog",
    details={"query": "laptop", "results": 2},
    status="success"
)
```

**Writes to:** Both database (queryable) and `audit.log` file (permanent record)

### 4. Error Handling (Lines 360–375)

Returns helpful 404 errors:
```json
{
  "error": "Product not found",
  "product_id": "SKU-INVALID",
  "normalized_id": "sku-invalid",
  "suggestion": "Check the product ID or use /search to discover products"
}
```

**Impact:** Agents can self-diagnose issues

### 5. Availability Check (Lines 455–525)

Atomic operation:
1. Query product from database
2. Compare stock vs. requested quantity
3. Return bounded response (yes/no + reason)
4. Log to audit trail

**No race conditions:** Database read/write is atomic

## Track 1 Compliance

### ✅ Grow Revenue
- Agents discover products via `/search`
- Agents get full details via `/details`
- Agents can check availability and purchase
→ Merchants reach AI buyers they couldn't reach before

### ✅ Make Merchants Transactable
- Clean API for agent automation
- Structured data agents can parse
- Real-time inventory updates
→ Merchants become machine-readable

### ✅ Every Money Action Explainable
- Audit logs for every action (search, details, check)
- Queryable via `/api/v1/audit-logs`
- Shows: agent_id, timestamp, action, result
→ Razorpay merchants see what happened

### ✅ Bounded and Gated
- `/check-availability` returns yes/no + reason
- No ambiguity (not "maybe" or "probably")
- Atomic transactions prevent race conditions
→ Agents can trust the API

### ✅ Graceful Failure Handling
- Out-of-stock: suggests similar products
- Product not found: helpful error message with suggestions
- Invalid requests: 400 with clear error details
- Database errors: 500 with safe error message
→ Systems don't crash, they fail informatively

## Deployment Readiness

### Local Development
```bash
python main.py
# Runs on http://localhost:8000
```

### Production Deployment

#### Option 1: Render.com
```bash
# Create Procfile
echo "web: uvicorn main:app --host 0.0.0.0 --port $PORT" > Procfile
git push render main
```

#### Option 2: Docker
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Option 3: AWS Lambda
Convert to serverless (requires modifications):
- Remove SQLite → use DynamoDB/RDS
- Add AWS Lambda handler
- Store logs in CloudWatch

## Performance Characteristics

| Operation | Database Query | Time | Notes |
|-----------|----------------|------|-------|
| Search | SELECT with WHERE | ~5ms | Indexed on name, category |
| Get Details | SELECT by PK | ~1ms | Primary key lookup (fastest) |
| Check Availability | SELECT by PK | ~1ms | Atomic (no race conditions) |
| Add to Audit | INSERT | ~2ms | Append-only, fast |
| List Audit Logs | SELECT with ORDER BY | ~10ms | Depends on table size |

## Scalability Notes

### Current Design (SQLite)
- Good for: MVP, demos, single-server deployments
- Handles: ~10k products, ~100k audit log entries
- Limitation: Single-threaded writes (but SQLAlchemy handles queuing)

### Production Scale (PostgreSQL)
If deployed to production with many agents:
```python
# Change DATABASE_URL in main.py
DATABASE_URL = "postgresql://user:password@localhost/catalog"
```

Benefits:
- Multi-threaded reads/writes
- Better concurrency handling
- Built-in replication for HA
- Scales to millions of products

---

## Implementation Decisions & Tradeoffs

| Decision | Rationale | Tradeoff |
|----------|-----------|----------|
| FastAPI | Modern, async-capable, auto-docs | Requires Python 3.7+ |
| SQLAlchemy ORM | Type-safe, prevents SQL injection | Slight overhead vs. raw SQL |
| SQLite | Zero-config, embedded database | Single-threaded writes |
| JSON Audit Logs | Flexible, human-readable | Larger disk usage |
| Pydantic Models | Data validation, auto-documentation | Small runtime overhead |

**All decisions prioritized safety and auditability over raw performance.**

---

This architecture ensures:
- ✅ Reliability (proper error handling, audit trails)
- ✅ Security (input validation, SQL injection prevention)
- ✅ Auditability (complete action logs)
- ✅ Scalability (clean design, easy to upgrade)
- ✅ Maintainability (well-structured code, clear separation of concerns)

