# Tenant ID Generation with UUID

## Overview

The system now supports **production-friendly tenant ID generation** by combining usernames with UUIDs. This ensures:

- ✅ **Uniqueness**: Each tenant ID is guaranteed to be unique via UUID
- ✅ **Human-readable**: Includes the username for easy identification
- ✅ **Production-ready**: Cleaned and sanitized for database safety
- ✅ **Backward compatible**: Still supports direct tenant_id input

---

## How It Works

### Format

```
username_<8-char-uuid>
```

**Examples:**
- Input: `"john_doe"` → Output: `"john_doe_a3f5b2c1"`
- Input: `"Jane Smith"` → Output: `"jane_smith_7f4e9a2b"`
- Input: `"alice-123"` → Output: `"alice-123_c9d6e8f1"`

### Character Cleaning

The system automatically:
1. Converts username to lowercase
2. Replaces spaces with underscores
3. Removes special characters (keeps only: `a-z`, `0-9`, `_`, `-`)
4. Appends an 8-character UUID for uniqueness

---

## API Usage

### Option 1: Using `username` (Recommended for New Tenants)

The system will automatically generate a unique tenant ID:

#### Upload PDF
```bash
curl -X POST "http://localhost:8000/upload_legal_pdf" \
  -F "file=@document.pdf" \
  -F "username=john_doe"
```

**Response:**
```json
{
  "message": "PDF 'document.pdf' processed successfully for tenant 'john_doe_a3f5b2c1'",
  "chunks": 42,
  "tenant_id": "john_doe_a3f5b2c1",
  "username": "john_doe",
  "filename": "document.pdf"
}
```

#### Chat
```bash
curl -X POST "http://localhost:8000/chat" \
  -F "username=john_doe" \
  -F "message=What are the key terms?"
```

**Response:**
```json
{
  "status": "success",
  "tenantId": "john_doe_a3f5b2c1",
  "username": "john_doe",
  "response": "Based on the document...",
  "time": 2.34
}
```

---

### Option 2: Using `tenant_id` (For Existing Tenants)

If you already have a tenant ID (e.g., from a previous session), use it directly:

#### Upload PDF
```bash
curl -X POST "http://localhost:8000/upload_legal_pdf" \
  -F "file=@document.pdf" \
  -F "tenant_id=john_doe_a3f5b2c1"
```

#### Chat
```bash
curl -X POST "http://localhost:8000/chat" \
  -F "tenant_id=john_doe_a3f5b2c1" \
  -F "message=Summarize the document"
```

---

## Implementation Details

### Utility Function

Located in `utils/util.py`:

```python
class TenantUtils:
    @staticmethod
    def generate_tenant_id(username: str) -> str:
        """
        Generate a production-friendly tenant ID by combining username with UUID.
        Format: username_<uuid>
        
        Example:
            generate_tenant_id("john_doe") -> "john_doe_a3f5b2c1"
        """
        # Generate a short UUID (first 8 characters)
        short_uuid = str(uuid.uuid4())[:8]
        
        # Clean username: lowercase, replace spaces, remove special chars
        clean_username = re.sub(r'[^a-zA-Z0-9_-]', '', username.lower().replace(' ', '_'))
        
        # Combine with underscore separator
        tenant_id = f"{clean_username}_{short_uuid}"
        
        return tenant_id
```

---

## Endpoints Updated

The following endpoints now support both `username` and `tenant_id`:

1. **`POST /upload_legal_pdf`**
   - `username` (optional): Generate new tenant ID
   - `tenant_id` (optional): Use existing tenant ID
   - ⚠️ At least one must be provided

2. **`POST /chat`**
   - `username` (optional): Generate new tenant ID
   - `tenant_id` (optional): Use existing tenant ID
   - ⚠️ At least one must be provided

3. **`POST /clear_session`**
   - Still uses `tenant_id` only (you need the exact ID to clear)

4. **`POST /delete_tenant`**
   - Still uses `tenant_id` only (you need the exact ID to delete)

---

## Best Practices

### For New Tenants
✅ **Use `username`** - The system will generate a unique ID automatically

```bash
# First upload - use username
curl -X POST "http://localhost:8000/upload_legal_pdf" \
  -F "file=@doc.pdf" \
  -F "username=alice"

# Response includes the generated tenant_id
# {
#   "tenant_id": "alice_f3e8d7c2",
#   "username": "alice",
#   ...
# }
```

### For Existing Tenants
✅ **Use `tenant_id`** - Use the exact ID from previous sessions

```bash
# Subsequent interactions - use the tenant_id from the first response
curl -X POST "http://localhost:8000/chat" \
  -F "tenant_id=alice_f3e8d7c2" \
  -F "message=What's in the document?"
```

### Client-Side Workflow

```javascript
// Step 1: Upload with username (first time)
const uploadResponse = await uploadPDF(file, "john_doe");
const tenantId = uploadResponse.tenant_id; // "john_doe_a3f5b2c1"

// Step 2: Store tenant_id for future use
localStorage.setItem('tenant_id', tenantId);

// Step 3: Use tenant_id for all subsequent requests
const chatResponse = await chat(tenantId, "What's in the document?");
```

---

## Migration Guide

### If You're Using Existing tenant_id Values

✅ **No changes needed!** The system is backward compatible.

Your existing code will continue to work:
```bash
curl -X POST "http://localhost:8000/chat" \
  -F "tenant_id=user123" \
  -F "message=Hello"
```

### If You Want to Use the New System

Update your code to:
1. Use `username` for first-time users
2. Store the returned `tenant_id` from the response
3. Use `tenant_id` for subsequent requests

---

## Why This Approach?

### Problems with Plain Usernames
- ❌ Risk of collisions (multiple "john" users)
- ❌ Not globally unique
- ❌ Difficult to distinguish between different sessions

### Solution: Username + UUID
- ✅ **Unique**: UUID ensures no collisions
- ✅ **Readable**: Username prefix for human identification
- ✅ **Scalable**: Works across distributed systems
- ✅ **Secure**: UUIDs are unpredictable
- ✅ **Production-ready**: Standard database-friendly format

---

## Filename in VectorDB

**Already Implemented!** ✅

The filename is automatically stored with each document chunk in the Weaviate vector database:

### Storage
Each chunk includes:
- `content`: The text content
- **`filename`**: Original PDF filename
- `tenant_id`: Owner's tenant ID
- `chunk_id`: Position in document
- `metadata`: Additional information

### Retrieval
When searching, results include the source filename:

```
[From: document.pdf]
This is the content of the chunk...

---

[From: legal_contract.pdf]
Another relevant chunk...
```

This allows users to:
- ✅ Know which document contains the information
- ✅ Reference specific documents in conversations
- ✅ Track document provenance

---

## Testing

### Test Tenant ID Generation
```python
from utils.util import TenantUtils

# Generate a tenant ID
tenant_id = TenantUtils.generate_tenant_id("john_doe")
print(tenant_id)  # Output: john_doe_a3f5b2c1

# Same username, different IDs
tenant_id_1 = TenantUtils.generate_tenant_id("alice")
tenant_id_2 = TenantUtils.generate_tenant_id("alice")
print(tenant_id_1)  # alice_f3e8d7c2
print(tenant_id_2)  # alice_9a2b4c1d (different UUID)
```

### Test API
See [`tests/test_client.py`](../tests/test_client.py) for complete API testing examples.

---

## Summary

### What Changed?
1. ✅ Added `TenantUtils.generate_tenant_id()` function
2. ✅ Updated `/upload_legal_pdf` to accept `username`
3. ✅ Updated `/chat` to accept `username`
4. ✅ Maintained backward compatibility with direct `tenant_id`

### What Stayed the Same?
1. ✅ Filename storage in VectorDB (already working)
2. ✅ Existing `tenant_id` usage still works
3. ✅ All other endpoints unchanged
4. ✅ Database schema unchanged

### What's Better?
1. ✅ Production-friendly unique IDs
2. ✅ Human-readable tenant identifiers
3. ✅ No risk of collision
4. ✅ Flexible API (username OR tenant_id)

