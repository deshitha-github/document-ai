from OCR.text_extraction import extract_pdf_text
from utils.util import DocUtils
from RAG.vectorizer import build_index_from_chunks
from utils.logging_util import get_logger

logger = get_logger(__name__)

async def build_legal_rag_index(pdf_path: str, filename: str, tenant_id: str, file_id: str):
    """
    Extract text → split into chunks → embed → upsert to Weaviate vector store.
    
    Args:
        pdf_path: Path to the PDF file
        filename: Name of the file
        tenant_id: The tenant/user ID who owns this document
        file_id: File ID from S3 upload (required)
    
    Returns:
        Number of chunks created
    """
    if not file_id:
        raise ValueError("file_id is required")
    
    text = await extract_pdf_text(pdf_path)
    if not text.strip():
        raise ValueError("No text extracted from PDF")

    chunks = DocUtils.split_text_for_embedding(text)
    
    # Upsert to Weaviate vector store with tenant_id and file_id
    logger.info(f"Upserting {len(chunks)} chunks to Weaviate for tenant '{tenant_id}', file '{filename}', file_id '{file_id}'...")
    weaviate_result = build_index_from_chunks(chunks, filename, tenant_id, file_id)
    logger.info(f"Weaviate upsertion result: {weaviate_result}")
    
    return len(chunks)

def reset_rag_indexes():
    """
    Placeholder reset — for now, just clears or resets vector storage if needed.
    """

    folder = "vector_indexes"
    if os.path.exists(folder):
        shutil.rmtree(folder)
        os.makedirs(folder)