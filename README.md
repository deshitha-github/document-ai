# Document AI Chatbot

A legal document assistant chatbot with RAG (Retrieval-Augmented Generation) capabilities, using Weaviate Cloud for vector storage and retrieval.

## Features

- 📄 **PDF OCR Processing**: Extract text from scanned legal documents
- 🤖 **AI-Powered Chat**: Conversational interface with memory
- 🔍 **Vector Search**: Weaviate Cloud (cloud-based vector database with semantic search)
- 🧠 **RAG Integration**: Retrieve relevant context from uploaded documents
- 💬 **Hybrid Session Management**: Redis (fast cache) + PostgreSQL (persistent storage)
- 🚀 **High Performance**: Sub-5ms cache response times for active sessions
- 📊 **Complete History**: All conversations stored permanently in PostgreSQL
- 👥 **Multi-Tenancy**: Complete data isolation - each tenant can only access their own documents
- 🔐 **UUID-Based Tenant IDs**: Production-friendly unique identifiers
- 🗑️ **GDPR Compliance**: Full data deletion across all systems
- 🔐 **Secure**: Environment-based configuration

## Prerequisites

- **Python 3.12** (recommended for best compatibility)
  - Python 3.11+ will also work
  - Python 3.13 may have package compatibility issues
- **Tesseract OCR** (for text extraction from PDFs)
- **OpenAI API Key** (for embeddings and chat)
- **Weaviate Cloud Account** (for vector storage)
- **PostgreSQL 12+** (for persistent chat history storage)
- **Redis 6+** (for session caching)

### Installing Prerequisites

#### macOS

```bash
# Install Python 3.12
brew install python@3.12

# Install Tesseract OCR
brew install tesseract

# Verify installations
python3.12 --version
tesseract --version
```

#### Windows

```powershell
# Install Python 3.12 from python.org
# Download and install from: https://www.python.org/downloads/

# Install Tesseract OCR
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add Tesseract to your PATH or set TESSERACT_CMD in .env

# Verify installations
python --version
tesseract --version
```

#### Linux (Ubuntu/Debian)

```bash
# Install Python 3.12
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip

# Install Tesseract OCR
sudo apt install tesseract-ocr

# Verify installations
python3.12 --version
tesseract --version
```

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd document-ai
```

### 2. Create a Virtual Environment

**macOS/Linux:**
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install & Start Database Services

#### PostgreSQL

**macOS**:
```bash
# Install
brew install postgresql@15

# Start service
brew services start postgresql@15

# Create database
createdb document_ai
```

**Linux (Ubuntu/Debian)**:
```bash
# Install
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql

# Create database
sudo -u postgres createdb document_ai
```

#### Redis

**macOS**:
```bash
# Install
brew install redis

# Start service
brew services start redis
```

**Linux (Ubuntu/Debian)**:
```bash
# Install
sudo apt install redis-server

# Start service
sudo systemctl start redis-server
```

### 4. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL_NAME=gpt-4o-mini

# Weaviate Cloud Configuration
WEAVIATE_URL=https://your-cluster.weaviate.cloud
WEAVIATE_ADMIN_KEY=your_weaviate_admin_key_here
WEAVIATE_COLLECTION=LegalKnowledgeBase

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=document_ai
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_SESSION_TTL=3600

# OCR Configuration (optional)
# For Windows, set full path to tesseract.exe
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
# For macOS/Linux with brew
# TESSERACT_CMD=/opt/homebrew/bin/tesseract
OCR_WORKERS=2
```

### 6. Check Dependencies & Initialize Database

```bash
# Check that all services are accessible
python scripts/check_dependencies.py

# Initialize PostgreSQL database (creates tables)
python scripts/init_database.py
```

### 7. Run the Application

**macOS/Linux:**
```bash
source .venv/bin/activate
python main.py
```

**Windows:**
```powershell
.venv\Scripts\activate
python main.py
```

The server will start at `http://127.0.0.1:8000`

## Usage

### Interactive Test Client

The easiest way to test the chatbot:

**macOS/Linux:**
```bash
source .venv/bin/activate
python tests/test_client.py
```

**Windows:**
```powershell
.venv\Scripts\activate
python tests/test_client.py
```

Commands in the test client:
- `/upload <file_path>` - Upload and process a PDF
- `/search <query>` - Search for similar documents
- `/stats` - View Weaviate collection statistics
- `/clear` - Clear conversation history
- `/quit` - Exit the client
- Type any message to chat with the AI

### API Documentation

Once the server is running, visit:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## API Endpoints

### Document Management
- `POST /upload_legal_pdf` - Upload and process a legal PDF (accepts `username` OR `tenant_id`)
- `POST /weaviate_delete` - Delete a document from Weaviate by filename
- `GET /weaviate_stats` - Get Weaviate collection statistics

### Chat & Search
- `POST /chat` - Send a message to the chatbot (accepts `username` OR `tenant_id`, tenant-filtered results)
- `POST /weaviate_search` - Search Weaviate for similar documents
- `GET /chat_history/{tenant_id}` - Get complete chat history from PostgreSQL
- `GET /session_stats/{tenant_id}` - Get session statistics (message count, cache status)
- `POST /clear_session` - Clear conversation history (Redis cache or both Redis + PostgreSQL)

### Tenant Management
- `POST /delete_tenant` - Delete all documents and data for a tenant (GDPR compliance - deletes from Weaviate, Redis, and PostgreSQL)

### Health Check
- `GET /health` - Check if the service is running
- `GET /health/databases` - Check Redis and PostgreSQL connection health

> 🆕 **New Feature**: Endpoints now support `username` parameter for automatic production-friendly tenant ID generation (format: `username_<uuid>`). See [Tenant ID Generation Guide](docs/TENANT_ID_GENERATION.md) for details.

## API Usage Examples

### Upload a PDF

**Option 1: Using `username` (Recommended for New Tenants)**

System generates a unique tenant ID automatically:

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/upload_legal_pdf" \
  -F "file=@contract.pdf" \
  -F "username=john_doe"
```

**Python:**
```python
import requests

with open('contract.pdf', 'rb') as f:
    response = requests.post(
        'http://127.0.0.1:8000/upload_legal_pdf',
        files={'file': f},
        data={'username': 'john_doe'}
    )
    
# Response includes the generated tenant_id
# {
#   "tenant_id": "john_doe_a3f5b2c1",  # ← Store this for future use!
#   "username": "john_doe",
#   ...
# }
```

**Option 2: Using `tenant_id` (For Existing Tenants)**

Use an existing tenant ID from previous sessions:

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/upload_legal_pdf" \
  -F "file=@contract.pdf" \
  -F "tenant_id=john_doe_a3f5b2c1"
```

**Python:**
```python
import requests

with open('contract.pdf', 'rb') as f:
    response = requests.post(
        'http://127.0.0.1:8000/upload_legal_pdf',
        files={'file': f},
        data={'tenant_id': 'john_doe_a3f5b2c1'}
    )
print(response.json())
# Output: {
#   "message": "PDF 'contract.pdf' processed successfully for tenant 'user123'",
#   "chunks": 42,
#   "tenant_id": "user123",
#   "filename": "contract.pdf"
# }
```

### Chat with the Bot

**Option 1: Using `username` (New Session)**

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -F "username=john_doe" \
  -F "message=What are the main terms of the contract?"
```

**Option 2: Using `tenant_id` (Existing Session)**

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -F "tenant_id=john_doe_a3f5b2c1" \
  -F "message=What are the main terms of the contract?"
```

**Python:**
```python
import requests

# For existing tenant with stored tenant_id
response = requests.post(
    'http://127.0.0.1:8000/chat',
    data={
        'tenant_id': 'user123',
        'message': 'What are the main terms of the contract?'
    }
)
print(response.json())
```

### Search Weaviate

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/weaviate_search" \
  -F "query=contract terms" \
  -F "k=5" \
  -F "tenant_id=user123"
```

### Delete a Tenant (GDPR Compliance)

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/delete_tenant" \
  -F "tenant_id=user123"
```

**Python:**
```python
import requests

response = requests.post(
    'http://127.0.0.1:8000/delete_tenant',
    data={'tenant_id': 'user123'}
)
print(response.json())
# Output: {
#   "status": "success",
#   "tenant_id": "user123",
#   "weaviate_deletion": {...},
#   "memory_cleared": true,
#   "message": "All data for tenant 'user123' has been deleted successfully"
# }
```

## How It Works

### Document Processing Pipeline

1. **PDF Upload** → API receives the PDF file with `tenant_id`
2. **OCR Extraction** → Tesseract extracts text from each page
3. **Text Chunking** → Document is split into manageable chunks
4. **Embedding** → OpenAI creates vector embeddings for each chunk
5. **Storage** → Chunks are stored in **Weaviate Cloud** with tenant isolation (persistent, scalable, cloud-native)

### Chat with RAG

1. **User Query** → User asks a question with their `tenant_id`
2. **Vector Search** → Find relevant document chunks (filtered by tenant)
3. **Context Retrieval** → Most relevant chunks from tenant's documents are retrieved
4. **LLM Generation** → OpenAI generates answer with context
5. **Response** → Answer is returned to user

**Multi-Tenant Isolation**: Each tenant can only search and retrieve their own documents. This ensures complete data privacy and GDPR compliance.

For detailed information about the upsertion process, see [`docs/UPSERTION_GUIDE.md`](docs/UPSERTION_GUIDE.md)

## Project Structure

```
document-ai/
├── ai_service/            # AI agent and prompt management
│   ├── agent.py           # Main chat agent with RAG
│   ├── prompts.py         # System prompts and templates
│   └── session_manager.py # Conversation memory management
├── llm/                   # Language model configuration
│   └── model.py           # OpenAI model initialization
├── OCR/                   # PDF text extraction
│   └── text_extraction.py # Tesseract OCR implementation
├── RAG/                   # Retrieval-Augmented Generation
│   ├── vectorizer.py      # Weaviate vector store operations
│   ├── preprocessor.py    # Document processing and chunking
│   └── retriever.py       # Context retrieval logic
├── utils/                 # Utility functions
│   ├── logging_util.py    # Logging configuration
│   ├── response_codes.py  # HTTP response codes
│   └── util.py            # General utilities
├── tests/                 # Test scripts
│   ├── test_client.py     # Test Client Implementation
│   └──  test_weviate.py   # Weaviate setup
├── logs/                  # Application logs
├── main.py                # FastAPI application entry point
├── test_client.py         # Interactive test client
├── test_weaviate.py       # Weaviate connection test
├── requirements.txt       # Python dependencies
└── .env                   # Environment configuration (create this)
```

## Testing

### Test Weaviate Connection

```bash
python test_weaviate.py
```

### Test Interactive Chat

```bash
python test_client.py
```

### Run with Sample Document

```bash
# Start the server
python main.py

# In another terminal, run the test client
python test_client.py

# In the client, upload a document
💬 You: /upload path/to/document.pdf

# Ask questions about it
💬 You: What are the main points in this document?
```

## Technologies

- **FastAPI**: Modern, fast web framework for building APIs
- **LangChain**: Framework for developing LLM applications
- **OpenAI**: GPT models for chat and text embeddings
- **Weaviate**: Cloud-native vector database for semantic search
- **PyMuPDF (fitz)**: PDF text and image extraction
- **Tesseract OCR**: Optical character recognition
- **Python 3.12**: Recommended Python version

## Troubleshooting

### Common Issues

#### 1. numpy Architecture Error (macOS)

If you see "incompatible architecture" errors:
- Make sure you're using Python 3.12: `python3.12 --version`
- Recreate your virtual environment with Python 3.12
- Avoid using Python 3.13 (too new, limited package support)

#### 2. Tesseract Not Found

**macOS:**
```bash
brew install tesseract
# Add to .env if needed:
# TESSERACT_CMD=/opt/homebrew/bin/tesseract
```

**Windows:**
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Add to PATH or set in `.env`: `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`

#### 3. Weaviate gRPC Connection Issues

If you see gRPC timeout errors:
- The code automatically uses `skip_init_checks=True` to bypass gRPC
- REST API is used as fallback
- This is normal for some network configurations

#### 4. No Text Extracted from PDF

- Ensure Tesseract is installed: `tesseract --version`
- Check if the PDF contains actual text or just images
- Verify `TESSERACT_CMD` in `.env` points to correct path

## Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started in 5 minutes
- **[Weaviate Integration](docs/WEAVIATE_INTEGRATION.md)** - Cloud vector database setup
- **[Upsertion Guide](docs/UPSERTION_GUIDE.md)** - Document processing implementation
- **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)** - Technical overview

## License

[Your License Here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For questions or issues:
1. Check the documentation in the `docs/` folder
2. Review the troubleshooting section above
3. Open an issue in the repository
