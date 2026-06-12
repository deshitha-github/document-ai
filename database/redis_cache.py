"""
Redis cache manager for current session storage.
Provides fast in-memory access to active conversation sessions.
"""
import os
import json
from typing import List, Dict, Any, Optional
import redis
from dotenv import load_dotenv
from utils.logging_util import get_logger

load_dotenv()
logger = get_logger(__name__)

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_SESSION_TTL = int(os.getenv("REDIS_SESSION_TTL", "3600"))  # 1 hour default


class RedisCache:
    """
    Redis cache manager for session data.
    Stores current active sessions in memory for fast access.
    """
    
    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
                decode_responses=True,  # Automatically decode responses to strings
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _get_session_key(self, tenant_id: str) -> str:
        """Generate Redis key for a session."""
        return f"session:{tenant_id}"
    
    def _get_messages_key(self, tenant_id: str) -> str:
        """Generate Redis key for session messages."""
        return f"messages:{tenant_id}"
    
    def set_session_messages(self, tenant_id: str, messages: List[Dict[str, Any]], 
                           ttl: Optional[int] = None) -> bool:
        """
        Store session messages in Redis cache.
        
        Args:
            tenant_id: The tenant/user ID
            messages: List of message dictionaries
            ttl: Time-to-live in seconds (default from env)
        
        Returns:
            True if successful
        """
        try:
            key = self._get_messages_key(tenant_id)
            value = json.dumps(messages)
            
            # Set with TTL
            ttl = ttl or REDIS_SESSION_TTL
            self.client.setex(key, ttl, value)
            
            # Also set a session marker
            session_key = self._get_session_key(tenant_id)
            self.client.setex(session_key, ttl, "active")
            
            logger.info(f"Cached {len(messages)} messages for tenant '{tenant_id}' with TTL {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Error caching session messages: {e}")
            return False
    
    def get_session_messages(self, tenant_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve session messages from Redis cache.
        
        Args:
            tenant_id: The tenant/user ID
        
        Returns:
            List of message dictionaries, or None if not found
        """
        try:
            key = self._get_messages_key(tenant_id)
            value = self.client.get(key)
            
            if value:
                messages = json.loads(value)
                logger.info(f"Retrieved {len(messages)} cached messages for tenant '{tenant_id}'")
                return messages
            
            logger.debug(f"No cached messages found for tenant '{tenant_id}'")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached messages: {e}")
            return None
    
    def append_message(self, tenant_id: str, message: Dict[str, Any], 
                      ttl: Optional[int] = None) -> bool:
        """
        Append a new message to cached session.
        
        Args:
            tenant_id: The tenant/user ID
            message: Message dictionary to append
            ttl: Time-to-live in seconds
        
        Returns:
            True if successful
        """
        try:
            # Get existing messages
            messages = self.get_session_messages(tenant_id) or []
            
            # Append new message
            messages.append(message)
            
            # Save back to Redis
            return self.set_session_messages(tenant_id, messages, ttl)
            
        except Exception as e:
            logger.error(f"Error appending message to cache: {e}")
            return False
    
    def clear_session(self, tenant_id: str) -> bool:
        """
        Clear session from Redis cache.
        
        Args:
            tenant_id: The tenant/user ID
        
        Returns:
            True if successful
        """
        try:
            messages_key = self._get_messages_key(tenant_id)
            session_key = self._get_session_key(tenant_id)
            
            deleted = self.client.delete(messages_key, session_key)
            logger.info(f"Cleared cache for tenant '{tenant_id}' ({deleted} keys deleted)")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing session cache: {e}")
            return False
    
    def session_exists(self, tenant_id: str) -> bool:
        """
        Check if a session exists in cache.
        
        Args:
            tenant_id: The tenant/user ID
        
        Returns:
            True if session exists in cache
        """
        try:
            key = self._get_session_key(tenant_id)
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking session existence: {e}")
            return False
    
    def extend_session_ttl(self, tenant_id: str, ttl: Optional[int] = None) -> bool:
        """
        Extend the TTL of a session.
        
        Args:
            tenant_id: The tenant/user ID
            ttl: New TTL in seconds
        
        Returns:
            True if successful
        """
        try:
            ttl = ttl or REDIS_SESSION_TTL
            messages_key = self._get_messages_key(tenant_id)
            session_key = self._get_session_key(tenant_id)
            
            self.client.expire(messages_key, ttl)
            self.client.expire(session_key, ttl)
            
            logger.debug(f"Extended TTL for tenant '{tenant_id}' to {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Error extending session TTL: {e}")
            return False
    
    def get_active_sessions(self) -> List[str]:
        """
        Get list of all active session tenant IDs.
        
        Returns:
            List of tenant IDs with active sessions
        """
        try:
            # Find all session keys
            keys = self.client.keys("session:*")
            
            # Extract tenant IDs
            tenant_ids = [key.replace("session:", "") for key in keys]
            
            logger.info(f"Found {len(tenant_ids)} active sessions")
            return tenant_ids
            
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Redis connection health.
        
        Returns:
            Dictionary with health status
        """
        try:
            self.client.ping()
            info = self.client.info()
            return {
                'status': 'healthy',
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'uptime_in_seconds': info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def close(self):
        """Close Redis connection."""
        try:
            self.client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Singleton instance
_redis_cache_instance = None


def get_redis_cache() -> RedisCache:
    """Get or create the Redis cache instance."""
    global _redis_cache_instance
    if _redis_cache_instance is None:
        _redis_cache_instance = RedisCache()
    return _redis_cache_instance

