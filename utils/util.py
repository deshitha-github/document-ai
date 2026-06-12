"""Utility functions for document processing and ML classification tasks."""
import os
import re
import httpx
import uuid
import asyncio
from fastapi import Header, HTTPException
from langchain.text_splitter import RecursiveCharacterTextSplitter

from dotenv import find_dotenv, load_dotenv

from utils.logging_util import get_logger

# Configure logger
logger = get_logger(__name__)

# Load the environment variables
load_dotenv(find_dotenv())

# Global API key for authentication
API_KEY = os.getenv("API_KEY")


class DocUtils:
    """ Utility class for document processing tasks. """
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean text for embeddings/classifiers:
        - Normalize whitespace
        - Remove OCR noise (�, •, ●)
        - Remove control chars
        """
        if not text:
            return ""

        # Normalize newlines to spaces
        text = text.replace("\r", " ").replace("\n", " ")

        # Remove only obvious OCR garbage: replacement char and bullet dots
        text = re.sub(r"[�•●]", " ", text)

        # Remove ASCII/Unicode control characters (keep printable punctuation & symbols)
        text = re.sub(r"[\u0000-\u001F\u007F-\u009F]", " ", text)

        # Collapse multiple spaces
        text = re.sub(r"\s{2,}", " ", text)

        # Strip leading/trailing spaces
        text = text.strip()

        return text
    
    @staticmethod
    def split_text_for_embedding(text: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", " "],
            length_function=len,
        )
        chunks = splitter.split_text(text)
        return [c.strip() for c in chunks if c.strip()]


class TenantUtils:
    """ Utility class for tenant management operations. """
    @staticmethod
    def generate_tenant_id(username: str) -> str:
        """
        Generate a production-friendly tenant ID by combining username with UUID.
        Format: username_<uuid>
        
        Args:
            username: The user's username or identifier
        
        Returns:
            A unique tenant ID in the format: username_<short-uuid>
        
        Example:
            generate_tenant_id("john_doe") -> "john_doe_a3f5b2c1"
        """
        # Generate a short UUID (first 8 characters for readability)
        short_uuid = str(uuid.uuid4())[:8]
        
        # Clean username: lowercase, replace spaces with underscores, remove special chars
        clean_username = re.sub(r'[^a-zA-Z0-9_-]', '', username.lower().replace(' ', '_'))
        
        # Combine with underscore separator
        tenant_id = f"{clean_username}_{short_uuid}"
        
        logger.info(f"Generated tenant_id: {tenant_id} for username: {username}")
        return tenant_id


class APIUtils:
    """ Utility class for API-related operations. """
    @staticmethod
    async def verify_api_key(x_api_key: str = Header(...)):
        """Validate request API key against stored API_KEY."""
        if x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

    @staticmethod
    async def download_to_temp(url: str, tmp_dir: str) -> str:
        """
        Stream an HTTPS URL to a temporary file (without loading the whole file into memory, 65kb per chunk).
        Returns the local path to the downloaded PDF.
        """

        dest_path = os.path.join(tmp_dir, f"{uuid.uuid4()}.pdf") # Create a unique file name
        timeout = httpx.Timeout(60.0, connect=60.0) # Set request timeouts

        logger.info("Starting download from [%s] into [%s]", url, dest_path)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            try:
                async with client.stream("GET", url) as resp:
                    # Fail if not HTTP 200
                    if resp.status_code != 200:
                        logger.error("Download failed: HTTP %s from %s", resp.status_code, url)
                        raise HTTPException(status_code=400, detail=f"Download failed: {resp.status_code}")

                    bytes_written = 0 # Track file size

                    async def stream_and_write():
                        """Write incoming chunks to file with streaming."""
                        nonlocal bytes_written
                        # Open file for writing
                        with open(dest_path, "wb") as f:
                            # Stream in chunks
                            async for chunk in resp.aiter_bytes(chunk_size=65536):
                                f.write(chunk) # Write chunk
                                bytes_written += len(chunk) # Track progress
                                # if bytes_written % (1024 * 1024) < 65536:  # Log roughly every MB
                                #     logger.info("Downloaded %.2f MB so far from %s", bytes_written / (1024 * 1024), url)

                    # Apply timeout to entire streaming process
                    try:
                        await asyncio.wait_for(stream_and_write(), timeout=60)
                    # Handle timeout
                    except asyncio.TimeoutError:
                        logger.error("Download timed out after 60 seconds from %s", url)
                        raise HTTPException(status_code=408, detail="Download timed out after 60 seconds")

            except httpx.HTTPError as e:
                logger.exception("HTTP error while downloading from %s", url)
                raise HTTPException(status_code=400, detail=f"HTTP download error: {e}") from e

        logger.info("Finished downloading [%s] (%.2f MB)", dest_path, bytes_written / (1024 * 1024))
        return dest_path # Return local path