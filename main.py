from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from typing import Optional
# from contextlib import asynccontextmanager
from dotenv import load_dotenv
from utils.logging_util import get_logger
from ai_service.agent import ChatAgent
from ai_service.session_manager import SessionManager
from ai_service.hybrid_session_manager import get_hybrid_session_manager
# from RAG.preprocessor import reset_rag_indexes
from RAG.preprocessor import build_legal_rag_index
from RAG.vectorizer import WeaviateVectorStore, search_weaviate

import tempfile
# import asyncio
import os

# Load environment variables
load_dotenv()
logger = get_logger(__name__)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     try:
#         # reset_rag_indexes()
#         logger.info("Grant AI Chatbot starting up...")
#     except Exception as e:
#         logger.error(f"Error resetting RAG indexes: {e}")
#         raise

#     yield

# Initialize FastAPI
app = FastAPI(title="Grant AI Chatbot")

# Health Check
@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "ok"}

# Upload & Index PDF
@app.post("/upload_legal_pdf")
async def upload_legal_pdf(
    file: UploadFile = File(...), 
    userId: str = Form(...),
    fileId: str = Form(...)
):
    """
    Upload a legal PDF, extract its text via OCR, and upsert to Weaviate vector store.
    Automatically deletes the temporary file after processing.
    
    Args:
        file: The PDF file to upload
        userId: The user ID from the backend (e.g., "64e86408-80b1-70f4-c16e-77b2279e6b2b")
        fileId: File ID from S3 upload (e.g., "058d30ca-8134-44ee-bcfe-914225f04fff") - REQUIRED
    
    Returns:
        Dict with upload results including chunks processed
    """
    if not userId:
        raise HTTPException(
            status_code=400, 
            detail="'userId' is required"
        )
    
    if not fileId:
        raise HTTPException(
            status_code=400,
            detail="'fileId' is required"
        )
    
    tmp_path = None
    try:
        # Save uploaded PDF temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # Extract text + embed into Weaviate vector store with userId and fileId
        total_chunks = await build_legal_rag_index(tmp_path, file.filename, userId, fileId)

        return {
            "message": f"PDF '{file.filename}' processed successfully for user '{userId}'",
            "chunks": total_chunks,
            "userId": userId,
            "fileId": fileId,
            "filename": file.filename
        }

    except Exception as e:
        logger.error(f"OCR/Index failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up the temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                logger.info(f"Temporary file {tmp_path} deleted successfully.")
            except Exception as cleanup_error:
                logger.warning(f"Failed to delete temp file {tmp_path}: {cleanup_error}")

# Persistent Chat Endpoint (with session memory)
@app.post("/chat")
async def chat(
    message: str = Form(...),
    userId: str = Form(...)
):
    """
    Chat endpoint that remembers conversation per userId.
    
    Args:
        message: The user's message/query
        userId: The user ID from the backend (e.g., "64e86408-80b1-70f4-c16e-77b2279e6b2b")
    
    Returns:
        Dict with AI response and conversation context
    """
    if not userId:
        raise HTTPException(
            status_code=400, 
            detail="'userId' is required"
        )
    
    try:
        payload = {
            "tenant_id": userId,  # Using userId as tenant_id for consistency with existing code
            "message": message,
        }

        agent = ChatAgent(payload)
        response = await agent.ai_agent()
        
        # Add userId to response
        response["userId"] = userId
        
        return response

    except Exception as e:
        logger.error(f"Chat processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Clear Chat Memory
@app.post("/clear_session")
async def clear_session(tenant_id: str = Form(...), clear_db: bool = Form(False)):
    """
    Clear the conversation memory for a given tenant/user.
    
    Args:
        tenant_id: The tenant/user ID
        clear_db: If True, also clear from PostgreSQL (default: False, only clears Redis cache)
    """
    try:
        # Use hybrid session manager
        hybrid_manager = await get_hybrid_session_manager()
        await hybrid_manager.clear_session(tenant_id, clear_db=clear_db)
        
        return {
            "message": f"Session memory cleared for tenant_id={tenant_id}",
            "redis_cleared": True,
            "postgres_cleared": clear_db
        }
    except Exception as e:
        logger.error(f"Session clear failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Weaviate Search Endpoint
@app.post("/weaviate_search")
async def weaviate_search(
    query: str = Form(...),
    k: int = Form(5),
    userId: Optional[str] = Form(None),
    fileId: Optional[str] = Form(None),
    filename: Optional[str] = Form(None)
):
    """
    Search Weaviate vector store for similar documents.
    
    Args:
        query: Search query text
        k: Number of results to return
        userId: Optional user ID to filter results
        fileId: Optional file ID to filter results
        filename: Optional filename to filter results
    """
    try:
        results = search_weaviate(query, k, filename, userId, fileId)
        return {
            "status": "success",
            "query": query,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Weaviate search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Weaviate Collection Stats
@app.get("/weaviate_stats")
async def weaviate_stats():
    """
    Get statistics about the Weaviate collection.
    """
    try:
        store = WeaviateVectorStore()
        try:
            stats = store.get_collection_stats()
            return stats
        finally:
            store.close()
    except Exception as e:
        logger.error(f"Failed to get Weaviate stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Delete Document from Weaviate
@app.post("/weaviate_delete")
async def weaviate_delete(filename: str = Form(...)):
    """
    Delete all chunks associated with a specific filename from Weaviate.
    """
    try:
        store = WeaviateVectorStore()
        try:
            result = store.delete_by_filename(filename)
            return result
        finally:
            store.close()
    except Exception as e:
        logger.error(f"Weaviate deletion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Delete Tenant Documents from Weaviate
@app.post("/delete_tenant")
async def delete_tenant(tenant_id: str = Form(...)):
    """
    Delete all documents and conversation memory associated with a specific tenant.
    This removes all tenant data from:
    - Weaviate vector store (documents)
    - Redis cache (active sessions)
    - PostgreSQL (chat history)
    
    Args:
        tenant_id: The tenant/user ID to delete
    
    Returns:
        Summary of deletion operations
    """
    try:
        # Delete all documents from Weaviate vector store
        store = WeaviateVectorStore()
        try:
            weaviate_result = store.delete_by_tenant(tenant_id)
        finally:
            store.close()
        
        # Delete from hybrid session manager (Redis + PostgreSQL)
        hybrid_manager = await get_hybrid_session_manager()
        session_result = await hybrid_manager.delete_tenant(tenant_id)
        
        return {
            "status": "success",
            "tenant_id": tenant_id,
            "weaviate_deletion": weaviate_result,
            "session_deletion": session_result,
            "message": f"All data for tenant '{tenant_id}' has been deleted successfully from all systems"
        }
    except Exception as e:
        logger.error(f"Tenant deletion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Get Chat History
@app.get("/chat_history/{tenant_id}")
async def get_chat_history(tenant_id: str, limit: int = 100):
    """
    Get complete chat history for a tenant from PostgreSQL.
    
    Args:
        tenant_id: The tenant/user ID
        limit: Maximum number of messages to retrieve (default 100)
    
    Returns:
        List of chat messages with metadata
    """
    try:
        hybrid_manager = await get_hybrid_session_manager()
        history = await hybrid_manager.get_chat_history(tenant_id, limit=limit)
        
        return {
            "status": "success",
            "tenant_id": tenant_id,
            "message_count": len(history),
            "messages": history
        }
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Get Session Stats
@app.get("/session_stats/{tenant_id}")
async def get_session_stats(tenant_id: str):
    """
    Get statistics about a tenant's chat sessions.
    
    Args:
        tenant_id: The tenant/user ID
    
    Returns:
        Session statistics including message count, session count, cache status
    """
    try:
        hybrid_manager = await get_hybrid_session_manager()
        stats = await hybrid_manager.get_session_stats(tenant_id)
        
        return {
            "status": "success",
            **stats
        }
    except Exception as e:
        logger.error(f"Failed to get session stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Health Check for Database Connections
@app.get("/health/databases")
async def health_databases():
    """
    Check health of Redis and PostgreSQL connections.
    
    Returns:
        Health status for Redis, PostgreSQL, and overall system
    """
    try:
        hybrid_manager = await get_hybrid_session_manager()
        health = hybrid_manager.health_check()
        
        return health
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return {
            "redis": {"status": "unknown"},
            "postgresql": {"status": "unknown"},
            "overall": "unhealthy",
            "error": str(e)
        }


# Run Server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
