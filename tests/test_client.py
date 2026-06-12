#!/usr/bin/env python3
"""
Interactive test client for Document AI Chatbot
This script allows you to:
1. Upload a PDF document
2. Chat with the AI about the document
3. Test all API endpoints
"""
import requests
import sys
import os
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def check_server():
    """Check if the server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server is running!\n")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please make sure it's running:")
        print("   Run: python main.py")
        return False

def upload_pdf(file_path, tenant_id):
    """Upload a PDF document."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"\n📤 Uploading PDF: {file_path}")
    print("Please wait, this may take a moment...")
    
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
        data = {'tenant_id': tenant_id}
        try:
            response = requests.post(f"{BASE_URL}/upload_legal_pdf", files=files, data=data)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Upload successful!")
                print(f"   Message: {result.get('message')}")
                print(f"   Chunks processed: {result.get('chunks')}")
                return True
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False

def chat(tenant_id, message):
    """Send a chat message."""
    data = {
        'tenant_id': tenant_id,
        'message': message
    }
    try:
        response = requests.post(f"{BASE_URL}/chat", data=data)
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"❌ Chat failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return None

def search_weaviate(query, k=5):
    """Search Weaviate for similar documents."""
    data = {
        'query': query,
        'k': k
    }
    try:
        response = requests.post(f"{BASE_URL}/weaviate_search", data=data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Search failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Search error: {e}")
        return None

def get_weaviate_stats():
    """Get Weaviate collection statistics."""
    try:
        response = requests.get(f"{BASE_URL}/weaviate_stats")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Stats failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return None

def clear_session(tenant_id):
    """Clear conversation history."""
    data = {'tenant_id': tenant_id}
    try:
        response = requests.post(f"{BASE_URL}/clear_session", data=data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result.get('message')}")
            return True
        else:
            print(f"❌ Clear session failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Clear session error: {e}")
        return False

def interactive_mode():
    """Interactive chat mode."""
    print("\n" + "="*60)
    print("DOCUMENT AI CHATBOT - INTERACTIVE MODE")
    print("="*60)
    
    # Check server
    if not check_server():
        return
    
    # Get Weaviate stats
    print("\n📊 Weaviate Collection Stats:")
    stats = get_weaviate_stats()
    if stats:
        print(f"   Collection: {stats.get('collection_name')}")
        print(f"   Total Documents: {stats.get('total_objects')}")
    
    tenant_id = input("\n👤 Enter your tenant ID (e.g., user123): ").strip()
    if not tenant_id:
        tenant_id = "test_user"
        print(f"   Using default: {tenant_id}")
    
    print("\n" + "="*60)
    print("COMMANDS:")
    print("  /upload <file_path>  - Upload a PDF document")
    print("  /search <query>      - Search Weaviate for documents")
    print("  /stats               - Show Weaviate statistics")
    print("  /clear               - Clear conversation history")
    print("  /quit or /exit       - Exit the chat")
    print("  Type any message to chat with the AI")
    print("="*60 + "\n")
    
    while True:
        try:
            user_input = input(f"\n💬 You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith('/'):
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                
                if command in ['/quit', '/exit']:
                    print("\n👋 Goodbye!")
                    break
                
                elif command == '/upload':
                    if len(parts) < 2:
                        print("❌ Usage: /upload <file_path>")
                        continue
                    file_path = parts[1].strip()
                    upload_pdf(file_path, tenant_id)
                
                elif command == '/search':
                    if len(parts) < 2:
                        print("❌ Usage: /search <query>")
                        continue
                    query = parts[1].strip()
                    print(f"\n🔍 Searching for: '{query}'")
                    results = search_weaviate(query)
                    if results:
                        print(f"   Found {results.get('results_count')} results:")
                        for i, result in enumerate(results.get('results', []), 1):
                            print(f"\n   Result {i}:")
                            print(f"   - Content: {result['content'][:100]}...")
                            print(f"   - Filename: {result['filename']}")
                            print(f"   - Distance: {result['distance']:.4f}")
                
                elif command == '/stats':
                    print("\n📊 Weaviate Collection Stats:")
                    stats = get_weaviate_stats()
                    if stats:
                        print(f"   Collection: {stats.get('collection_name')}")
                        print(f"   Total Documents: {stats.get('total_objects')}")
                        print(f"   Status: {stats.get('status')}")
                
                elif command == '/clear':
                    clear_session(tenant_id)
                
                else:
                    print(f"❌ Unknown command: {command}")
                
                continue
            
            # Regular chat message
            print("\n🤖 AI: ", end="", flush=True)
            response = chat(tenant_id, user_input)
            
            if response:
                # Handle the response structure
                if isinstance(response, dict):
                    if 'response' in response:
                        print(response['response'])
                    elif 'answer' in response:
                        print(response['answer'])
                    elif 'message' in response:
                        print(response['message'])
                    else:
                        print(response)
                else:
                    print(response)
            else:
                print("❌ Failed to get response")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

def quick_test(pdf_path):
    """Quick test with a PDF file."""
    print("\n" + "="*60)
    print("DOCUMENT AI CHATBOT - QUICK TEST")
    print("="*60)
    
    # Check server
    if not check_server():
        return
    
    # Upload PDF
    if pdf_path:
        upload_pdf(pdf_path, tenant_id)
    
    # Get stats
    print("\n📊 Collection Stats:")
    stats = get_weaviate_stats()
    if stats:
        print(f"   Total Documents: {stats.get('total_objects')}")
    
    # Test chat
    tenant_id = "test_user"
    test_messages = [
        "Hello, can you help me understand this document?",
        "What are the main points in the document?",
        "Can you summarize the key terms?"
    ]
    
    print(f"\n🤖 Testing chat with tenant_id: {tenant_id}")
    for msg in test_messages:
        print(f"\n💬 User: {msg}")
        response = chat(tenant_id, msg)
        if response:
            print(f"🤖 AI: {response.get('response', response)}")
        else:
            print("❌ Failed to get response")
    
    print("\n✅ Quick test completed!")

if __name__ == "__main__":
    print("\n🚀 Document AI Chatbot - Test Client")
    
    if len(sys.argv) > 1:
        # Quick test mode with PDF path
        pdf_path = sys.argv[1]
        quick_test(pdf_path)
    else:
        # Interactive mode
        interactive_mode()

