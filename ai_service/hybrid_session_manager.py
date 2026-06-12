"""
Hybrid Session Manager - Combines Redis and PostgreSQL for optimal performance.

Architecture:
- Redis: Fast access to current active sessions (in-memory cache)
- PostgreSQL: Persistent storage of complete chat history

Workflow:
1. On message retrieval:
   - Check Redis first (fast)
   - If not in Redis, load from PostgreSQL and cache in Redis
2. On message save:
   - Save to PostgreSQL (persistent)
   - Update Redis cache (fast access)
3. On session expiry:
   - Clear from Redis
   - Keep in PostgreSQL (full history preserved)
"""
from typing import List, Dict, Any, Optional
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage, BaseMessage
import asyncio
from datetime import datetime
import uuid

from database.postgres_db import get_postgres_db
from database.redis_cache import get_redis_cache
from utils.logging_util import get_logger

logger = get_logger(__name__)


class HybridSessionManager:
    """
    Manages chat sessions using both Redis (cache) and PostgreSQL (persistent storage).
    
    Features:
    - Fast access via Redis for active sessions
    - Persistent storage via PostgreSQL for full history
    - Automatic cache management with TTL
    - Thread-safe operations
    """
    
    _lock = asyncio.Lock()
    
    def __init__(self):
        """Initialize connections to Redis and PostgreSQL."""
        try:
            self.redis = get_redis_cache()
            self.postgres = get_postgres_db()
            logger.info("Hybrid session manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize hybrid session manager: {e}")
            raise
    
    async def get_memory(self, tenant_id: str, session_id: Optional[str] = None) -> ConversationBufferMemory:
        """
        Get conversation memory for a tenant.
        First checks Redis cache, falls back to PostgreSQL if needed.
        
        Args:
            tenant_id: The tenant/user ID
            session_id: Optional session ID (defaults to tenant_id)
        
        Returns:
            ConversationBufferMemory with chat history
        """
        async with self._lock:
            session_id = session_id or tenant_id
            
            # Try Redis first (fast)
            cached_messages = self.redis.get_session_messages(tenant_id)
            
            if cached_messages:
                logger.info(f"Cache HIT for tenant '{tenant_id}' - loading from Redis")
                messages = self._convert_to_langchain_messages(cached_messages)
            else:
                logger.info(f"Cache MISS for tenant '{tenant_id}' - loading from PostgreSQL")
                # Load from PostgreSQL
                db_messages = self.postgres.get_recent_messages(tenant_id, limit=50)
                
                if db_messages:
                    # Cache in Redis for future access
                    self.redis.set_session_messages(tenant_id, db_messages)
                    messages = self._convert_to_langchain_messages(db_messages)
                else:
                    messages = []
            
            # Create memory with loaded messages
            memory = ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history",
                output_key="output",
            )
            
            # Add messages to memory
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    memory.chat_memory.add_user_message(msg.content)
                elif isinstance(msg, AIMessage):
                    memory.chat_memory.add_ai_message(msg.content)
            
            return memory
    
    async def save_message(self, tenant_id: str, role: str, content: str, 
                          session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Save a message to both PostgreSQL and Redis.
        
        Args:
            tenant_id: The tenant/user ID
            role: Message role ('user' or 'assistant')
            content: Message content
            session_id: Optional session ID (defaults to tenant_id)
        
        Returns:
            Dictionary with save result
        """
        async with self._lock:
            session_id = session_id or tenant_id
            
            try:
                # Save to PostgreSQL (persistent)
                db_result = self.postgres.save_message(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    role=role,
                    content=content
                )
                
                # Update Redis cache
                message_dict = {
                    'role': role,
                    'content': content,
                    'timestamp': datetime.utcnow().isoformat()
                }
                self.redis.append_message(tenant_id, message_dict)
                
                # Extend session TTL on activity
                self.redis.extend_session_ttl(tenant_id)
                
                logger.info(f"Saved '{role}' message for tenant '{tenant_id}'")
                return {
                    'status': 'success',
                    'tenant_id': tenant_id,
                    'session_id': session_id,
                    'saved_to_db': True,
                    'cached': True
                }
                
            except Exception as e:
                logger.error(f"Error saving message: {e}")
                raise
    
    async def save_conversation_turn(self, tenant_id: str, user_message: str, 
                                   assistant_message: str, session_id: Optional[str] = None):
        """
        Save a complete conversation turn (user + assistant messages).
        
        Args:
            tenant_id: The tenant/user ID
            user_message: User's message
            assistant_message: Assistant's response
            session_id: Optional session ID
        """
        session_id = session_id or tenant_id
        
        # Save user message
        await self.save_message(tenant_id, 'user', user_message, session_id)
        
        # Save assistant message
        await self.save_message(tenant_id, 'assistant', assistant_message, session_id)
    
    async def get_chat_history(self, tenant_id: str, session_id: Optional[str] = None,
                               limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get complete chat history from PostgreSQL.
        
        Args:
            tenant_id: The tenant/user ID
            session_id: Optional session ID filter
            limit: Maximum messages to retrieve
        
        Returns:
            List of message dictionaries
        """
        try:
            return self.postgres.get_chat_history(tenant_id, session_id, limit)
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}")
            raise
    
    async def clear_session(self, tenant_id: str, clear_db: bool = False):
        """
        Clear session from Redis cache, optionally from PostgreSQL too.
        
        Args:
            tenant_id: The tenant/user ID
            clear_db: If True, also delete from PostgreSQL (default False)
        """
        async with self._lock:
            try:
                # Always clear from Redis
                self.redis.clear_session(tenant_id)
                logger.info(f"Cleared Redis cache for tenant '{tenant_id}'")
                
                # Optionally clear from PostgreSQL
                if clear_db:
                    self.postgres.delete_tenant_history(tenant_id)
                    logger.info(f"Deleted PostgreSQL history for tenant '{tenant_id}'")
                
            except Exception as e:
                logger.error(f"Error clearing session: {e}")
                raise
    
    async def delete_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """
        Completely delete all data for a tenant (Redis + PostgreSQL).
        
        Args:
            tenant_id: The tenant/user ID
        
        Returns:
            Dictionary with deletion summary
        """
        async with self._lock:
            try:
                # Delete from Redis
                self.redis.clear_session(tenant_id)
                
                # Delete from PostgreSQL
                db_result = self.postgres.delete_tenant_history(tenant_id)
                
                logger.info(f"Completely deleted all data for tenant '{tenant_id}'")
                return {
                    'status': 'success',
                    'tenant_id': tenant_id,
                    'redis_cleared': True,
                    'postgres_result': db_result
                }
                
            except Exception as e:
                logger.error(f"Error deleting tenant: {e}")
                raise
    
    async def get_session_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get statistics about a tenant's sessions.
        
        Args:
            tenant_id: The tenant/user ID
        
        Returns:
            Dictionary with session statistics
        """
        try:
            # Get PostgreSQL stats
            db_stats = self.postgres.get_session_stats(tenant_id)
            
            # Check Redis cache status
            in_cache = self.redis.session_exists(tenant_id)
            
            return {
                **db_stats,
                'active_in_cache': in_cache
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            raise
    
    def _convert_to_langchain_messages(self, messages: List[Dict[str, Any]]) -> List[BaseMessage]:
        """
        Convert message dictionaries to LangChain message objects.
        
        Args:
            messages: List of message dictionaries
        
        Returns:
            List of LangChain BaseMessage objects
        """
        langchain_messages = []
        
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'user':
                langchain_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                langchain_messages.append(AIMessage(content=content))
        
        return langchain_messages
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of Redis and PostgreSQL connections.
        
        Returns:
            Dictionary with health status for both systems
        """
        try:
            redis_health = self.redis.health_check()
            
            # Simple PostgreSQL health check
            try:
                self.postgres.get_session_stats("health_check_test")
                postgres_health = {'status': 'healthy'}
            except Exception as e:
                postgres_health = {'status': 'unhealthy', 'error': str(e)}
            
            return {
                'redis': redis_health,
                'postgresql': postgres_health,
                'overall': 'healthy' if (redis_health['status'] == 'healthy' and 
                                        postgres_health['status'] == 'healthy') else 'degraded'
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'redis': {'status': 'unknown'},
                'postgresql': {'status': 'unknown'},
                'overall': 'unhealthy',
                'error': str(e)
            }


# Singleton instance
_hybrid_session_manager = None


async def get_hybrid_session_manager() -> HybridSessionManager:
    """Get or create the hybrid session manager instance."""
    global _hybrid_session_manager
    if _hybrid_session_manager is None:
        _hybrid_session_manager = HybridSessionManager()
    return _hybrid_session_manager

