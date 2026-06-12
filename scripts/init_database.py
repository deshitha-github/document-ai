"""
Database initialization script.
Creates necessary tables in PostgreSQL for chat history storage.
Run this script before starting the application for the first time.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.postgres_db import get_postgres_db
from utils.logging_util import get_logger

logger = get_logger(__name__)


def init_database():
    """Initialize PostgreSQL database with necessary tables."""
    try:
        logger.info("Starting database initialization...")
        
        # Get PostgreSQL instance
        postgres = get_postgres_db()
        
        # Create all tables
        postgres.create_tables()
        
        logger.info("✅ Database initialization completed successfully!")
        logger.info("Tables created:")
        logger.info("  - chat_messages: Stores individual chat messages")
        logger.info("  - session_metadata: Tracks session information")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PostgreSQL Database Initialization")
    print("="*60 + "\n")
    
    success = init_database()
    
    if success:
        print("\n✅ Database is ready to use!")
        print("\nNext steps:")
        print("1. Start Redis server: redis-server")
        print("2. Start the application: python main.py")
        sys.exit(0)
    else:
        print("\n❌ Database initialization failed!")
        print("\nPlease check:")
        print("1. PostgreSQL is running")
        print("2. Database credentials in .env are correct")
        print("3. Database 'document_ai' exists (or create it first)")
        sys.exit(1)

