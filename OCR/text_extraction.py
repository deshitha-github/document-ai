import os
import fitz
import asyncio
import itertools
# import threading
from PIL import Image, ImageOps
import pytesseract
from utils.logging_util import get_logger
from dotenv import find_dotenv
from dotenv import load_dotenv

# Load the environment variables
load_dotenv(find_dotenv())

# Load environment variables
load_dotenv()

# Initialize logger for this module
logger = get_logger(__name__)

# Initialize Tesseract
TESSSERACT_CMD = os.getenv("TESSERACT_CMD", "/opt/homebrew/bin/tesseract")
if TESSSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSSERACT_CMD

OCR_WORKERS = int(os.getenv("OCR_WORKERS", "2"))
OCR_SEM = asyncio.Semaphore(OCR_WORKERS)


class OCR:
    """
    Utility class for extracting text from PDF pages using Tesseract OCR.
    """

    @staticmethod
    def extract_text_from_scanned_page(pdf_path,
                                       page_number=0,
                                       invert_negative=True,
                                       dpi=300):
        """
        Extract text from scanned or hybrid PDF (text + scanned) page using Tesseract OCR.

        Args:
            pdf_path (str): Path to PDF file.
            page_number (int): Page index (0-based).
            invert_negative (bool): Invert if suspected negative scan.
            dpi (int): Rendering DPI.

        Returns:
            str: OCR-extracted text.
        """

        doc = fitz.open(pdf_path) # Open the PDF
        page = doc[page_number] # Select target page

        # Render image at high resolution
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Convert image to grayscale
        gray = img.convert("L")

        # Invert if image is a negative scan (white text on black background)
        if invert_negative and gray.getextrema()[0] > 200:
            gray = ImageOps.invert(gray)

        # Binarize image for cleaner OCR (convert pixels to either black or white)
        bw = gray.point(lambda x: 0 if x < 180 else 255, '1')

        # Perform OCR on processed image
        try:
            text = pytesseract.image_to_string(bw)
        except Exception as e:
            # If error return text as empty and log the error
            text = ""
            logger.error("Tesseract OCR failed: %s", e)

        # Return the extracted text
        return text


async def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text from every page of a PDF asynchronously using OCR.
    Runs multiple OCR tasks in parallel (bounded by a semaphore limit).

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Combined OCR-extracted text from all pages.
    """

    # Open the PDF document using PyMuPDF (fitz)
    doc = fitz.open(pdf_path)

    # Count total number of pages in the PDF
    total_pages = len(doc)

    # Sequential counter for completed pages
    logger.info(f"Starting OCR for {total_pages} pages...")
    completed_counter = itertools.count(1)  # sequential counter for completed pages

    # Define an inner async function to handle one page at a time
    async def run_page(i):
        # Semaphore ensures we don't run too many OCR workers simultaneously
        async with OCR_SEM:
            # Run blocking OCR in a threads for concurrency
            text =  await asyncio.to_thread(
                OCR.extract_text_from_scanned_page,  # OCR method
                pdf_path,                            # PDF file path
                i                                    # Current page index
            )
            current_done = next(completed_counter)
            logger.info(f"OCR → Completed page {current_done}/{total_pages}")
            return text
    
    # Run OCR tasks for all pages concurrently and wait for all to complete
    results = await asyncio.gather(*(run_page(i) for i in range(total_pages)))

    # Join all extracted page texts into one combined string
    return "\n".join(results)
