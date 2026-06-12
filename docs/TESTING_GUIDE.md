# 🚀 Local Testing Guide for Grant AI Chatbot

This guide will help you run and test the Grant AI Chatbot locally with PDF upload and chat capabilities.

## Prerequisites

✅ Weaviate connection verified
✅ Dependencies installed in `.venv`
✅ Environment variables configured in `.env`

## Quick Start

### Step 1: Start the Server

Open a terminal and run:

```bash
cd /Users/desh/zitles/grant-ai
source .venv/bin/activate
python main.py
```

Or use the startup script:

```bash
./start_server.sh
```

You should see output like:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 2: Test with the Interactive Client

Open a **NEW terminal** window and run:

```bash
cd /Users/desh/zitles/grant-ai
source .venv/bin/activate
python test_client.py
```

## Interactive Client Commands

Once the interactive client is running, you can use these commands:

### Upload a PDF Document
```
/upload path/to/your/document.pdf
```

Example:
```
/upload ~/Documents/contract.pdf
```

### Chat with the AI
Just type your message and press Enter:
```
What are the main terms in the contract?
Can you explain clause 5?
Summarize the document for me
```

### Search Weaviate
```
/search contract terms
```

### Check Statistics
```
/stats
```

### Clear Conversation History
```
/clear
```

### Exit
```
/quit
```

## Testing with curl (Alternative Method)

If you prefer using curl, here are some examples:

### 1. Health Check
```bash
curl http://127.0.0.1:8000/health
```

### 2. Upload a PDF
```bash
curl -X POST "http://127.0.0.1:8000/upload_legal_pdf" \
  -F "file=@/path/to/your/document.pdf"
```

### 3. Chat with the Bot
```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -F "tenant_id=test_user" \
  -F "message=What are the main points in the document?"
```

### 4. Search Weaviate
```bash
curl -X POST "http://127.0.0.1:8000/weaviate_search" \
  -F "query=contract terms" \
  -F "k=5"
```

### 5. Get Weaviate Stats
```bash
curl http://127.0.0.1:8000/weaviate_stats
```

### 6. Clear Session
```bash
curl -X POST "http://127.0.0.1:8000/clear_session" \
  -F "tenant_id=test_user"
```

### 7. Delete Document
```bash
curl -X POST "http://127.0.0.1:8000/weaviate_delete" \
  -F "filename=your_document.pdf"
```

## Testing Flow Example

Here's a complete testing flow:

### Terminal 1: Start the Server
```bash
cd /Users/desh/zitles/grant-ai
source .venv/bin/activate
python main.py
```

### Terminal 2: Test the Chatbot
```bash
cd /Users/desh/zitles/grant-ai
source .venv/bin/activate
python test_client.py
```

Then in the interactive client:
```
👤 Enter your tenant ID: test_user

💬 You: /upload sample_contract.pdf
📤 Uploading PDF: sample_contract.pdf
✅ Upload successful!

💬 You: What are the main terms in this contract?
🤖 AI: [AI response with relevant information from the document]

💬 You: Can you summarize the payment terms?
🤖 AI: [AI response about payment terms]

💬 You: /stats
📊 Weaviate Collection Stats:
   Collection: LegalKnowledgeBase
   Total Documents: 15

💬 You: /quit
👋 Goodbye!
```

## API Documentation (Swagger)

Once the server is running, you can access the interactive API documentation at:

**Swagger UI:** http://127.0.0.1:8000/docs

**ReDoc:** http://127.0.0.1:8000/redoc

These provide a user-friendly interface to test all endpoints directly in your browser.

## Troubleshooting

### Server Won't Start
- Check if port 8000 is already in use:
  ```bash
  lsof -i :8000
  ```
- Make sure virtual environment is activated:
  ```bash
  which python
  # Should show: /Users/desh/zitles/grant-ai/.venv/bin/python
  ```

### PDF Upload Fails
- Ensure Tesseract OCR is installed:
  ```bash
  tesseract --version
  ```
- If not installed:
  ```bash
  brew install tesseract
  ```

### Chat Doesn't Return Relevant Information
- Make sure you uploaded a PDF first
- Check if Weaviate has documents:
  ```bash
  curl http://127.0.0.1:8000/weaviate_stats
  ```

### Connection Errors
- Verify `.env` file has correct credentials:
  - `OPENAI_API_KEY`
  - `WEAVIATE_URL`
  - `WEAVIATE_ADMIN_KEY`

## Features to Test

1. ✅ **PDF Upload**: Upload a legal document
2. ✅ **Text Extraction**: OCR processes the document
3. ✅ **Vector Storage**: Document chunks stored in Weaviate
4. ✅ **Semantic Search**: Find relevant information
5. ✅ **Chat with Memory**: Conversation history per user
6. ✅ **RAG Integration**: AI answers based on uploaded documents
7. ✅ **Multi-User Support**: Different tenants have separate conversations

## Next Steps

After testing locally, you can:
1. Deploy to a cloud platform (AWS, GCP, Azure)
2. Add authentication and authorization
3. Create a web frontend
4. Add more document types (Word, Excel, etc.)
5. Implement document versioning

## Quick Test Script

Want to automate testing? Run:

```bash
python test_client.py /path/to/test/document.pdf
```

This will:
- Upload the PDF
- Test several chat queries
- Display results

## Support

For issues or questions, refer to:
- Main documentation: `README.md`
- Weaviate integration: `WEAVIATE_INTEGRATION.md`
- Implementation details: `SUCCESS_SUMMARY.md`

---

Happy Testing! 🎉

