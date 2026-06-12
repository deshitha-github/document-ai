#!/usr/bin/env python3
"""
Quick test script for Document AI Chatbot API
Replace the values below with your actual userId and file paths
"""

import requests

BASE_URL = "http://127.0.0.1:8000"

# Replace with your actual userId
USER_ID = "64e86408-80b1-70f4-c16e-77b2279e6b2b"

# Replace with your actual fileId from S3 upload
FILE_ID = "058d30ca-8134-44ee-bcfe-914225f04fff"

def test_upload_pdf(file_path, user_id, file_id):
    """Test uploading a PDF document"""
    print(f"\n📤 Uploading PDF: {file_path}")
    print(f"   userId: {user_id}")
    print(f"   fileId: {file_id}")
    
    if not file_id:
        print("❌ Error: fileId is required")
        return None
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'userId': user_id,
            'fileId': file_id
        }
        
        response = requests.post(f"{BASE_URL}/upload_legal_pdf", files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Upload successful!")
        print(f"   Chunks processed: {result.get('chunks')}")
        print(f"   Message: {result.get('message')}")
        return result
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def test_chat(user_id, message):
    """Test chatting with the AI"""
    print(f"\n💬 Chat Message: {message}")
    print(f"   userId: {user_id}")
    
    data = {
        'userId': user_id,
        'message': message
    }
    
    response = requests.post(f"{BASE_URL}/chat", data=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Chat successful!")
        print(f"   Response: {result.get('response', result.get('answer', 'N/A'))}")
        return result
    else:
        print(f"❌ Chat failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def test_search(user_id, query, file_id=None, k=5):
    """Test searching Weaviate"""
    print(f"\n🔍 Search Query: {query}")
    print(f"   userId: {user_id}")
    if file_id:
        print(f"   fileId: {file_id}")
    
    data = {
        'query': query,
        'k': k,
        'userId': user_id
    }
    if file_id:
        data['fileId'] = file_id
    
    response = requests.post(f"{BASE_URL}/weaviate_search", data=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Search successful!")
        print(f"   Results found: {result.get('results_count')}")
        for i, r in enumerate(result.get('results', [])[:3], 1):
            print(f"   Result {i}: {r.get('content', '')[:100]}...")
        return result
    else:
        print(f"❌ Search failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def main():
    print("=" * 60)
    print("Document AI Chatbot - API Test Script")
    print("=" * 60)
    
    # Update these paths with your actual file
    PDF_PATH = "/path/to/your/document.pdf"  # ← Update this!
    
    print(f"\nUsing userId: {USER_ID}")
    print(f"Using fileId: {FILE_ID}")
    
    # Test 1: Upload PDF
    # Uncomment to test upload (fileId is now required)
    # result = test_upload_pdf(PDF_PATH, USER_ID, FILE_ID)
    
    # Test 2: Chat
    test_chat(USER_ID, "What are the main points in my uploaded documents?")
    
    # Test 3: Search
    test_search(USER_ID, "contract terms", file_id=FILE_ID)
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()

