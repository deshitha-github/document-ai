"""
Database models for chat history storage in PostgreSQL.
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class ChatMessage(Base):
    """
    Model for storing individual chat messages.
    Each message is associated with a tenant and has a role (user/assistant).
    """
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)  # For grouping related messages
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Composite index for efficient querying by tenant and timestamp
    __table_args__ = (
        Index('idx_tenant_timestamp', 'tenant_id', 'timestamp'),
        Index('idx_session_timestamp', 'session_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, tenant_id={self.tenant_id}, role={self.role}, timestamp={self.timestamp})>"
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class SessionMetadata(Base):
    """
    Model for storing session metadata.
    Tracks session information like start time, last activity, message count.
    """
    __tablename__ = "session_metadata"
    
    session_id = Column(String(255), primary_key=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    message_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<SessionMetadata(session_id={self.session_id}, tenant_id={self.tenant_id}, message_count={self.message_count})>"
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'session_id': self.session_id,
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'message_count': self.message_count
        }

