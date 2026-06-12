# Document AI Chat - System Architecture

## Table of Contents

1. [Overview](#overview)
2. [Current Architecture](#current-architecture)
3. [Component Details](#component-details)
4. [AWS Deployment Architecture](#aws-deployment-architecture)
5. [Future Enhancements](#future-enhancements)
6. [Data Flow Diagrams](#data-flow-diagrams)

---

## Overview

Document AI Chat is a multi-tenant legal document assistant powered by RAG (Retrieval-Augmented Generation) technology. The system enables users to upload legal PDFs, extract text via OCR, store document embeddings in a vector database, and interact with an AI agent that provides context-aware responses.

---

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT APPLICATIONS                               │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────┐   │
│  │  Web Client  │   │ Mobile Client│   │  API Client  │   │ Test Client │   │ 
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬──────┘   │
│         │                  │                  │                  │          │
└─────────┼──────────────────┼──────────────────┼──────────────────┼───────-──┘
          │                  │                  │                  │
          └──────────────────┴──────────────────┴──────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI APPLICATION (main.py)                       │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         API ENDPOINTS                                  │ │
│  │                                                                        │ │
│  │  • POST /upload_legal_pdf    - Upload & process PDF documents          │ │
│  │  • POST /chat                - Chat with AI agent (RAG)                │ │
│  │  • POST /weaviate_search     - Vector similarity search                │ │
│  │  • POST /clear_session       - Clear conversation memory               │ │
│  │  • POST /delete_tenant       - GDPR-compliant tenant deletion          │ │
│  │  • GET  /weaviate_stats      - Get collection statistics               │ │
│  │  • POST /weaviate_delete     - Delete document by filename             │ │
│  │  • GET  /health              - Health check                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
          │                                          │
          │                                          │
          ▼                                          ▼
┌──────────────────────────┐            ┌──────────────────────────┐
│  DOCUMENT PROCESSING     │            │    AI CHAT SERVICE       │
│  PIPELINE (OCR → RAG)    │            │   (Agent + Memory)       │
└──────────────────────────┘            └──────────────────────────┘
          │                                          │
          │                                          │
          ▼                                          ▼

┌────────────────────────────────────────────────────────────────────────────┐
│                              CORE SERVICES                                 │
│                                                                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────--─┐    │
│  │   OCR SERVICE    │  │  RAG PROCESSING  │  │   SESSION MANAGER      │    │
│  │ (text_extraction)│  │  (preprocessor)  │  │  (In-Memory Storage)   |    │
│  │                  │  │                  │  │                        │    │
│  │  • PyMuPDF       │  │  • Text Chunking │  │  • ConversationBuffer  │    │
│  │  • Tesseract OCR │  │  • Vectorization │  │  • Per-Tenant Memory   │    │
│  │  • Async Workers │  │  • Embedding     │  │  • Thread-Safe Dict    │    │
│  └────────┬─────────┘  └────────┬─────────┘  └───────────┬────────────┘    │
│           │                     │                        │                 │
│           └─────────┬───────────┘                        │                 │
│                     │                                    │                 │
└─────────────────────┼────────────────────────────────────┼─────────────────┘
                      │                                    │
                      ▼                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                             AI AGENT SYSTEM                                 │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         CHAT AGENT (agent.py)                        │   │
│  │                                                                      │   │
│  │  ┌────────────────┐      ┌────────────────┐     ┌────────────────┐   │   │
│  │  │   LangChain    │      │   AgentPrompt  │     │  Tool System   │   │   │
│  │  │  AgentExecutor │  ──▶ │   Template     │ ──▶ │  (Retriever)   │   │   │
│  │  └────────────────┘      └────────────────┘     └────────────────┘   │   │
│  │         │                                               │            │   │
│  │         │                                               │            │   │
│  │         ▼                                               ▼            │   │
│  │  ┌────────────────┐                              ┌──────────────┐    │   │
│  │  │  OpenAI GPT    │◀─────────────────────────────│  Weaviate    │    │   │
│  │  │  (gpt-4o-mini) │      Inject Context          │  Retriever   │    │   │
│  │  └────────────────┘                              └──────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                      │                                     │
                      ▼                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                   │
│                                                                              │
│  ┌──────────────────────────────┐      ┌────────────────────────────────┐  │
│  │       OPENAI SERVICES        │      │      WEAVIATE CLOUD            │  │
│  │                              │      │   (Vector Database)            │  │
│  │  ┌──────────────────────┐   │      │                                │  │
│  │  │ text-embedding-3-small│   │      │  Collection: LegalKnowledgeBase│  │
│  │  │  (Vectorization)      │   │      │                                │  │
│  │  └──────────────────────┘   │      │  Properties:                   │  │
│  │                              │      │  • content (TEXT)              │  │
│  │  ┌──────────────────────┐   │      │  • filename (TEXT)             │  │
│  │  │   gpt-4o-mini         │   │      │  • tenant_id (TEXT)            │  │
│  │  │  (Chat Completion)    │   │      │  • chunk_id (INT)              │  │
│  │  └──────────────────────┘   │      │  • metadata (TEXT)             │  │
│  │                              │      │  • vector (auto-generated)     │  │
│  └──────────────────────────────┘      │                                │  │
│                                         │  Multi-Tenant Isolation:       │  │
│                                         │  • Tenant-based filtering      │  │
│                                         │  • GDPR-compliant deletion     │  │
│                                         └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. FastAPI Application Layer

**Location**: `main.py`

The main entry point providing REST API endpoints for document management, chat interaction, and system administration.

**Key Features**:

- Async request handling
- Multi-tenant support
- Temporary file management
- Comprehensive error handling
- Health monitoring

---

### 2. OCR Service

**Location**: `OCR/text_extraction.py`

Extracts text from scanned PDF documents using Tesseract OCR.

**Architecture**:

```
PDF Upload
    │
    ▼
PyMuPDF (fitz)
    │
    ├──▶ Page Rendering (High DPI: 300)
    │
    ├──▶ Image Processing
    │      ├─ Grayscale Conversion
    │      ├─ Negative Detection & Inversion
    │      └─ Binarization (Threshold: 180)
    │
    └──▶ Tesseract OCR (Parallel Workers)
           │
           ▼
     Extracted Text
```

**Performance**:

- Async/Parallel Processing
- Configurable OCR Workers (Default: 2)
- Semaphore-based Concurrency Control
- Page-by-Page Progress Logging

---

### 3. RAG Processing Pipeline

**Location**: `RAG/preprocessor.py`, `RAG/vectorizer.py`

Handles document chunking, embedding, and vector storage.

**Workflow**:

```
PDF Text
    │
    ▼
Text Chunking (DocUtils)
    │
    ├─ Chunk Size: Configurable
    ├─ Overlap: Smart overlap for context
    │
    ▼
OpenAI Embeddings
    │
    ├─ Model: text-embedding-3-small
    ├─ Dimension: 1536 (default)
    │
    ▼
Weaviate Upsert
    │
    ├─ Collection: LegalKnowledgeBase
    ├─ Tenant Isolation: tenant_id filtering
    ├─ Batch Insert: Optimized performance
    │
    ▼
Vector Store (Persistent)
```

**Key Features**:

- Automatic vectorization by Weaviate
- Multi-tenant data isolation
- Batch processing for efficiency
- Error handling with partial success support

---

### 4. Session Manager

**Location**: `ai_service/session_manager.py`

Manages conversation memory per tenant using in-memory storage.

**Current Implementation**:

```python
SessionManager
    │
    ├─ Storage: In-Memory Dictionary
    │   └─ Key: tenant_id
    │   └─ Value: ConversationBufferMemory
    │
    ├─ Thread Safety: asyncio.Lock()
    │
    └─ Operations:
        ├─ get_memory(session_id)
        └─ clear_memory(session_id)
```

**Limitations**:

- ❌ Not persistent (lost on restart)
- ❌ Not scalable across multiple instances
- ❌ Memory grows unbounded per session

---

### 5. AI Agent System

**Location**: `ai_service/agent.py`

LangChain-based agent orchestrating retrieval and generation.

**Architecture**:

```
User Query
    │
    ▼
┌────────────────────────┐
│   ChatAgent            │
│                        │
│  1. Load Memory        │
│     (ConversationBuffer)│
│                        │
│  2. Create Tools       │
│     ┌──────────────┐   │
│     │ Retriever Tool│   │
│     │ (Weaviate)   │   │
│     └──────────────┘   │
│                        │
│  3. Build Prompt       │
│     (System + Context) │
│                        │
│  4. Agent Executor     │
│     ┌──────────────┐   │
│     │ Tool Calling │   │
│     │ Reasoning    │   │
│     └──────────────┘   │
│                        │
│  5. Response           │
└────────────────────────┘
    │
    ▼
Structured Output
    ├─ status
    ├─ tenantId
    ├─ response
    └─ time
```

**RAG Flow**:

1. User asks a question
2. Agent decides if retrieval is needed
3. Calls `legal_retriever` tool with tenant filtering
4. Weaviate returns top-k relevant chunks
5. Context injected into LLM prompt
6. GPT generates response with context
7. Response saved to conversation memory

---

### 6. Weaviate Vector Store

**Location**: `RAG/vectorizer.py`

Cloud-hosted vector database for semantic search.

**Features**:

- ✅ Cloud-native (Weaviate Cloud)
- ✅ Persistent storage
- ✅ Multi-tenant isolation
- ✅ Semantic search via cosine similarity
- ✅ GDPR-compliant deletion
- ✅ Auto-vectorization with OpenAI

**Query Filtering**:

```python
# Tenant-specific search
filter = Filter.by_property("tenant_id").equal(tenant_id)

# File-specific search
filter = Filter.by_property("filename").equal(filename)

# Combined filtering
filter = Filter.all_of([tenant_filter, file_filter])
```

---

## AWS Deployment Architecture

### Option 1: Lambda-Based Serverless (Recommended for Cost Efficiency)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AWS CLOUD INFRASTRUCTURE                          │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         CLOUDFRONT CDN (Optional)                    │   │
│  │                   Global Edge Locations, SSL/TLS                     │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        API GATEWAY (REST/HTTP)                       │   │
│  │                                                                      │   │
│  │  • Rate Limiting & Throttling                                       │   │
│  │  • API Key Management                                               │   │
│  │  • Request/Response Transformation                                  │   │
│  │  • CloudWatch Logging                                               │   │
│  └──────────┬────────────────────────┬────────────────┬─────────────────┘   │
│             │                        │                │                     │
│             ▼                        ▼                ▼                     │
│  ┌─────────────────┐    ┌────────────────────┐   ┌──────────────────┐     │
│  │  LAMBDA FUNCTION│    │  LAMBDA FUNCTION   │   │ LAMBDA FUNCTION  │     │
│  │  (PDF Upload &  │    │   (Chat Endpoint)  │   │ (Admin Functions)│     │
│  │   Processing)   │    │                    │   │                  │     │
│  │                 │    │                    │   │  • Clear Session │     │
│  │  • OCR Extract  │    │  • Agent Executor  │   │  • Delete Tenant │     │
│  │  • Chunking     │    │  • RAG Retrieval   │   │  • Stats Query   │     │
│  │  • Embedding    │    │  • Memory Access   │   │                  │     │
│  │  • Weaviate     │    │  • Weaviate Search │   │                  │     │
│  │    Upsert       │    │  • OpenAI Chat     │   │                  │     │
│  │                 │    │                    │   │                  │     │
│  │  Timeout: 900s  │    │  Timeout: 300s     │   │  Timeout: 60s    │     │
│  │  Memory: 3GB    │    │  Memory: 1GB       │   │  Memory: 512MB   │     │
│  └────────┬────────┘    └──────────┬─────────┘   └────────┬─────────┘     │
│           │                        │                       │                │
│           │                        │                       │                │
└───────────┼────────────────────────┼───────────────────────┼────────────────┘
            │                        │                       │
            │                        │                       │
            ▼                        ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STORAGE & PERSISTENCE LAYER                         │
│                                                                              │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────┐   │
│  │   AMAZON S3      │   │  ELASTICACHE     │   │   AMAZON RDS         │   │
│  │  (File Storage)  │   │  (Redis)         │   │  (PostgreSQL)        │   │
│  │                  │   │                  │   │                      │   │
│  │  • Uploaded PDFs │   │  • Session Cache │   │  • Chat History      │   │
│  │  • Temp Storage  │   │  • Current Conv. │   │  • User Sessions     │   │
│  │  • Lifecycle     │   │  • TTL: 1 hour   │   │  • Document Metadata │   │
│  │    Rules         │   │  • Fast Access   │   │  • Audit Logs        │   │
│  └──────────────────┘   └──────────────────┘   └──────────────────────┘   │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
            │                        │                       │
            │                        │                       │
            ▼                        ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                  │
│                                                                             │
│  ┌──────────────────────────────┐      ┌────────────────────────────────┐   │
│  │       OPENAI API             │      │      WEAVIATE CLOUD            │   │
│  │  (Via VPC Endpoint if needed)│      │   (Vector Database)            │   │
│  └──────────────────────────────┘      └────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
            │                                            │
            ▼                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MONITORING & OBSERVABILITY                           │
│                                                                             │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────┐     │
│  │  CLOUDWATCH      │   │  X-RAY           │   │  SNS ALERTS          │     │
│  │  (Logs, Metrics) │   │  (Tracing)       │   │  (Notifications)     │     │
│  └──────────────────┘   └──────────────────┘   └──────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Lambda Configuration**:


| Function           | Timeout       | Memory | Trigger     | Use Case                            |
| ------------------ | ------------- | ------ | ----------- | ----------------------------------- |
| `upload-processor` | 900s (15 min) | 3GB    | API Gateway | OCR + Embedding (long-running)      |
| `chat-handler`     | 300s (5 min)  | 1GB    | API Gateway | RAG queries, agent execution        |
| `admin-functions`  | 60s           | 512MB  | API Gateway | Clear session, delete tenant, stats |


**Pros**:

- ✅ Pay-per-use pricing
- ✅ Auto-scaling
- ✅ No server management
- ✅ Cost-effective for variable traffic

**Cons**:

- ❌ Cold start latency (~1-3s)
- ❌ 15-minute max timeout (can be limiting for large PDFs)
- ❌ Stateless (requires external state management)

**Estimated Cost** (monthly):

- API Gateway: ~$3.50/million requests
- Lambda: ~$0.20 per million requests + compute time
- S3: ~$0.023/GB
- Redis: ~$15-50 (t3.small ElastiCache)
- RDS: ~$25-100 (t3.small PostgreSQL)
- **Total: ~$50-200/month** (low to medium traffic)

---

### Option 2: EC2-Based Deployment (Recommended for Low Latency)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AWS CLOUD INFRASTRUCTURE                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     APPLICATION LOAD BALANCER (ALB)                 │    │
│  │                                                                     │    │
│  │  • SSL/TLS Termination                                              │    │
│  │  • Health Checks                                                    │    │
│  │  • Path-Based Routing                                               │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                           │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     AUTO SCALING GROUP (ASG)                        │    │
│  │                                                                     │    │
│  │  Min: 1 instance  │  Desired: 2 instances  │  Max: 5 instances      │    │
│  │                                                                     │    │
│  │  Scaling Triggers:                                                  │    │
│  │  • CPU > 70% → Scale Up                                             │    │
│  │  • CPU < 30% → Scale Down                                           │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                           │
│          ┌──────────────────────┼──────────────────────┐                    │
│          │                      │                      │                    │
│          ▼                      ▼                      ▼                    │
│  ┌──────────────┐       ┌──────────────┐      ┌──────────────┐              │
│  │ EC2 Instance │       │ EC2 Instance │      │ EC2 Instance │              │
│  │  (t3.medium) │       │  (t3.medium) │      │  (t3.medium) │              │
│  │              │       │              │      │              │              │
│  │  Ubuntu 22.04│       │  Ubuntu 22.04│      │  Ubuntu 22.04│              │
│  │              │       │              │      │              │              │
│  │ ┌──────────┐ │       │ ┌──────────┐ │      │ ┌──────────┐ │              │
│  │ │ FastAPI  │ │       │ │ FastAPI  │ │      │ │ FastAPI  │ │              │
│  │ │ Uvicorn  │ │       │ │ Uvicorn  │ │      │ │ Uvicorn  │ │              │
│  │ │ Workers:4│ │       │ │ Workers:4│ │      │ │ Workers:4│ │              │
│  │ └──────────┘ │       │ └──────────┘ │      │ └──────────┘ │              │
│  │              │       │              │      │              │              │
│  │ ┌──────────┐ │       │ ┌──────────┐ │      │ ┌──────────┐ │              │
│  │ │Tesseract │ │       │ │Tesseract │ │      │ │Tesseract │ │              │
│  │ │   OCR    │ │       │ │   OCR    │ │      │ │   OCR    │ │              │
│  │ └──────────┘ │       │ └──────────┘ │      │ └──────────┘ │              │
│  │              │       │              │      │              │              │
│  │ Python 3.12  │       │ Python 3.12  │      │ Python 3.12  │              │
│  └──────┬───────┘       └──────┬───────┘      └──────┬───────┘              │
│         │                      │                      │                     │
└─────────┼──────────────────────┼──────────────────────┼─────────────────────┘
          │                      │                      │
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STORAGE & PERSISTENCE LAYER                        │
│                                                                             │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────┐     │
│  │   AMAZON S3      │   │  ELASTICACHE     │   │   AMAZON RDS         │     │
│  │  (File Storage)  │   │  (Redis Cluster) │   │  (PostgreSQL)        │     │
│  │                  │   │                  │   │                      │     │
│  │  • Uploaded PDFs │   │  • Session Cache │   │  • Chat History      │     │
│  │  • Processed     │   │  • Active Conv.  │   │  • User Data         │     │
│  │    Documents     │   │  • Fast Lookup   │   │  • Document Metadata │     │
│  │  • Lifecycle     │   │  • Multi-AZ      │   │  • Multi-AZ          │     │
│  │    Management    │   │  • Replication   │   │  • Automated Backups │     │
│  └──────────────────┘   └──────────────────┘   └──────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
          │                      │                      │
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                  │
│                                                                             │
│  ┌──────────────────────────────┐      ┌────────────────────────────────┐   │
│  │       OPENAI API             │      │      WEAVIATE CLOUD            │   │
│  │                              │      │   (Vector Database)            │   │
│  └──────────────────────────────┘      └────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**EC2 Configuration**:

- **Instance Type**: t3.medium (2 vCPU, 4 GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Python**: 3.12
- **Web Server**: Uvicorn (4 workers)
- **Reverse Proxy**: Nginx (optional)
- **Process Manager**: systemd or supervisor

**Deployment Stack**:

```
EC2 Instance
    │
    ├─ Nginx (Reverse Proxy)
    │   └─ SSL/TLS, Static Files
    │
    ├─ Uvicorn (ASGI Server)
    │   ├─ Workers: 4
    │   ├─ Port: 8000
    │   └─ Timeout: 300s
    │
    ├─ FastAPI Application
    │   └─ Document AI Chat
    │
    └─ System Dependencies
        ├─ Tesseract OCR
        ├─ Python 3.12
        └─ Required Packages
```

**Pros**:

- ✅ No cold starts
- ✅ Full control over environment
- ✅ Can handle long-running processes
- ✅ Predictable latency

**Cons**:

- ❌ Fixed costs (even with low traffic)
- ❌ Manual scaling management
- ❌ Server maintenance required

**Estimated Cost** (monthly):

- EC2 (2x t3.medium): ~$60
- ALB: ~$20
- S3: ~$10
- Redis: ~$50
- RDS: ~$50
- Data Transfer: ~$10
- **Total: ~$200-250/month**

---

### Option 3: Hybrid Approach (Best of Both Worlds)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HYBRID ARCHITECTURE                            │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                        API GATEWAY                                 │     │
│  └──────────────────────┬──────────────────────┬──────────────────────┘     │
│                         │                      │                            │
│                         ▼                      ▼                            │
│           ┌──────────────────────┐   ┌──────────────────────┐               │
│           │  LAMBDA FUNCTIONS    │   │   EC2 AUTO SCALING   │               │
│           │  (Light Operations)  │   │  (Heavy Operations)  │               │
│           │                      │   │                      │               │
│           │  • /health           │   │  • /upload_legal_pdf │               │
│           │  • /weaviate_stats   │   │    (OCR Processing)  │               │
│           │  • /clear_session    │   │                      │               │
│           │  • /delete_tenant    │   │  • /chat (RAG)       │               │
│           │  • /weaviate_search  │   │                      │               │
│           └──────────────────────┘   └──────────────────────┘               │
│                                                                             │
│  Benefits:                                                                  │
│  • Cost-effective for admin operations                                      │
│  • Low latency for chat (EC2)                                               │
│  • Scalable OCR processing (EC2 ASG)                                        │
│  • No cold starts for critical paths                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Future Enhancements

### Redis + PostgreSQL Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ENHANCED SESSION MANAGEMENT                             │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    NEW SESSION MANAGER                                │  │
│  │                                                                       │  │
│  │  ┌─────────────────────┐          ┌──────────────────────┐          │  │
│  │  │   REDIS CACHE       │          │   POSTGRESQL DB      │          │  │
│  │  │  (ElastiCache)      │          │   (RDS)              │          │  │
│  │  │                     │          │                      │          │  │
│  │  │  • Current Session  │◀────────▶│  • Full Chat History│          │  │
│  │  │  • Last N messages  │  Sync    │  • User Sessions    │          │  │
│  │  │  • TTL: 1 hour      │          │  • Metadata         │          │  │
│  │  │  • Fast Read/Write  │          │  • Long-term Storage│          │  │
│  │  └─────────────────────┘          └──────────────────────┘          │  │
│  │           │                                    │                     │  │
│  └───────────┼────────────────────────────────────┼─────────────────────┘  │
│              │                                    │                         │
│              ▼                                    ▼                         │
│    ┌─────────────────┐                  ┌─────────────────┐                │
│    │  Read Pattern   │                  │  Write Pattern  │                │
│    │                 │                  │                 │                │
│    │  1. Check Redis │                  │  1. Write Redis │                │
│    │  2. If miss →   │                  │  2. Async write │                │
│    │     Query PG    │                  │     to PG       │                │
│    │  3. Cache in    │                  │  3. Expire old  │                │
│    │     Redis       │                  │     cache       │                │
│    └─────────────────┘                  └─────────────────┘                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Database Schema (PostgreSQL)

```sql
-- Users/Tenants Table
CREATE TABLE tenants (
    tenant_id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Chat Sessions Table
CREATE TABLE chat_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW(),
    metadata JSONB,
    INDEX idx_tenant_sessions (tenant_id, last_activity)
);

-- Chat Messages Table
CREATE TABLE chat_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    tenant_id VARCHAR(255) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB,
    INDEX idx_session_messages (session_id, created_at),
    INDEX idx_tenant_messages (tenant_id, created_at)
);

-- Documents Metadata Table
CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_size BIGINT,
    chunk_count INTEGER,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    s3_key VARCHAR(1000),
    metadata JSONB,
    INDEX idx_tenant_documents (tenant_id, uploaded_at)
);

-- Audit Logs Table
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) REFERENCES tenants(tenant_id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_tenant_audit (tenant_id, created_at),
    INDEX idx_action_audit (action, created_at)
);
```

### Redis Data Structure

```python
# Session Cache Key Pattern
session:{tenant_id}:messages = List[
    {
        "role": "user" | "assistant",
        "content": str,
        "timestamp": datetime,
        "message_id": UUID
    }
]

# TTL: 1 hour (3600 seconds)
EXPIRE session:{tenant_id}:messages 3600

# Active Sessions Set
active_sessions = Set[tenant_id]
# TTL: 1 hour

# Session Metadata
session:{tenant_id}:meta = {
    "last_activity": timestamp,
    "message_count": int,
    "session_id": UUID
}
```

### Updated Session Manager Implementation

```python
class SessionManager:
    """
    Enhanced session manager with Redis + PostgreSQL persistence.
    """
    
    @classmethod
    async def get_memory(cls, tenant_id: str) -> ConversationBufferMemory:
        """
        Load conversation from Redis cache, fallback to PostgreSQL.
        """
        # 1. Check Redis cache
        messages = await cls._load_from_redis(tenant_id)
        
        if not messages:
            # 2. Cache miss - load from PostgreSQL
            messages = await cls._load_from_postgres(tenant_id)
            
            # 3. Populate Redis cache
            await cls._cache_to_redis(tenant_id, messages)
        
        # 4. Create memory object
        memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history",
            output_key="output"
        )
        
        # 5. Load messages into memory
        for msg in messages:
            if msg["role"] == "user":
                memory.chat_memory.add_user_message(msg["content"])
            else:
                memory.chat_memory.add_ai_message(msg["content"])
        
        return memory
    
    @classmethod
    async def save_message(cls, tenant_id: str, role: str, content: str):
        """
        Save message to both Redis and PostgreSQL.
        """
        # 1. Save to Redis (immediate)
        await cls._save_to_redis(tenant_id, role, content)
        
        # 2. Save to PostgreSQL (async, non-blocking)
        await cls._save_to_postgres(tenant_id, role, content)
    
    @classmethod
    async def clear_memory(cls, tenant_id: str):
        """
        Clear session from Redis and optionally PostgreSQL.
        """
        # Clear Redis cache
        await cls._clear_redis(tenant_id)
        
        # Optional: Archive to cold storage before deleting
        # await cls._archive_to_s3(tenant_id)
```

---

## Data Flow Diagrams

### 1. Document Upload Flow

```
┌─────────┐
│  Client │
└────┬────┘
     │
     │ POST /upload_legal_pdf
     │ (file + tenant_id)
     │
     ▼
┌──────────────────┐
│  FastAPI Server  │
│                  │
│ 1. Validate      │
│ 2. Save temp     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  OCR Service     │
│                  │
│ 1. PyMuPDF open  │
│ 2. Extract pages │
│ 3. Tesseract OCR │
│ 4. Parallel proc │
└────────┬─────────┘
         │
         │ Extracted Text
         │
         ▼
┌──────────────────┐
│  Preprocessor    │
│                  │
│ 1. Split chunks  │
│ 2. Add metadata  │
└────────┬─────────┘
         │
         │ Chunks[]
         │
         ▼
┌──────────────────┐
│  Vectorizer      │
│                  │
│ 1. OpenAI embed  │
│ 2. Batch prep    │
└────────┬─────────┘
         │
         │ Embeddings + Metadata
         │
         ▼
┌──────────────────┐
│  Weaviate Cloud  │
│                  │
│ 1. Insert batch  │
│ 2. Index vectors │
│ 3. Return result │
└────────┬─────────┘
         │
         │ Success Response
         │
         ▼
┌──────────────────┐
│  Client Response │
│                  │
│ {                │
│   chunks: N,     │
│   filename: X,   │
│   tenant_id: Y   │
│ }                │
└──────────────────┘
```

**Metrics**:

- OCR Processing: ~1-3 seconds/page
- Chunking: <1 second
- Embedding: ~50ms per chunk (batched)
- Weaviate Insert: ~100ms per batch
- **Total**: ~10-60 seconds (depends on PDF size)

---

### 2. Chat Interaction Flow (RAG)

```
┌─────────┐
│  Client │
└────┬────┘
     │
     │ POST /chat
     │ (tenant_id + message)
     │
     ▼
┌────────────────────────┐
│  FastAPI Server        │
│                        │
│ 1. Parse request       │
│ 2. Create ChatAgent    │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  Session Manager       │
│                        │
│ 1. Load memory         │
│    (Redis → PG)        │
│ 2. Return buffer       │
└────────┬───────────────┘
         │
         │ ConversationBufferMemory
         │
         ▼
┌────────────────────────┐
│  ChatAgent             │
│                        │
│ 1. Build prompt        │
│ 2. Create tools        │
│ 3. Init executor       │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  Agent Executor        │
│  (LangChain)           │
│                        │
│ 1. Analyze query       │
│ 2. Decide tool call    │
└────────┬───────────────┘
         │
         │ Tool Call: legal_retriever
         │
         ▼
┌────────────────────────┐
│  Weaviate Search       │
│                        │
│ 1. Vector search       │
│ 2. Filter by tenant    │
│ 3. Return top-k        │
└────────┬───────────────┘
         │
         │ Relevant Chunks
         │
         ▼
┌────────────────────────┐
│  Context Formatter     │
│                        │
│ 1. Format chunks       │
│ 2. Add metadata        │
└────────┬───────────────┘
         │
         │ Formatted Context
         │
         ▼
┌────────────────────────┐
│  OpenAI GPT-4o-mini    │
│                        │
│ 1. Inject context      │
│ 2. Generate response   │
└────────┬───────────────┘
         │
         │ AI Response
         │
         ▼
┌────────────────────────┐
│  Memory Update         │
│                        │
│ 1. Save to Redis       │
│ 2. Async save to PG    │
└────────┬───────────────┘
         │
         │
         ▼
┌────────────────────────┐
│  Client Response       │
│                        │
│ {                      │
│   status: "success",   │
│   response: "...",     │
│   tenantId: "...",     │
│   time: 2.5            │
│ }                      │
└────────────────────────┘
```

**Latency Breakdown**:

- Session load: 5-20ms (Redis) / 50-100ms (PG)
- Vector search: 50-150ms
- GPT-4o-mini: 1-3 seconds
- Memory save: 10-50ms (async)
- **Total**: 1.5-4 seconds (typical)

---

### 3. Memory Management Flow (Future: Redis + PostgreSQL)

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER SENDS MESSAGE                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 SESSION MANAGER: Read Path                       │
│                                                                  │
│  ┌────────────────┐                                             │
│  │ Check Redis    │                                             │
│  │ Key: session:  │                                             │
│  │   {tenant_id}  │                                             │
│  └───────┬────────┘                                             │
│          │                                                       │
│          ├─── Cache Hit ──────┐                                 │
│          │                    │                                 │
│          └─── Cache Miss      │                                 │
│                │              │                                 │
│                ▼              │                                 │
│     ┌────────────────────┐   │                                 │
│     │  Query PostgreSQL  │   │                                 │
│     │                    │   │                                 │
│     │  SELECT * FROM     │   │                                 │
│     │  chat_messages     │   │                                 │
│     │  WHERE tenant_id=X │   │                                 │
│     │  ORDER BY created  │   │                                 │
│     │  LIMIT 50          │   │                                 │
│     └──────────┬─────────┘   │                                 │
│                │              │                                 │
│                │              │                                 │
│                ▼              │                                 │
│     ┌────────────────────┐   │                                 │
│     │  Cache to Redis    │   │                                 │
│     │  TTL: 3600s        │   │                                 │
│     └──────────┬─────────┘   │                                 │
│                │              │                                 │
│                └──────────────┘                                 │
│                       │                                         │
│                       ▼                                         │
│             Return ConversationMemory                           │
│                                                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT PROCESSES                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 SESSION MANAGER: Write Path                      │
│                                                                  │
│  ┌────────────────────────────────────────┐                     │
│  │  1. Write to Redis (Immediate)         │                     │
│  │                                        │                     │
│  │     RPUSH session:{tenant_id}:messages │                     │
│  │     EXPIRE session:{tenant_id} 3600    │                     │
│  │     SADD active_sessions {tenant_id}   │                     │
│  └─────────────────┬──────────────────────┘                     │
│                    │                                             │
│                    │ (Latency: ~5-10ms)                          │
│                    │                                             │
│  ┌─────────────────▼──────────────────────┐                     │
│  │  2. Async Write to PostgreSQL          │                     │
│  │     (Background Task, Non-Blocking)    │                     │
│  │                                        │                     │
│  │     INSERT INTO chat_messages (        │                     │
│  │       tenant_id, role, content,        │                     │
│  │       session_id, created_at           │                     │
│  │     ) VALUES (...)                     │                     │
│  └────────────────────────────────────────┘                     │
│                    │                                             │
│                    │ (Latency: ~50-100ms, async)                 │
│                    │                                             │
│  ┌─────────────────▼──────────────────────┐                     │
│  │  3. Update Session Metadata            │                     │
│  │                                        │                     │
│  │     UPDATE chat_sessions               │                     │
│  │     SET last_activity = NOW()          │                     │
│  │     WHERE session_id = X               │                     │
│  └────────────────────────────────────────┘                     │
│                                                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RETURN TO CLIENT                              │
└─────────────────────────────────────────────────────────────────┘
```

**Benefits**:

- ⚡ Ultra-fast reads (5-20ms from Redis)
- 💾 Persistent storage (PostgreSQL)
- 🔄 Automatic sync between layers
- 📊 Queryable history (SQL analytics)
- 🗑️ GDPR-compliant deletion (cascade)

---

## AWS Deployment Recommendations

### For MVP / Low Budget:

**Lambda + S3 + Redis + RDS (Serverless-First)**

- Estimated Cost: $50-100/month
- Best for: Variable traffic, cost optimization
- Deployment: Serverless Framework / AWS SAM

### For Production / High Traffic:

**EC2 Auto Scaling + ALB + Redis + RDS**

- Estimated Cost: $200-500/month
- Best for: Predictable performance, low latency
- Deployment: Terraform / CloudFormation

### For Enterprise:

**Hybrid: EC2 (chat) + Lambda (admin) + ECS/EKS**

- Estimated Cost: $500-1500/month
- Best for: Scalability, reliability, observability
- Deployment: Kubernetes / ECS with CI/CD

---

## Infrastructure as Code (IaC) Example

### Terraform Configuration (EC2 Deployment)

```hcl
# main.tf

provider "aws" {
  region = "us-east-1"
}

# VPC and Networking
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "document-ai-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  
  enable_nat_gateway = true
  enable_dns_hostnames = true
}

# Application Load Balancer
resource "aws_lb" "document_ai_alb" {
  name               = "document-ai-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = module.vpc.public_subnets
}

# Auto Scaling Group
resource "aws_autoscaling_group" "document_ai_asg" {
  name                = "document-ai-asg"
  vpc_zone_identifier = module.vpc.private_subnets
  target_group_arns   = [aws_lb_target_group.document_ai_tg.arn]
  health_check_type   = "ELB"
  
  min_size         = 1
  max_size         = 5
  desired_capacity = 2
  
  launch_template {
    id      = aws_launch_template.document_ai_lt.id
    version = "$Latest"
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "document_ai_db" {
  identifier        = "document-ai-db"
  engine            = "postgres"
  engine_version    = "15.3"
  instance_class    = "db.t3.small"
  allocated_storage = 20
  
  db_name  = "grantai"
  username = var.db_username
  password = var.db_password
  
  multi_az            = true
  skip_final_snapshot = false
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "document_ai_redis" {
  cluster_id           = "document-ai-redis"
  engine               = "redis"
  node_type            = "cache.t3.small"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  engine_version       = "7.0"
  port                 = 6379
}

# S3 Bucket for Document Storage
resource "aws_s3_bucket" "document_ai_docs" {
  bucket = "document-ai-documents-${var.environment}"
  
  lifecycle_rule {
    enabled = true
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    expiration {
      days = 365
    }
  }
}
```

---

## Monitoring & Observability

### CloudWatch Metrics to Track

```yaml
Application Metrics:
  - Request Count (by endpoint)
  - Response Time (P50, P95, P99)
  - Error Rate (4xx, 5xx)
  - OCR Processing Time
  - Weaviate Query Latency
  - OpenAI API Latency
  
Infrastructure Metrics:
  - EC2 CPU Utilization
  - EC2 Memory Usage
  - ALB Target Health
  - RDS CPU/IOPS
  - Redis Cache Hit Rate
  - S3 Request Count
  
Business Metrics:
  - Documents Uploaded (per tenant)
  - Chat Messages (per tenant)
  - Active Sessions
  - Token Usage (OpenAI costs)
  - Storage Usage (S3, Weaviate)
```

### Alerting Rules

```yaml
Critical Alerts:
  - Error Rate > 5% (5 min window)
  - Response Time > 10s (P95)
  - RDS Connection Pool Exhausted
  - Redis Cache Unavailable
  - OpenAI API Failures > 10%
  
Warning Alerts:
  - CPU > 80% (10 min sustained)
  - Memory > 85%
  - Disk Space > 80%
  - Redis Evictions > 100/min
  - S3 Bucket Size > 90% quota
```

---

## Security Considerations

### 1. API Security

- ✅ API Key Authentication (API Gateway)
- ✅ Rate Limiting (per tenant)
- ✅ Input Validation (Pydantic schemas)
- ✅ CORS Configuration
- ✅ SSL/TLS Encryption (ALB)

### 2. Data Security

- ✅ Encryption at Rest (S3, RDS, EBS)
- ✅ Encryption in Transit (TLS 1.2+)
- ✅ Multi-Tenant Isolation (tenant_id filtering)
- ✅ VPC Private Subnets
- ✅ Security Groups (least privilege)

### 3. Secrets Management

- ✅ AWS Secrets Manager (DB credentials)
- ✅ Environment Variables (API keys)
- ✅ IAM Roles (no hardcoded credentials)
- ✅ Rotation Policies (90 days)

### 4. Compliance

- ✅ GDPR: Right to deletion (delete_tenant endpoint)
- ✅ Data Residency: AWS region selection
- ✅ Audit Logs: CloudWatch + PostgreSQL
- ✅ Data Retention: S3 lifecycle policies

---

## Scalability Considerations

### Horizontal Scaling

```
Current Load: 100 requests/min
    │
    ├─ EC2: 2 instances (t3.medium)
    ├─ Redis: 1 node
    └─ RDS: db.t3.small

Medium Load: 1,000 requests/min
    │
    ├─ EC2: 5 instances (t3.large)
    ├─ Redis: 3-node cluster
    └─ RDS: db.t3.large (Multi-AZ)

High Load: 10,000 requests/min
    │
    ├─ EC2: 20 instances (c5.xlarge)
    ├─ Redis: Redis Cluster (6 shards)
    ├─ RDS: db.r5.xlarge (Read Replicas)
    └─ Weaviate: Dedicated cluster scaling
```

### Optimization Strategies

1. **Caching**: Redis for hot data, CloudFront for static assets
2. **Connection Pooling**: SQLAlchemy, Redis connection pools
3. **Async Processing**: Celery for long-running tasks
4. **Database Indexing**: Composite indexes on (tenant_id, created_at)
5. **Query Optimization**: Limit result sets, pagination
6. **CDN**: CloudFront for PDF delivery
7. **Compression**: Gzip responses, S3 compression

---

## Cost Optimization

### Tips for Reducing AWS Costs

1. **Reserved Instances**: 30-60% savings for predictable workloads
2. **Spot Instances**: 70-90% savings for OCR workers
3. **S3 Lifecycle**: Transition to Glacier after 90 days
4. **CloudWatch**: Reduce log retention to 7-30 days
5. **RDS**: Use Aurora Serverless for variable workloads
6. **Lambda**: Use Provisioned Concurrency only if needed
7. **Data Transfer**: Keep services in same region/AZ

---

## Conclusion

This architecture provides a robust, scalable, and cost-effective foundation for the Document AI Chat system. The design supports both serverless (Lambda) and traditional (EC2) deployment models, with clear paths for future enhancements including Redis/PostgreSQL integration for chat history management.

### Next Steps

1. ✅ Choose deployment model (Lambda vs EC2 vs Hybrid)
2. ✅ Set up AWS infrastructure (Terraform/CloudFormation)
3. ✅ Implement Redis + PostgreSQL session management
4. ✅ Configure monitoring and alerting
5. ✅ Deploy to staging environment
6. ✅ Load testing and optimization
7. ✅ Production deployment with CI/CD pipeline

---

**Document Version**: 1.0  
**Last Updated**: October 28, 2025  
**Author**: Document AI Team