"""
Dependency checker script.
Verifies that all required services (PostgreSQL, Redis) are accessible.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from utils.logging_util import get_logger
import redis
import psycopg2

load_dotenv()
logger = get_logger(__name__)


def check_redis():
    """Check if Redis is accessible."""
    print("\n📡 Checking Redis connection...")
    try:
        REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
        
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            socket_connect_timeout=5
        )
        client.ping()
        
        print(f"✅ Redis is accessible at {REDIS_HOST}:{REDIS_PORT}")
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print(f"   Make sure Redis is running: redis-server")
        return False


def check_postgresql():
    """Check if PostgreSQL is accessible."""
    print("\n🗄️  Checking PostgreSQL connection...")
    try:
        POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
        POSTGRES_DB = os.getenv("POSTGRES_DB", "document_ai")
        POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
        POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
        
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=5
        )
        conn.close()
        
        print(f"✅ PostgreSQL is accessible at {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print(f"   Make sure PostgreSQL is running and database '{POSTGRES_DB}' exists")
        return False
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False


def check_openai():
    """Check if OpenAI API key is set."""
    print("\n🤖 Checking OpenAI configuration...")
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key and len(api_key) > 20:
        print(f"✅ OpenAI API key is configured")
        return True
    else:
        print(f"❌ OpenAI API key is missing or invalid in .env")
        return False


def check_weaviate():
    """Check if Weaviate configuration is set."""
    print("\n🔍 Checking Weaviate configuration...")
    url = os.getenv("WEAVIATE_URL")
    key = os.getenv("WEAVIATE_ADMIN_KEY")
    
    if url and key:
        print(f"✅ Weaviate is configured: {url}")
        return True
    else:
        print(f"❌ Weaviate credentials are missing in .env")
        return False


def main():
    """Run all dependency checks."""
    print("\n" + "="*60)
    print("Document AI - Dependency Checker")
    print("="*60)
    
    results = {
        "Redis": check_redis(),
        "PostgreSQL": check_postgresql(),
        "OpenAI": check_openai(),
        "Weaviate": check_weaviate()
    }
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    all_passed = all(results.values())
    
    for service, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {service}: {'OK' if status else 'FAILED'}")
    
    print("\n" + "="*60)
    
    if all_passed:
        print("✅ All dependencies are ready!")
        print("\nNext steps:")
        print("1. Initialize database: python scripts/init_database.py")
        print("2. Start application: python main.py")
        return 0
    else:
        print("❌ Some dependencies are not ready.")
        print("\nPlease fix the issues above and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

