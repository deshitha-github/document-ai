"""
Test script for Weaviate integration
Run this to verify that Weaviate connection and upsertion work correctly.
"""
import asyncio
from dotenv import load_dotenv
from RAG.weaviate_vectorizer import WeaviateVectorStore, upsert_to_weaviate, search_weaviate

load_dotenv()

async def test_weaviate_integration():
    """Test the Weaviate integration end-to-end."""
    
    print("=" * 60)
    print("Testing Weaviate Integration")
    print("=" * 60)
    
    # Test 1: Initialize connection
    print("\n[1] Testing Weaviate connection...")
    try:
        store = WeaviateVectorStore()
        print("✅ Successfully connected to Weaviate")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # Test 2: Get collection stats
    print("\n[2] Getting collection statistics...")
    try:
        stats = store.get_collection_stats()
        print(f"✅ Collection Stats:")
        print(f"   - Name: {stats['collection_name']}")
        print(f"   - Total Objects: {stats['total_objects']}")
        print(f"   - Status: {stats['status']}")
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
    
    # Test 3: Upsert test documents
    print("\n[3] Testing document upsertion...")
    test_chunks = [
        "This is a test document about contract law and legal agreements.",
        "The parties agree to the terms and conditions outlined herein.",
        "This contract shall be governed by the laws of the jurisdiction.",
        "Any disputes shall be resolved through arbitration.",
    ]
    
    try:
        result = store.upsert_document_chunks(
            chunks=test_chunks,
            filename="test_contract.pdf",
            metadata={"test": True, "date": "2025-10-23"}
        )
        print(f"✅ Upsert Result:")
        print(f"   - Status: {result['status']}")
        print(f"   - Total Chunks: {result['total_chunks']}")
        print(f"   - Successful: {result['successful_insertions']}")
        print(f"   - Failed: {result['failed_insertions']}")
    except Exception as e:
        print(f"❌ Upsertion failed: {e}")
        store.close()
        return
    
    # Test 4: Search for similar documents
    print("\n[4] Testing semantic search...")
    try:
        query = "What are the dispute resolution procedures?"
        results = store.search_similar(query, k=3)
        print(f"✅ Search Results for: '{query}'")
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n   Result {i}:")
            print(f"   - Content: {result['content'][:80]}...")
            print(f"   - Filename: {result['filename']}")
            print(f"   - Chunk ID: {result['chunk_id']}")
            print(f"   - Distance: {result['distance']:.4f}")
    except Exception as e:
        print(f"❌ Search failed: {e}")
    
    # Test 5: Search with filename filter
    print("\n[5] Testing filtered search...")
    try:
        results = store.search_similar(
            query="legal agreements",
            k=2,
            filename="test_contract.pdf"
        )
        print(f"✅ Filtered Search Results:")
        print(f"   Found {len(results)} results from 'test_contract.pdf'")
    except Exception as e:
        print(f"❌ Filtered search failed: {e}")
    
    # Test 6: Delete test documents (cleanup)
    print("\n[6] Cleaning up test documents...")
    try:
        delete_result = store.delete_by_filename("test_contract.pdf")
        print(f"✅ Deletion Result:")
        print(f"   - Status: {delete_result['status']}")
        print(f"   - Filename: {delete_result['filename']}")
        print(f"   - Deleted Count: {delete_result['deleted_count']}")
    except Exception as e:
        print(f"❌ Deletion failed: {e}")
    
    # Test 7: Verify deletion
    print("\n[7] Verifying deletion...")
    try:
        results = store.search_similar("contract", k=5, filename="test_contract.pdf")
        if len(results) == 0:
            print("✅ Test documents successfully deleted")
        else:
            print(f"⚠️  Warning: Found {len(results)} documents that should have been deleted")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    
    # Test 8: Test convenience functions
    print("\n[8] Testing convenience functions...")
    try:
        # Upsert using convenience function
        result = upsert_to_weaviate(
            chunks=["Test chunk via convenience function"],
            filename="convenience_test.pdf"
        )
        print(f"✅ Convenience upsert: {result['successful_insertions']} chunks")
        
        # Search using convenience function
        results = search_weaviate("test chunk", k=1)
        print(f"✅ Convenience search: Found {len(results)} results")
        
        # Cleanup
        store2 = WeaviateVectorStore()
        store2.delete_by_filename("convenience_test.pdf")
        store2.close()
        print("✅ Cleanup successful")
    except Exception as e:
        print(f"❌ Convenience functions test failed: {e}")
    
    # Close connection
    store.close()
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


def test_sync_operations():
    """Test synchronous operations."""
    print("\n\n[SYNC TEST] Testing synchronous convenience functions...")
    
    try:
        # Test upsert
        result = upsert_to_weaviate(
            chunks=["Sync test chunk 1", "Sync test chunk 2"],
            filename="sync_test.pdf"
        )
        print(f"✅ Sync upsert successful: {result['successful_insertions']} chunks")
        
        # Test search
        results = search_weaviate("sync test", k=2)
        print(f"✅ Sync search successful: Found {len(results)} results")
        
        # Cleanup
        store = WeaviateVectorStore()
        store.delete_by_filename("sync_test.pdf")
        store.close()
        print("✅ Sync cleanup successful")
        
    except Exception as e:
        print(f"❌ Sync operations failed: {e}")


if __name__ == "__main__":
    print("\n🚀 Starting Weaviate Integration Tests...\n")
    
    # Run async tests
    asyncio.run(test_weaviate_integration())
    
    # Run sync tests
    test_sync_operations()
    
    print("\n✨ Testing complete!\n")


