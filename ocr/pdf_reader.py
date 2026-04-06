"""
PDF text extraction module.

Strategy:
    1. Try native text extraction with pdfplumber (for digital PDFs).
    2. If no text → fallback to OCR via PyMuPDF rendering + Tesseract.
    3. OCR uses high-DPI (300) rendering and the same preprocessing
       pipeline as image_ocr for maximum accuracy.
"""

import pdfplumber
import io
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import numpy as np
import fitz  # PyMuPDF

from ocr.image_ocr import preprocess_image_for_ocr

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# ── Tesseract OCR config ──────────────────────────────────────────────
_TESSERACT_CONFIG = r"--oem 3 --psm 6"

# Render at 300 DPI for crisp OCR input (default PyMuPDF is 72 DPI)
_RENDER_DPI = 300
_RENDER_MATRIX = fitz.Matrix(_RENDER_DPI / 72, _RENDER_DPI / 72)


async def extract_text_from_pdf(file) -> str:
    """
    Extract text from an uploaded PDF.

    Attempts native text extraction first; falls back to OCR when
    the PDF contains scanned images instead of selectable text.

    Args:
        file: FastAPI UploadFile object.

    Returns:
        str: Extracted text from all pages.

    Raises:
        ValueError: If the PDF cannot be processed.
    """
    try:
        content = await file.read()

        # ── 1. Native text extraction ─────────────────────────────
        extracted_text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"

        if extracted_text.strip():
            return extracted_text

        # ── 2. Fallback: OCR ──────────────────────────────────────
        print("No text detected in PDF. Running OCR...")
        extracted_text = ""

        pdf_doc = fitz.open(stream=content, filetype="pdf")

        for page_num, page in enumerate(pdf_doc):
            # Render page at high DPI
            pix = page.get_pixmap(matrix=_RENDER_MATRIX, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Run through the same preprocessing pipeline as images
            img = preprocess_image_for_ocr(img)

            text = pytesseract.image_to_string(img, config=_TESSERACT_CONFIG)
            print(f"OCR PAGE {page_num + 1} TEXT: {text[:200]}")
            extracted_text += text + "\n"

        pdf_doc.close()
        return extracted_text

    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}")