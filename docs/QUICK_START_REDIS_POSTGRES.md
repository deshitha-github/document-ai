# Quick Start: Redis + PostgreSQL Chat History

## 🚀 Getting Started in 5 Minutes

### Prerequisites Check
```bash
# Make sure you have these installed:
- PostgreSQL 12+
- Redis 6+
- Python 3.12
```

---

## Step 1: Install Services

### macOS
```bash
# Install PostgreSQL & Redis
brew install postgresql@15 redis

# Start services
brew services start postgresql@15
brew services start redis

# Create database
createdb document_ai
```

### Linux (Ubuntu/Debian)
```bash
# Install PostgreSQL & Redis
sudo apt install postgresql postgresql-contrib redis-server

# Start services
sudo systemctl start postgresql
sudo systemctl start redis-server

# Create database
sudo -u postgres createdb document_ai
```

---

## Step 2: Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env - Add your credentials:
# - POSTGRES_PASSWORD=your_password
# - OPENAI_API_KEY=sk-...
# - WEAVIATE_URL=https://...
# - WEAVIATE_ADMIN_KEY=...
```

---

## Step 3: Install & Initialize

```bash
# Install Python dependencies
pip install -r requirements.txt

# Check all services
python scripts/check_dependencies.py

# Initialize database (creates tables)
python scripts/init_database.py
```

---

## Step 4: Start Application

```bash
python main.py
```

Visit: http://127.0.0.1:8000/docs

---

## ✅ Test It Works

```bash
# 1. Upload a document
curl -X POST "http://localhost:8000/upload_legal_pdf" \
  -F "file=@test.pdf" \
  -F "username=testuser"

# Save the tenant_id from response!

# 2. Chat with it
curl -X POST "http://localhost:8000/chat" \
  -F "tenant_id=testuser_abc123" \
  -F "message=What is this document about?"

# 3. Get chat history
curl -X GET "http://localhost:8000/chat_history/testuser_abc123"

# 4. Check session stats
curl -X GET "http://localhost:8000/session_stats/testuser_abc123"

# 5. Health check
curl -X GET "http://localhost:8000/health/databases"
```

---

## 🎯 What You Get

✅ **Fast**: Sub-5ms responses for active sessions (Redis cache)  
✅ **Reliable**: All messages saved to PostgreSQL forever  
✅ **Scalable**: Handles thousands of concurrent users  
✅ **GDPR**: Complete deletion support  

---

## 📚 Next Steps

- Read full docs: [`docs/CHAT_HISTORY_MANAGEMENT.md`](2. CHAT_HISTORY_MANAGEMENT.md)
- Implementation details: [`docs/IMPLEMENTATION_REDIS_POSTGRES.md`](IMPLEMENTATION_REDIS_POSTGRES.md)
- Tenant ID guide: [`docs/TENANT_ID_GENERATION.md`](TENANT_ID_GENERATION.md)

---

## 🆘 Troubleshooting

### Redis not connecting?
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG
```

### PostgreSQL not connecting?
```bash
# Check PostgreSQL is running
pg_isready
# Should return: accepting connections

# Check database exists
psql -l | grep document_ai
```

### Still having issues?
```bash
# Run dependency checker
python scripts/check_dependencies.py
```

---

## 🎉 You're Done!

Your chat history system is now:
- ⚡ **Fast** (Redis caching)
- 💾 **Persistent** (PostgreSQL storage)  
- 🔒 **Secure** (Multi-tenant isolation)
- 📊 **Queryable** (Full history access)

Happy coding! 🚀

