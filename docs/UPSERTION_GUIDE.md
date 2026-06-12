# Document Upsertion Implementation Guide

This document provides a comprehensive overview of the document upsertion functionality in the Document AI Chatbot, explaining how documents are processed, embedded, and stored in the Weaviate vector database.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Implementation Details](#implementation-details)
- [Usage](#usage)
- [Integration with Current Development](#integration-with-current-development)
- [API Reference](#api-reference)
- [Error Handling](#error-handling)
- [Performance Considerations](#performance-considerations)

---

## Overview

**Upsertion** (Update + Insertion) is the process of adding or updating document chunks in the vector database. In this system, when a PDF is uploaded, it goes through several stages before being stored as searchable vector embeddings.

### What Happens During Upsertion?

1. **PDF Upload** → User uploads a PDF through the API
2. **OCR Extraction** → Text is extracted from each page using Tesseract
3. **Text Chunking** → Extracted text is split into manageable chunks
4. **Embedding Generation** → OpenAI creates vector embeddings for each chunk
5. **Vector Storage** → Chunks are stored in both FAISS and Weaviate
6. **Metadata Indexing** → Filename, chunk IDs, and metadata are stored

### Why Dual Storage?

- **FAISS**: Fast local retrieval for development and quick queries
- **Weaviate**: Persistent cloud storage, scalable, supports complex queries

---

## Architecture

### High-Level Flow

```
┌─────────────┐
│  PDF Upload │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  OCR Extraction │ (Tesseract)
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Text Chunking  │ (LangChain)
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│   Embedding     │ (OpenAI)
└──────┬──────────┘
       │
       ├──────────────┐
       │              │
       ▼              ▼
┌──────────┐    ┌──────────┐
│  FAISS   │    │ Weaviate │
│ (Local)  │    │ (Cloud)  │
└──────────┘    └──────────┘
```

### Component Interaction

```
┌──────────────┐
│   main.py    │  FastAPI endpoint (/upload_legal_pdf)
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ RAG/preprocessor.py  │  Orchestrates the pipeline
└──────┬───────────────┘
       │
       ├────────────────────────────┐
       │                            │
       ▼                            ▼
┌─────────────────┐       ┌────────────────────┐
│ OCR/text_       │       │ RAG/weaviate_      │
│ extraction.py   │       │ vectorizer.py      │
└─────────────────┘       └────────────────────┘
       │                            │
       ▼                            ▼
  [Text Output]              [Weaviate Cloud]
```

---

## Implementation Details

### 1. OCR Extraction (`OCR/text_extraction.py`)

#### Purpose
Extract text from scanned or hybrid PDFs using Tesseract OCR.

#### Key Functions

##### `extract_text_from_scanned_page()`
```python
@staticmethod
def extract_text_from_scanned_page(pdf_path, page_number=0, 
                                   invert_negative=True, dpi=300):
    """
    Extract text from a single PDF page using OCR.
    
    Args:
        pdf_path (str): Path to PDF file
        page_number (int): Page index (0-based)
        invert_negative (bool): Invert if negative scan detected
        dpi (int): Rendering DPI for quality
    
    Returns:
        str: OCR-extracted text
    """
```

**Process:**
1. Opens PDF with PyMuPDF (fitz)
2. Renders page as high-resolution image (default 300 DPI)
3. Converts to grayscale
4. Detects and inverts negative scans (white text on black)
5. Binarizes image for cleaner OCR
6. Runs Tesseract OCR
7. Returns extracted text

##### `extract_pdf_text()` (Async)
```python
async def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text from all pages asynchronously.
    
    Args:
        pdf_path (str): Path to PDF
    
    Returns:
        str: Combined text from all pages
    """
```

**Features:**
- Processes multiple pages concurrently
- Uses semaphore to limit concurrent OCR workers (default: 2)
- Provides progress logging
- Handles errors gracefully

**Configuration:**
```env
OCR_WORKERS=2  # Number of concurrent OCR processes
TESSERACT_CMD=/path/to/tesseract  # Optional: Tesseract path
```

---

### 2. Text Processing (`RAG/preprocessor.py`)

#### Purpose
Orchestrate the document processing pipeline from PDF to vector storage.

#### Key Function

##### `build_legal_rag_index()`
```python
async def build_legal_rag_index(pdf_path: str, filename: str) -> int:
    """
    Process PDF and upsert to vector stores.
    
    Args:
        pdf_path (str): Path to PDF file
        filename (str): Original filename
    
    Returns:
        int: Number of chunks processed
    
    Raises:
        ValueError: If no text extracted
    """
```

**Pipeline Steps:**

1. **OCR Extraction**
   ```python
   ocr_text = await extract_pdf_text(pdf_path)
   if not ocr_text or not ocr_text.strip():
       raise ValueError("No text extracted from PDF")
   ```

2. **Text Chunking**
   ```python
   text_splitter = RecursiveCharacterTextSplitter(
       chunk_size=1000,
       chunk_overlap=200,
       length_function=len,
   )
   chunks = text_splitter.split_text(ocr_text)
   ```
   - **chunk_size**: 1000 characters per chunk
   - **chunk_overlap**: 200 characters overlap between chunks
   - Ensures context preservation across chunks

3. **FAISS Storage**
   ```python
   vectorizer = Vectorizer()
   vectorizer.add_texts(chunks)
   vectorizer.save()
   ```

4. **Weaviate Upsertion**
   ```python
   result = upsert_to_weaviate(
       chunks=chunks,
       filename=filename,
       metadata={"upload_date": datetime.now().isoformat()}
   )
   ```

---

### 3. Weaviate Integration (`RAG/weaviate_vectorizer.py`)

#### Purpose
Handle all interactions with Weaviate Cloud vector database.

#### Class: `WeaviateVectorStore`

##### Initialization
```python
def __init__(self):
    """Initialize Weaviate client and ensure collection exists."""
    self.client = weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=Auth.api_key(WEAVIATE_ADMIN_KEY),
        headers={"X-OpenAI-Api-Key": OPENAI_API_KEY},
        skip_init_checks=True  # Skip gRPC health check
    )
    self._ensure_collection_exists()
```

**Configuration:**
```env
WEAVIATE_URL=https://your-cluster.weaviate.cloud
WEAVIATE_ADMIN_KEY=your_admin_key
WEAVIATE_COLLECTION=LegalKnowledgeBase  # Collection name
```

##### Collection Schema
```python
def _ensure_collection_exists(self):
    """Create collection with proper schema if it doesn't exist."""
    self.client.collections.create(
        name=WEAVIATE_COLLECTION,
        vectorizer_config=Configure.Vectorizer.text2vec_openai(
            model="text-embedding-3-small"
        ),
        properties=[
            Property(name="content", data_type=DataType.TEXT),
            Property(name="filename", data_type=DataType.TEXT),
            Property(name="chunk_id", data_type=DataType.INT),
            Property(name="metadata", data_type=DataType.TEXT),
        ]
    )
```

**Schema Details:**
- **content**: The text content of the chunk
- **filename**: Original PDF filename
- **chunk_id**: Sequential ID within the document
- **metadata**: JSON string with additional metadata
- **Vectorizer**: Uses OpenAI's text-embedding-3-small model

#### Core Methods

##### 1. `upsert_document_chunks()`
```python
def upsert_document_chunks(self, chunks: List[str], 
                          filename: str, 
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Upsert document chunks to Weaviate.
    
    Args:
        chunks (List[str]): List of text chunks
        filename (str): Source document name
        metadata (Dict): Additional metadata
    
    Returns:
        Dict: {
            'status': 'success' | 'partial_success',
            'total_chunks': int,
            'successful_insertions': int,
            'failed_insertions': int,
            'filename': str,
            'errors': List[str] | None
        }
    """
```

**Implementation:**
```python
collection = self.client.collections.get(WEAVIATE_COLLECTION)

objects_to_insert = []
for idx, chunk in enumerate(chunks):
    obj = {
        "content": chunk,
        "filename": filename,
        "chunk_id": idx,
        "metadata": str(metadata) if metadata else "{}"
    }
    objects_to_insert.append(obj)

response = collection.data.insert_many(objects_to_insert)
```

**Features:**
- Batch insertion for efficiency
- Automatic embedding generation by Weaviate
- Error tracking per chunk
- Detailed response with success/failure counts

##### 2. `search_similar()`
```python
def search_similar(self, query: str, k: int = 5, 
                  filename: str = None) -> List[Dict[str, Any]]:
    """
    Search for similar chunks using vector similarity.
    
    Args:
        query (str): Search query
        k (int): Number of results
        filename (str): Optional filename filter
    
    Returns:
        List[Dict]: [
            {
                'content': str,
                'filename': str,
                'chunk_id': int,
                'distance': float,
                'metadata': str
            }
        ]
    """
```

**Implementation:**
```python
if filename:
    response = collection.query.near_text(
        query=query,
        limit=k,
        return_metadata=["distance"],
        filters=Filter.by_property("filename").equal(filename)
    )
else:
    response = collection.query.near_text(
        query=query,
        limit=k,
        return_metadata=["distance"]
    )
```

**Features:**
- Vector similarity search
- Optional filename filtering
- Returns distance scores
- Sorted by relevance

##### 3. `delete_by_filename()`
```python
def delete_by_filename(self, filename: str) -> Dict[str, Any]:
    """
    Delete all chunks for a specific document.
    
    Args:
        filename (str): Name of file to delete
    
    Returns:
        Dict: {
            'status': 'success',
            'filename': str,
            'deleted_count': int
        }
    """
```

##### 4. `get_collection_stats()`
```python
def get_collection_stats(self) -> Dict[str, Any]:
    """
    Get collection statistics.
    
    Returns:
        Dict: {
            'collection_name': str,
            'total_objects': int,
            'status': 'active'
        }
    """
```

#### Convenience Functions

##### `upsert_to_weaviate()`
```python
def upsert_to_weaviate(chunks: List[str], 
                       filename: str, 
                       metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convenience function for one-off upsertion.
    Automatically handles connection management.
    """
    store = WeaviateVectorStore()
    try:
        return store.upsert_document_chunks(chunks, filename, metadata)
    finally:
        store.close()
```

##### `search_weaviate()`
```python
def search_weaviate(query: str, k: int = 5, 
                   filename: str = None) -> List[Dict[str, Any]]:
    """
    Convenience function for searching.
    Automatically handles connection management.
    """
    store = WeaviateVectorStore()
    try:
        return store.search_similar(query, k, filename)
    finally:
        store.close()
```

---

## Usage

### 1. Via API Endpoint

```python
import requests

# Upload a PDF
with open('contract.pdf', 'rb') as f:
    response = requests.post(
        'http://127.0.0.1:8000/upload_legal_pdf',
        files={'file': f}
    )

result = response.json()
print(f"Processed {result['chunks']} chunks")
```

### 2. Programmatic Usage

```python
from RAG.preprocessor import build_legal_rag_index
import asyncio

async def process_document():
    chunks = await build_legal_rag_index(
        pdf_path="/path/to/document.pdf",
        filename="document.pdf"
    )
    print(f"Processed {chunks} chunks")

asyncio.run(process_document())
```

### 3. Direct Weaviate Operations

```python
from RAG.weaviate_vectorizer import WeaviateVectorStore

# Initialize connection
store = WeaviateVectorStore()

# Upsert chunks
result = store.upsert_document_chunks(
    chunks=["Chunk 1 text", "Chunk 2 text"],
    filename="example.pdf",
    metadata={"author": "John Doe", "date": "2025-01-01"}
)

print(f"Inserted {result['successful_insertions']} chunks")

# Search
results = store.search_similar("contract terms", k=5)
for r in results:
    print(f"Found: {r['content'][:100]}...")

# Cleanup
store.close()
```

---

## Integration with Current Development

### 1. FastAPI Endpoint (`main.py`)

The upsertion process is triggered by the `/upload_legal_pdf` endpoint:

```python
@app.post("/upload_legal_pdf")
async def upload_legal_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF document."""
    tmp_path = None
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # Process and upsert
        total_chunks = await build_legal_rag_index(tmp_path, file.filename)

        return {
            "message": f"PDF '{file.filename}' processed successfully",
            "chunks": total_chunks
        }
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
```

### 2. RAG Retrieval (`ai_service/agent.py`)

The chatbot uses the upserted chunks for context retrieval:

```python
from RAG.retriever import RAGRetriever

class ChatAgent:
    def __init__(self, payload):
        self.retriever = RAGRetriever()
    
    async def ai_agent(self):
        # Retrieve relevant context from Weaviate
        context = self.retriever.retrieve_context(
            query=self.message,
            k=5  # Top 5 most relevant chunks
        )
        
        # Generate response with context
        response = await self.llm.generate(
            prompt=self.format_prompt(context)
        )
        return response
```

### 3. Context Retrieval Flow

```
User Query
    ↓
[Vector Search]
    ↓
Weaviate.search_similar(query)
    ↓
[Top K Chunks Retrieved]
    ↓
[Formatted as Context]
    ↓
LLM Prompt + Context
    ↓
Generated Response
```

### 4. Dual Storage Strategy

**Why Both FAISS and Weaviate?**

| Feature | FAISS | Weaviate |
|---------|-------|----------|
| Speed | Very Fast | Fast |
| Persistence | File-based | Cloud DB |
| Scalability | Limited by memory | Highly scalable |
| Updates | Rebuild required | Real-time updates |
| Use Case | Development, quick queries | Production, persistent storage |

**Current Implementation:**
- Both stores are updated simultaneously
- Weaviate is primary for production
- FAISS provides local backup/development

---

## API Reference

### Upsertion Functions

#### `upsert_to_weaviate()`
```python
def upsert_to_weaviate(
    chunks: List[str],
    filename: str,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]
```

**Parameters:**
- `chunks`: List of text chunks to upsert
- `filename`: Source document filename
- `metadata`: Optional metadata dictionary

**Returns:**
```python
{
    "status": "success",  # or "partial_success"
    "total_chunks": 10,
    "successful_insertions": 10,
    "failed_insertions": 0,
    "filename": "document.pdf",
    "errors": None  # or list of error messages
}
```

#### `search_weaviate()`
```python
def search_weaviate(
    query: str,
    k: int = 5,
    filename: str = None
) -> List[Dict[str, Any]]
```

**Parameters:**
- `query`: Search query string
- `k`: Number of results to return
- `filename`: Optional filter by filename

**Returns:**
```python
[
    {
        "content": "Chunk text content...",
        "filename": "document.pdf",
        "chunk_id": 0,
        "distance": 0.234,  # Lower is more similar
        "metadata": "{...}"
    }
]
```

### HTTP Endpoints

#### `POST /upload_legal_pdf`
Upload and process a PDF document.

**Request:**
```
Content-Type: multipart/form-data
file: <PDF file>
```

**Response:**
```json
{
    "message": "PDF 'document.pdf' processed successfully",
    "chunks": 25
}
```

#### `POST /weaviate_search`
Search for similar document chunks.

**Request:**
```
Content-Type: application/x-www-form-urlencoded
query: "contract terms"
k: 5
filename: "document.pdf" (optional)
```

**Response:**
```json
{
    "status": "success",
    "query": "contract terms",
    "results_count": 5,
    "results": ["..."]
}
```

#### `GET /weaviate_stats`
Get collection statistics.

**Response:**
```json
{
    "collection_name": "LegalKnowledgeBase",
    "total_objects": 150,
    "status": "active"
}
```

#### `POST /weaviate_delete`
Delete all chunks for a document.

**Request:**
```
Content-Type: application/x-www-form-urlencoded
filename: "document.pdf"
```

**Response:**
```json
{
    "status": "success",
    "filename": "document.pdf",
    "deleted_count": 25
}
```

---

## Error Handling

### Common Errors and Solutions

#### 1. No Text Extracted
```python
ValueError: No text extracted from PDF
```

**Causes:**
- PDF contains only images with no OCR
- Tesseract not installed or not in PATH
- Corrupted PDF file

**Solutions:**
- Install Tesseract: `brew install tesseract` (macOS)
- Set `TESSERACT_CMD` in `.env`
- Verify PDF integrity

#### 2. Weaviate Connection Failed
```python
WeaviateGRPCUnavailableError: gRPC health check failed
```

**Causes:**
- Network firewall blocking gRPC port
- Invalid Weaviate credentials
- Weaviate cluster down

**Solutions:**
- Code uses `skip_init_checks=True` to bypass gRPC
- Verify `WEAVIATE_URL` and `WEAVIATE_ADMIN_KEY` in `.env`
- Check Weaviate Cloud dashboard

#### 3. Embedding API Error
```python
OpenAIError: Rate limit exceeded
```

**Causes:**
- Too many API calls
- Exceeded OpenAI quota

**Solutions:**
- Add retry logic with exponential backoff
- Reduce `OCR_WORKERS` in `.env`
- Upgrade OpenAI plan

#### 4. Memory Issues
```python
MemoryError: Cannot allocate memory
```

**Causes:**
- Large PDF with many pages
- Too many concurrent OCR workers

**Solutions:**
- Reduce `OCR_WORKERS` to 1
- Process PDFs in batches
- Increase system memory

---

## Performance Considerations

### Optimization Tips

#### 1. OCR Performance
```env
# Optimal for most systems
OCR_WORKERS=2

# For powerful machines
OCR_WORKERS=4

# For limited resources
OCR_WORKERS=1
```

#### 2. Chunking Strategy
```python
# Current settings
chunk_size=1000      # Characters per chunk
chunk_overlap=200    # Overlap for context preservation

# For shorter responses
chunk_size=500
chunk_overlap=100

# For longer context
chunk_size=1500
chunk_overlap=300
```

#### 3. Batch Processing
For multiple documents:
```python
async def process_multiple_documents(pdf_paths: List[str]):
    tasks = [
        build_legal_rag_index(path, Path(path).name)
        for path in pdf_paths
    ]
    results = await asyncio.gather(*tasks)
    return sum(results)
```

#### 4. Caching
Consider caching processed documents:
```python
import hashlib

def get_pdf_hash(pdf_path: str) -> str:
    """Get hash of PDF for caching."""
    with open(pdf_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

# Check if already processed
pdf_hash = get_pdf_hash(pdf_path)
if not is_already_processed(pdf_hash):
    await build_legal_rag_index(pdf_path, filename)
```

### Benchmarks

Typical processing times (300 DPI, OCR_WORKERS=2):

| Pages | Time | Chunks |
|-------|------|--------|
| 5 | ~30s | ~15 |
| 10 | ~1m | ~30 |
| 50 | ~5m | ~150 |
| 100 | ~10m | ~300 |

*Times vary based on:*
- PDF quality and complexity
- System specifications
- Network speed (Weaviate uploads)
- OCR_WORKERS setting

---

## Best Practices

### 1. Error Logging
Always log errors for debugging:
```python
logger.error(f"Failed to process {filename}: {str(e)}", exc_info=True)
```

### 2. Resource Cleanup
Ensure connections are closed:
```python
store = WeaviateVectorStore()
try:
    result = store.upsert_document_chunks(...)
finally:
    store.close()
```

### 3. Metadata Management
Store useful metadata:
```python
metadata = {
    "upload_date": datetime.now().isoformat(),
    "user_id": user_id,
    "document_type": "contract",
    "language": "en"
}
```

### 4. Testing
Test with sample documents:
```bash
python test_weaviate.py
```

### 5. Monitoring
Track upsertion metrics:
- Processing time per document
- Success/failure rates
- Chunk counts
- Storage usage

---

## Conclusion

The upsertion functionality is the backbone of the Document AI Chatbot's RAG system. It enables:

1. **Efficient Document Processing**: OCR → Chunking → Embedding
2. **Scalable Storage**: Dual FAISS + Weaviate approach
3. **Semantic Search**: Vector similarity for relevant retrieval
4. **Production-Ready**: Error handling, logging, monitoring

For questions or issues, refer to:
- [Weaviate Integration Guide](WEAVIATE_INTEGRATION.md)
- [Quick Start Guide](QUICKSTART.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)

