# Quick Start — Get Running in 2 Minutes

## Step 1: Install Dependencies (30 seconds)

```bash
pip install -r requirements.txt
```

## Step 2: Start the API (10 seconds)

```bash
python main.py
```

You should see:
```
✓ Database seeded with sample products
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Step 3: Test It Works (1 minute)

### Option A: Open the Interactive Docs
Open this in your browser:
```
http://localhost:8000/docs
```

You'll see Swagger UI with all endpoints. Click any endpoint and click "Try it out" to test.

### Option B: Run the Test Suite
In a new terminal window:
```bash
python test_api.py
```

This runs 14 automated tests covering all endpoints, search filters, error handling, and audit logging.

### Option C: Manual cURL Tests

**Health Check:**
```bash
curl http://localhost:8000/
```

**Search for products:**
```bash
curl "http://localhost:8000/api/v1/catalog/search?query=laptop"
```

**Get product details:**
```bash
curl "http://localhost:8000/api/v1/catalog/products/SKU-LAPTOP-001"
```

**Check if product is available:**
```bash
curl -X POST "http://localhost:8000/api/v1/catalog/check-availability" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "SKU-LAPTOP-001", "quantity": 5}'
```

**Check out-of-stock product (graceful failure):**
```bash
curl -X POST "http://localhost:8000/api/v1/catalog/check-availability" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "SKU-KEYBOARD-001", "quantity": 1}'
```

**View audit logs:**
```bash
curl "http://localhost:8000/api/v1/audit-logs"
```

## Step 4: Record Your Demo Video

Keep the API running and open a new terminal.

### Using Quicktime (Mac)
1. Press Cmd + Space
2. Type "Screen Recording"
3. Select "New Screen Recording"
4. Click red button to start
5. Select the terminal window
6. Run the cURL commands above
7. Stop recording
8. Save as MP4

### Using OBS (Windows/Linux/Mac)
1. Open OBS
2. Add a "Display Capture" or "Window Capture" source
3. Click Start Recording
4. Run the cURL commands
5. Stop recording
6. File → Export Video → MP4

### Simple: Use Terminal Recording
```bash
# macOS: Use QuickTime
# Windows: Use Xbox Game Bar (Win + G)
# Linux: Use SimpleScreenRecorder
```

## What Your Demo Should Show (5 minutes)

### 0:00–0:30: Intro
"Hi, I'm [Name]. I built an agent-readable product catalog API for Razorpay. The problem is that AI agents can buy from humans, but merchants can't be transacted by agents because their product data is locked in spreadsheets. I built an API that exposes normalized product data agents can query."

### 0:30–1:30: API in Action
Show 3 API calls:

**Call 1: Search**
```bash
curl "http://localhost:8000/api/v1/catalog/search?query=laptop"
```
"Agent searches for 'laptop'. Here's the structured response with product details, prices, and availability."

**Call 2: Get Details**
```bash
curl "http://localhost:8000/api/v1/catalog/products/SKU-LAPTOP-001"
```
"Agent requests full details on the Dell XPS. Here's the complete information it needs to make a purchase decision."

**Call 3: Check Availability**
```bash
curl -X POST "http://localhost:8000/api/v1/catalog/check-availability" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "SKU-KEYBOARD-001", "quantity": 1}'
```
"Finally, agent checks if we can fulfill an order. This product is out of stock, and the API gracefully tells the agent why and suggests similar products."

### 1:30–2:30: Audit Trail
```bash
curl "http://localhost:8000/api/v1/audit-logs?limit=20"
```
"Here's the audit trail. Every agent search, every detail request, every availability check is logged with timestamp, agent ID, and success/failure status. This is what Razorpay merchants see for compliance and debugging."

### 2:30–3:00: Architecture
Show the code briefly:
- SKU normalization function (handles messy data)
- Check availability logic (atomic operations)
- Audit logging middleware

"The system is designed with three principles: explainability (JSON + audit logs), bounded operations (yes/no answers), and graceful failure (helpful error messages)."

### 3:00–5:00: Close
"That's the agent-readable product catalog. It enables AI agents to discover and buy from merchants on Razorpay, supporting the open problem of agent-to-agent commerce. Code is on GitHub [your repo]. Thanks."

---

## File Structure After Setup

```
razorpay-catalog-api/
├── main.py              ← FastAPI server
├── requirements.txt     ← Dependencies
├── test_api.py         ← Test suite
├── sample_catalog.csv  ← Example product data
├── README.md           ← Full documentation
├── QUICKSTART.md       ← This file
├── catalog.db          ← SQLite database (created on first run)
└── audit.log           ← Audit trail (created on first API call)
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'fastapi'"
```bash
pip install -r requirements.txt
```

### "Address already in use" (port 8000 is taken)
Edit `main.py` line 290:
```python
uvicorn.run(app, host="0.0.0.0", port=8001)  # Change to 8001
```

### "Database is locked"
Delete `catalog.db` and restart:
```bash
rm catalog.db
python main.py
```

### Test suite fails with "Connection refused"
Make sure API is running in another terminal:
```bash
python main.py
# Then in a new terminal:
python test_api.py
```

---

## Next Steps

1. ✓ Install dependencies
2. ✓ Run the API
3. ✓ Test it works
4. ✓ Record your video
5. ✓ Push to GitHub
6. ✓ Submit to Razorpay

---

## GitHub Quick Setup

```bash
git init
git add .
git commit -m "Agent-Readable Product Catalog - Razorpay AI Buildathon Track 1"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/razorpay-catalog-api.git
git push -u origin main
```

Then update your GITHUB URL in the Razorpay application form.

---

Good luck! 🚀
