"""
Weaviate Vector Store Integration
Handles document upsertion (embedding + storage) and retrieval from Weaviate Cloud.
"""
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType
from langchain_openai import OpenAIEmbeddings
from utils.logging_util import get_logger

load_dotenv()
logger = get_logger(__name__)

# Environment variables
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_ADMIN_KEY = os.getenv("WEAVIATE_ADMIN_KEY")
WEAVIATE_COLLECTION = os.getenv("WEAVIATE_COLLECTION", "LegalKnowledgeBase")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-3-small")


class WeaviateVectorStore:
    """
    Manages Weaviate vector database operations for document storage and retrieval.
    """
    
    def __init__(self):
        """Initialize Weaviate client connection."""
        if not WEAVIATE_URL or not WEAVIATE_ADMIN_KEY:
            raise ValueError("WEAVIATE_URL and WEAVIATE_ADMIN_KEY must be set in environment variables")
        
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set in environment variables for Weaviate vectorization")
        
        # Connect to Weaviate with OpenAI API key for vectorization
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=Auth.api_key(WEAVIATE_ADMIN_KEY),
            headers={
                "X-OpenAI-Api-Key": OPENAI_API_KEY
            },
            skip_init_checks=True  # Skip gRPC health check for cloud connections
        )
        logger.info(f"Connected to Weaviate cluster at {WEAVIATE_URL}")
        
        # Ensure collection exists
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """
        Create the collection if it doesn't exist.
        """
        try:
            # Check if collection exists
            if self.client.collections.exists(WEAVIATE_COLLECTION):
                logger.info(f"Collection '{WEAVIATE_COLLECTION}' already exists")
                return
            
            # Create collection with text2vec-openai vectorizer
            self.client.collections.create(
                name=WEAVIATE_COLLECTION,
                vectorizer_config=Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-3-small"
                ),
                properties=[
                    Property(
                        name="content",
                        data_type=DataType.TEXT,
                        description="The text content of the document chunk"
                    ),
                    Property(
                        name="filename",
                        data_type=DataType.TEXT,
                        description="The original filename of the document"
                    ),
                    Property(
                        name="tenant_id",
                        data_type=DataType.TEXT,
                        description="The tenant/user ID who owns this document"
                    ),
                    Property(
                        name="file_id",
                        data_type=DataType.TEXT,
                        description="The unique file ID from S3 upload (for file-level management)"
                    ),
                    Property(
                        name="chunk_id",
                        data_type=DataType.INT,
                        description="The chunk index within the document"
                    ),
                    Property(
                        name="metadata",
                        data_type=DataType.TEXT,
                        description="Additional metadata in JSON format"
                    ),
                ]
            )
            logger.info(f"Created new collection '{WEAVIATE_COLLECTION}'")
            
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    def upsert_document_chunks(self, chunks: List[str], filename: str, tenant_id: str, file_id: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Upsert document chunks to Weaviate collection.
        The function sends the embedded vectors of a document to the weaviate collection.
        
        Args:
            chunks (List[str]): List of text chunks from the document
            filename (str): Name of the source document
            tenant_id (str): The tenant/user ID who owns this document
            file_id (str): The unique file ID from S3 upload (required)
            metadata (Dict[str, Any], optional): Additional metadata to store
        
        Returns:
            Dict[str, Any]: Summary of the upsertion operation
        """
        if not file_id:
            raise ValueError("file_id is required")
        
        try:
            collection = self.client.collections.get(WEAVIATE_COLLECTION)
            
            # Prepare objects for batch insertion
            # Weaviate will automatically generate embeddings using text2vec-openai
            objects_to_insert = []
            for idx, chunk in enumerate(chunks):
                obj = {
                    "content": chunk,
                    "filename": filename,
                    "tenant_id": tenant_id,
                    "file_id": file_id,  # Store file_id for file-level management
                    "chunk_id": idx,
                    "metadata": str(metadata) if metadata else "{}"
                }
                objects_to_insert.append(obj)
            
            logger.info(f"Upserting {len(objects_to_insert)} chunks to Weaviate for file '{filename}'...")
            
            # Batch insert with vectorization
            response = collection.data.insert_many(objects_to_insert)
            
            # Check for errors
            errors = []
            if response.has_errors:
                for idx, error in enumerate(response.errors):
                    if error:
                        errors.append(f"Chunk {idx}: {error}")
                        logger.error(f"Error inserting chunk {idx}: {error}")
            
            successful_count = len(chunks) - len(errors)
            
            result = {
                "status": "success" if not errors else "partial_success",
                "total_chunks": len(chunks),
                "successful_insertions": successful_count,
                "failed_insertions": len(errors),
                "filename": filename,
                "errors": errors if errors else None
            }
            
            logger.info(f"Upserted {successful_count}/{len(chunks)} chunks successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error upserting document chunks: {e}", exc_info=True)
            raise
    
    def search_similar(self, query: str, k: int = 5, filename: str = None, tenant_id: str = None, file_id: str = None) -> List[Dict[str, Any]]:
        """
        Search for similar chunks in Weaviate using vector similarity.
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            filename (str, optional): Filter by specific filename
            tenant_id (str, optional): Filter by specific tenant
            file_id (str, optional): Filter by specific file ID
        
        Returns:
            List[Dict[str, Any]]: List of similar chunks with metadata
        """
        try:
            collection = self.client.collections.get(WEAVIATE_COLLECTION)
            
            # Build query with optional filters
            filters = []
            if filename:
                filters.append(weaviate.classes.query.Filter.by_property("filename").equal(filename))
            if tenant_id:
                filters.append(weaviate.classes.query.Filter.by_property("tenant_id").equal(tenant_id))
            if file_id:
                filters.append(weaviate.classes.query.Filter.by_property("file_id").equal(file_id))
            
            # Combine filters if multiple exist
            combined_filter = None
            if len(filters) == 1:
                combined_filter = filters[0]
            elif len(filters) > 1:
                combined_filter = weaviate.classes.query.Filter.all_of(filters)
            
            # Execute query
            if combined_filter:
                response = collection.query.near_text(
                    query=query,
                    limit=k,
                    return_metadata=["distance"],
                    filters=combined_filter
                )
            else:
                response = collection.query.near_text(
                    query=query,
                    limit=k,
                    return_metadata=["distance"]
                )
            
            results = []
            for obj in response.objects:
                results.append({
                    "content": obj.properties.get("content", ""),
                    "filename": obj.properties.get("filename", "unknown"),
                    "tenant_id": obj.properties.get("tenant_id", "unknown"),
                    "file_id": obj.properties.get("file_id", ""),
                    "chunk_id": obj.properties.get("chunk_id", 0),
                    "distance": obj.metadata.distance if obj.metadata else None,
                    "metadata": obj.properties.get("metadata", "{}")
                })
            
            logger.info(f"Retrieved {len(results)} similar chunks for query")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}", exc_info=True)
            raise
    
    def delete_by_filename(self, filename: str) -> Dict[str, Any]:
        """
        Delete all chunks associated with a specific filename.
        
        Args:
            filename (str): Name of the file to delete
        
        Returns:
            Dict[str, Any]: Deletion summary
        """
        try:
            collection = self.client.collections.get(WEAVIATE_COLLECTION)
            
            # Delete objects matching the filename
            result = collection.data.delete_many(
                where=weaviate.classes.query.Filter.by_property("filename").equal(filename)
            )
            
            logger.info(f"Deleted chunks for filename '{filename}': {result}")
            return {
                "status": "success",
                "filename": filename,
                "deleted_count": result.successful if hasattr(result, 'successful') else "unknown"
            }
            
        except Exception as e:
            logger.error(f"Error deleting chunks by filename: {e}", exc_info=True)
            raise
    
    def delete_by_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """
        Delete all chunks associated with a specific tenant.
        This removes all documents owned by the tenant from the vector store.
        
        Args:
            tenant_id (str): The tenant ID whose documents should be deleted
        
        Returns:
            Dict[str, Any]: Deletion summary
        """
        try:
            collection = self.client.collections.get(WEAVIATE_COLLECTION)
            
            # Delete objects matching the tenant_id
            result = collection.data.delete_many(
                where=weaviate.classes.query.Filter.by_property("tenant_id").equal(tenant_id)
            )
            
            logger.info(f"Deleted all chunks for tenant_id '{tenant_id}': {result}")
            return {
                "status": "success",
                "tenant_id": tenant_id,
                "deleted_count": result.successful if hasattr(result, 'successful') else "unknown",
                "message": f"All documents for tenant '{tenant_id}' have been deleted from the vector store"
            }
            
        except Exception as e:
            logger.error(f"Error deleting chunks by tenant_id: {e}", exc_info=True)
            raise
    
    def delete_by_file_id(self, file_id: str) -> Dict[str, Any]:
        """
        Delete all chunks associated with a specific file ID.
        This removes all chunks for a specific file from the vector store.
        
        Args:
            file_id (str): The file ID whose chunks should be deleted
        
        Returns:
            Dict[str, Any]: Deletion summary
        """
        try:
            collection = self.client.collections.get(WEAVIATE_COLLECTION)
            
            # Delete objects matching the file_id
            result = collection.data.delete_many(
                where=weaviate.classes.query.Filter.by_property("file_id").equal(file_id)
            )
            
            logger.info(f"Deleted all chunks for file_id '{file_id}': {result}")
            return {
                "status": "success",
                "file_id": file_id,
                "deleted_count": result.successful if hasattr(result, 'successful') else "unknown",
                "message": f"All chunks for file '{file_id}' have been deleted from the vector store"
            }
            
        except Exception as e:
            logger.error(f"Error deleting chunks by file_id: {e}", exc_info=True)
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Dict[str, Any]: Collection statistics
        """
        try:
            collection = self.client.collections.get(WEAVIATE_COLLECTION)
            
            # Get aggregate count
            response = collection.aggregate.over_all(total_count=True)
            
            return {
                "collection_name": WEAVIATE_COLLECTION,
                "total_objects": response.total_count,
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}", exc_info=True)
            raise
    
    def close(self):
        """Close the Weaviate client connection."""
        if self.client:
            self.client.close()
            logger.info("Weaviate client connection closed")


# ============================================================================
# Convenience functions for backward compatibility and ease of use
# ============================================================================

def build_index_from_chunks(chunks: List[str], filename: str, tenant_id: str, file_id: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Add new document chunks to Weaviate vector store.
    This is a wrapper function for backward compatibility.
    
    Args:
        chunks: List of text chunks to index
        filename: Source filename for the chunks
        tenant_id: The tenant/user ID who owns this document
        file_id: File ID from S3 upload (required)
        metadata: Optional metadata to store with the chunks
    
    Returns:
        Dict containing upsertion results
    """
    store = WeaviateVectorStore()
    try:
        result = store.upsert_document_chunks(chunks, filename, tenant_id, file_id, metadata)
        return result
    finally:
        store.close()


def search_similar(query: str, k: int = 5, filename: str = None, tenant_id: str = None, file_id: str = None) -> List[Dict[str, Any]]:
    """
    Search for similar chunks in Weaviate vector store.
    Returns a list of dicts: [{'text': str, 'distance': float, 'filename': str}, ...]
    
    Args:
        query: Search query text
        k: Number of results to return
        filename: Optional filename filter
        tenant_id: Optional tenant ID filter
        file_id: Optional file ID filter
    
    Returns:
        List of result dictionaries with 'text', 'distance', and 'filename' keys
    """
    store = WeaviateVectorStore()
    try:
        results = store.search_similar(query, k, filename, tenant_id, file_id)
        
        if not results:
            logger.info("No relevant chunks found for query.")
            return []
        
        # Format results to match expected format for compatibility
        formatted = []
        for result in results:
            formatted.append({
                "text": result.get("content", "").strip(),
                "filename": result.get("filename", "unknown"),
                "tenant_id": result.get("tenant_id", "unknown"),
                "score": result.get("distance", 0.0),  # Weaviate uses distance (lower is better)
            })
        
        logger.info(f"Retrieved {len(formatted)} relevant chunks for query.")
        return formatted
    finally:
        store.close()


def search_weaviate(query: str, k: int = 5, filename: str = None, tenant_id: str = None, file_id: str = None) -> List[Dict[str, Any]]:
    """
    Convenience function to search Weaviate for similar chunks.
    Returns raw Weaviate results with 'content' key.
    
    Args:
        query (str): Search query
        k (int): Number of results to return
        filename (str, optional): Filter by specific filename
        tenant_id (str, optional): Filter by specific tenant
        file_id (str, optional): Filter by specific file ID
    
    Returns:
        List[Dict[str, Any]]: List of similar chunks with metadata
    """
    store = WeaviateVectorStore()
    try:
        results = store.search_similar(query, k, filename, tenant_id, file_id)
        return results
    finally:
        store.close()


def delete_tenant_documents(tenant_id: str) -> Dict[str, Any]:
    """
    Delete all documents associated with a specific tenant.
    This is the main function to call when a tenant is being deleted.
    
    Args:
        tenant_id (str): The tenant ID whose documents should be deleted
    
    Returns:
        Dict[str, Any]: Deletion summary
    """
    store = WeaviateVectorStore()
    try:
        result = store.delete_by_tenant(tenant_id)
        return result
    finally:
        store.close()
