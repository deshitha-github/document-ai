# Document AI Chat - Architecture Overview

> **Quick Visual Guide** | For detailed documentation, see [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md)

---

## 🎯 System at a Glance

```
┌─────────────┐
│   CLIENTS   │  Web, Mobile, API
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         FASTAPI APPLICATION             │
│                                         │
│  Upload PDFs → Chat with AI → Manage    │
└──────┬──────────────┬───────────────────┘
       │              │
       ▼              ▼
┌─────────────┐  ┌────────────────┐
│ OCR + RAG   │  │  AI Agent      │
│ Pipeline    │  │  (LangChain)   │
└──────┬──────┘  └────────┬───────┘
       │                  │
       ▼                  ▼
┌──────────────────────────────────┐
│     EXTERNAL SERVICES            │
│                                  │
│  • Weaviate Cloud (Vectors)      │
│  • OpenAI (Embeddings + GPT)     │
│  • Redis (Session Cache)         │
│  • PostgreSQL (History)          │
└──────────────────────────────────┘
```

---

## 🏗️ Core Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      FASTAPI LAYER                             │
│  /upload_legal_pdf  /chat  /weaviate_search  /delete_tenant    │
└────────┬───────────────────────────────┬─────────────────────--┘
         │                               │
         │ PDF PROCESSING                │ CHAT INTERACTION
         │                               │
    ┌────▼────────┐                 ┌────▼──────────┐
    │ OCR Service │                 │  Chat Agent   │
    │             │                 │               │
    │ • PyMuPDF   │                 │ • LangChain   │
    │ • Tesseract │                 │ • Tools       │
    │ • Async     │                 │ • Memory      │
    └────┬────────┘                 └────┬──────────┘
         │                               │
         ▼                               ▼
    ┌────────────┐                 ┌────────────┐
    │Preprocessor│                 │ Retriever  │
    │            │                 │            │
    │ • Chunking │                 │ • Weaviate │
    │ • Metadata │                 │ • Filters  │
    └────┬───────┘                 └────┬───────┘
         │                               │
         ▼                               ▼
    ┌────────────────────────────────────────┐
    │   OpenAI Embeddings + GPT-4o-mini      │
    └────────┬───────────────────────────────┘
             │
             ▼
    ┌────────────────────────────────────────┐
    │        WEAVIATE CLOUD                  │
    │  • Vector Storage                      │
    │  • Semantic Search                     │
    │  • Multi-Tenant Isolation              │
    └────────────────────────────────────────┘
```

---

## 📊 Data Flow

### 1️⃣ Document Upload Flow

```
PDF → OCR Extract → Chunk → Embed → Store in Weaviate
 ↓        ↓          ↓        ↓           ↓
File   Text      Chunks  Vectors   Multi-tenant DB
(3s)   (2s/pg)   (1s)    (50ms)     (100ms)
```

### 2️⃣ Chat Query Flow

```
User Query → Load Memory → Agent Decides → Search Weaviate → GPT Response
     ↓           ↓              ↓               ↓                ↓
 "What is X?"  History    Need context?   Top-K chunks      AI Answer
              (20ms)      (reasoning)      (100ms)          (2-3s)
```

### 3️⃣ RAG Context Injection

```
┌──────────────┐
│  User Query  │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────┐
│  Vector Search (Weaviate)   │
│  Filter: tenant_id          │
└──────┬──────────────────────┘
       │
       ├─► Chunk 1: [Legal text about X...]
       ├─► Chunk 2: [Contract section Y...]
       └─► Chunk 3: [Document clause Z...]
       │
       ▼
┌─────────────────────────────┐
│  Inject into GPT Prompt     │
│  System + Context + Query   │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  GPT-4o-mini Generation     │
└──────┬──────────────────────┘
       │
       ▼
  📤 Response to User
```

---

## ☁️ AWS Deployment Options

### 🚀 Option 1: Serverless (Lambda)

**Best for**: Variable traffic, cost optimization

```
Internet → API Gateway → Lambda Functions → Services
                            ↓
                         ┌─────────────────┐
                         │ Upload Handler  │  15 min timeout
                         │ Chat Handler    │  5 min timeout
                         │ Admin Handler   │  1 min timeout
                         └─────────────────┘
                            ↓
                    S3 + Redis + RDS + Weaviate
```

**💰 Cost**: ~$50-100/month  
**⚡ Performance**: Cold start 1-3s, then fast  
**📈 Scaling**: Automatic, unlimited

---

### 🖥️ Option 2: EC2 + Auto Scaling

**Best for**: Predictable performance, low latency

```
Internet → ALB → [EC2] [EC2] [EC2] → Services
                   ↓     ↓     ↓
                FastAPI Instances (t3.medium)
                   ↓
            Redis + RDS + S3 + Weaviate
```

**💰 Cost**: ~$200-300/month  
**⚡ Performance**: No cold starts, consistent <100ms  
**📈 Scaling**: Auto Scaling Group (1-5 instances)

---

### 🔀 Option 3: Hybrid

**Best for**: Balance cost + performance

```
                  API Gateway
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
   Lambda                        EC2 ASG
(Light Ops)                  (Heavy Ops)
    │                             │
    ├─ /health                    ├─ /upload_legal_pdf
    ├─ /stats                     └─ /chat
    └─ /clear_session
```

**💰 Cost**: ~$100-200/month  
**⚡ Performance**: Mixed (best of both)  
**📈 Scaling**: Smart routing

---

## 🔮 Future Architecture: Memory Management

### Current (In-Memory)

```
┌──────────────────────┐
│  SessionManager      │
│                      │
│  Dict[tenant_id,     │
│       Memory]        │
│                      │
│  ❌ Lost on restart  │
│  ❌ Single instance  │
└──────────────────────┘
```

### Future (Redis + PostgreSQL)

```
┌────────────────────────────────────────┐
│           SESSION FLOW                 │
└────────────────┬───────────────────────┘
                 │
       ┌─────────┴──────────┐
       ▼                    ▼
┌─────────────┐      ┌──────────────┐
│   REDIS     │      │  POSTGRESQL  │
│  (L1 Cache) │◄────►│ (L2 Storage) │
│             │ Sync │              │
│ • Fast      │      │ • Persistent │
│ • Current   │      │ • Full       │
│   session   │      │   history    │
│ • TTL: 1hr  │      │ • Analytics  │
└─────────────┘      └──────────────┘
```

**Benefits**:

- ⚡ 5-20ms read latency (Redis)
- 💾 Persistent chat history (PostgreSQL)
- 🔄 Automatic sync between layers
- 📊 SQL analytics on conversations
- 🌐 Works across multiple servers

---

## 📈 Scalability Comparison


| Load Level    | Users/min | Lambda         | EC2                 | Hybrid       |
| ------------- | --------- | -------------- | ------------------- | ------------ |
| **Low**       | <100      | ✅ Best         | ⚠️ Over-provisioned | ✅ Good       |
| **Medium**    | 100-1000  | ✅ Good         | ✅ Best              | ✅ Best       |
| **High**      | 1000-10K  | ⚠️ Cold starts | ✅ Best              | ✅ Good       |
| **Very High** | >10K      | ❌ Limits       | ✅ Scale out         | ✅ Scale both |


---

## 🔒 Security Layers

```
┌────────────────────────────────────────┐
│  1. API Layer                          │
│     • API Keys, Rate Limiting          │
└────────────────┬───────────────────────┘
                 ▼
┌────────────────────────────────────────┐
│  2. Application Layer                  │
│     • Input Validation, Auth           │
└────────────────┬───────────────────────┘
                 ▼
┌────────────────────────────────────────┐
│  3. Data Layer                         │
│     • Encryption at Rest/Transit       │
│     • Multi-Tenant Isolation           │
└────────────────┬───────────────────────┘
                 ▼
┌────────────────────────────────────────┐
│  4. Infrastructure Layer               │
│     • VPC, Security Groups, IAM        │
└────────────────────────────────────────┘
```

---

## 🎯 Recommended Deployment Path

### Phase 1: MVP (1-2 weeks)

```
✅ Lambda + API Gateway
✅ Weaviate Cloud
✅ OpenAI API
✅ Basic monitoring
```

**Cost**: ~$50/month

---

### Phase 2: Production (2-4 weeks)

```
✅ EC2 Auto Scaling + ALB
✅ Redis (ElastiCache)
✅ PostgreSQL (RDS)
✅ S3 with lifecycle
✅ CloudWatch alerts
```

**Cost**: ~$200-300/month

---

### Phase 3: Enterprise (1-2 months)

```
✅ Multi-region deployment
✅ Read replicas
✅ Advanced monitoring (X-Ray)
✅ CI/CD pipeline
✅ Load testing
✅ Disaster recovery
```

**Cost**: ~$500-1000/month

---

## 📦 Quick Deploy Commands

### Lambda (Serverless Framework)

```bash
# Install Serverless
npm install -g serverless

# Deploy
cd document-ai
serverless deploy --stage prod
```

### EC2 (Terraform)

```bash
# Initialize Terraform
cd infrastructure/terraform
terraform init

# Plan and apply
terraform plan
terraform apply
```

### Docker (ECS/EKS)

```bash
# Build image
docker build -t document-ai:latest .

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <ecr-url>
docker push <ecr-url>/document-ai:latest
```

---

## 🔍 Monitoring Dashboard (Sample Metrics)

```
┌─────────────────────────────────────────────────┐
│  DOCUMENT AI HEALTH DASHBOARD                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  📊 Requests/min:    ████████░░ 856             │
│  ⚡ Avg Latency:      ████░░░░░░ 1.2s            │
│  ❌ Error Rate:      █░░░░░░░░░ 0.3%            │
│  💾 Redis Hit Rate:  █████████░ 94%             │
│  🔍 Weaviate QPS:    ███████░░░ 142             │
│  💰 OpenAI Cost:     ████░░░░░░ $12.50/day      │
│  👥 Active Sessions: ██████░░░░ 328             │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🚨 Key Performance Targets


| Metric             | Target    | Critical  |
| ------------------ | --------- | --------- |
| **API Response**   | <3s (P95) | <10s      |
| **OCR Processing** | <5s/page  | <15s/page |
| **Vector Search**  | <200ms    | <1s       |
| **Memory Load**    | <50ms     | <200ms    |
| **Error Rate**     | <1%       | >5%       |
| **Uptime**         | >99.5%    | <95%      |


---

## 📚 Tech Stack Summary


| Layer        | Technology          | Purpose            |
| ------------ | ------------------- | ------------------ |
| **API**      | FastAPI             | REST endpoints     |
| **OCR**      | Tesseract + PyMuPDF | PDF extraction     |
| **AI**       | LangChain + OpenAI  | Agent + generation |
| **Vectors**  | Weaviate Cloud      | Semantic search    |
| **Cache**    | Redis (future)      | Session cache      |
| **Database** | PostgreSQL (future) | Chat history       |
| **Storage**  | S3                  | Document storage   |
| **Deploy**   | Lambda/EC2          | Compute            |
| **Monitor**  | CloudWatch          | Observability      |


---

## 🎓 Key Takeaways

1. **Multi-Tenant by Design**: Every query filters by `tenant_id` - complete data isolation
2. **RAG-Powered Chat**: AI augmented with relevant document context via vector search
3. **Async Processing**: OCR runs in parallel, non-blocking operations throughout
4. **Cloud-Native**: Weaviate Cloud for vectors, ready for Redis/PostgreSQL
5. **AWS-Ready**: Three deployment options (Lambda, EC2, Hybrid) - pick based on needs
6. **Cost-Effective**: Start at $50/month (Lambda) or $200/month (EC2)
7. **Scalable**: Auto-scaling from 1 to 1000s of concurrent users
8. **Secure**: Multi-layer security, GDPR-compliant deletion

---

## 🔗 Related Documents

- **[Detailed Architecture](./ARCHITECTURE_DIAGRAM.md)** - In-depth technical documentation
- **[Quick Start Guide](./QUICKSTART.md)** - Get started in 5 minutes
- **[Weaviate Integration](./WEAVIATE_INTEGRATION.md)** - Vector database setup
- **[Implementation Summary](./IMPLEMENTATION_SUMMARY.md)** - Current system overview

---

**Version**: 1.0 | **Last Updated**: October 28, 2025 | **Status**: Production-Ready 🚀