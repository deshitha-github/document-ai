from langchain.memory import ConversationBufferMemory
from typing import Dict
import asyncio

class SessionManager:
    """
    Manage user sessions and their conversation memory.
    Each tenant/user_id gets its own ConversationBufferMemory.
    Thread-safe for async FastAPI calls.
    """
    _lock = asyncio.Lock()
    _sessions: Dict[str, ConversationBufferMemory] = {}

    @classmethod
    async def get_memory(cls, session_id: str) -> ConversationBufferMemory:
        """
        Retrieve or create a memory buffer for a given session ID.
        """
        async with cls._lock:
            if session_id not in cls._sessions:
                cls._sessions[session_id] = ConversationBufferMemory(
                    return_messages=True,
                    memory_key="chat_history",
                    output_key="output",
                )
            return cls._sessions[session_id]

    @classmethod
    async def clear_memory(cls, session_id: str):
        """
        Clear conversation memory for a specific session.
        """
        async with cls._lock:
            if session_id in cls._sessions:
                del cls._sessions[session_id]
