"""
PostgreSQL database connection and operations.
Handles persistent storage of all chat history.
"""
import os
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from dotenv import load_dotenv

from database.models import Base, ChatMessage, SessionMetadata
from utils.logging_util import get_logger

load_dotenv()
logger = get_logger(__name__)

# PostgreSQL connection settings
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "grant_ai")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# Connection string
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


class PostgresDB:
    """
    PostgreSQL database manager for chat history.
    Provides methods for storing and retrieving chat messages.
    """
    
    def __init__(self):
        """Initialize database connection."""
        try:
            self.engine = create_engine(
                DATABASE_URL,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Verify connections before using
                echo=False  # Set to True for SQL query logging
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info(f"Connected to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def create_tables(self):
        """Create all tables if they don't exist."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for database sessions.
        Automatically handles commit/rollback and cleanup.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def save_message(self, tenant_id: str, session_id: str, role: str, content: str) -> Dict[str, Any]:
        """
        Save a chat message to PostgreSQL.
        
        Args:
            tenant_id: The tenant/user ID
            session_id: The session ID (for grouping related messages)
            role: Message role ('user' or 'assistant')
            content: Message content
        
        Returns:
            Dictionary with saved message details
        """
        try:
            with self.get_session() as session:
                # Create message
                message = ChatMessage(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    role=role,
                    content=content
                )
                session.add(message)
                session.flush()  # Get the ID before commit
                
                # Update session metadata
                metadata = session.query(SessionMetadata).filter_by(session_id=session_id).first()
                if metadata:
                    metadata.message_count += 1
                else:
                    metadata = SessionMetadata(
                        session_id=session_id,
                        tenant_id=tenant_id,
                        message_count=1
                    )
                    session.add(metadata)
                
                session.commit()
                
                logger.info(f"Saved message for tenant '{tenant_id}', session '{session_id}'")
                return message.to_dict()
                
        except SQLAlchemyError as e:
            logger.error(f"Error saving message: {e}")
            raise
    
    def get_chat_history(self, tenant_id: str, session_id: Optional[str] = None, 
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve chat history for a tenant.
        
        Args:
            tenant_id: The tenant/user ID
            session_id: Optional session ID to filter by specific session
            limit: Maximum number of messages to retrieve (default 100)
        
        Returns:
            List of message dictionaries, ordered by timestamp (oldest first)
        """
        try:
            with self.get_session() as session:
                query = session.query(ChatMessage).filter_by(tenant_id=tenant_id)
                
                if session_id:
                    query = query.filter_by(session_id=session_id)
                
                # Order by timestamp ascending (oldest first) and limit
                messages = query.order_by(ChatMessage.timestamp.asc()).limit(limit).all()
                
                result = [msg.to_dict() for msg in messages]
                logger.info(f"Retrieved {len(result)} messages for tenant '{tenant_id}'")
                return result
                
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving chat history: {e}")
            raise
    
    def get_recent_messages(self, tenant_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent messages for a tenant.
        
        Args:
            tenant_id: The tenant/user ID
            limit: Number of recent messages to retrieve
        
        Returns:
            List of recent message dictionaries
        """
        try:
            with self.get_session() as session:
                messages = (
                    session.query(ChatMessage)
                    .filter_by(tenant_id=tenant_id)
                    .order_by(desc(ChatMessage.timestamp))
                    .limit(limit)
                    .all()
                )
                
                # Reverse to get chronological order (oldest first)
                result = [msg.to_dict() for msg in reversed(messages)]
                logger.info(f"Retrieved {len(result)} recent messages for tenant '{tenant_id}'")
                return result
                
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving recent messages: {e}")
            raise
    
    def delete_tenant_history(self, tenant_id: str) -> Dict[str, Any]:
        """
        Delete all chat history for a specific tenant.
        
        Args:
            tenant_id: The tenant/user ID
        
        Returns:
            Dictionary with deletion summary
        """
        try:
            with self.get_session() as session:
                # Delete messages
                message_count = session.query(ChatMessage).filter_by(tenant_id=tenant_id).delete()
                
                # Delete session metadata
                session_count = session.query(SessionMetadata).filter_by(tenant_id=tenant_id).delete()
                
                session.commit()
                
                logger.info(f"Deleted {message_count} messages and {session_count} sessions for tenant '{tenant_id}'")
                return {
                    'status': 'success',
                    'tenant_id': tenant_id,
                    'messages_deleted': message_count,
                    'sessions_deleted': session_count
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Error deleting tenant history: {e}")
            raise
    
    def delete_session_history(self, session_id: str) -> Dict[str, Any]:
        """
        Delete chat history for a specific session.
        
        Args:
            session_id: The session ID
        
        Returns:
            Dictionary with deletion summary
        """
        try:
            with self.get_session() as session:
                # Delete messages
                message_count = session.query(ChatMessage).filter_by(session_id=session_id).delete()
                
                # Delete session metadata
                session.query(SessionMetadata).filter_by(session_id=session_id).delete()
                
                session.commit()
                
                logger.info(f"Deleted {message_count} messages for session '{session_id}'")
                return {
                    'status': 'success',
                    'session_id': session_id,
                    'messages_deleted': message_count
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Error deleting session history: {e}")
            raise
    
    def get_session_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get statistics about a tenant's chat sessions.
        
        Args:
            tenant_id: The tenant/user ID
        
        Returns:
            Dictionary with session statistics
        """
        try:
            with self.get_session() as session:
                total_messages = session.query(ChatMessage).filter_by(tenant_id=tenant_id).count()
                total_sessions = session.query(SessionMetadata).filter_by(tenant_id=tenant_id).count()
                
                return {
                    'tenant_id': tenant_id,
                    'total_messages': total_messages,
                    'total_sessions': total_sessions
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting session stats: {e}")
            raise


# Singleton instance
_postgres_db_instance = None


def get_postgres_db() -> PostgresDB:
    """Get or create the PostgreSQL database instance."""
    global _postgres_db_instance
    if _postgres_db_instance is None:
        _postgres_db_instance = PostgresDB()
    return _postgres_db_instance

