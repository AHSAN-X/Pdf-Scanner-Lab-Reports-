"""
Image OCR module for extracting text from images.

Uses pytesseract (Tesseract OCR) with advanced image preprocessing
(adaptive thresholding, deskewing, noise removal, sharpening) to
achieve high-accuracy text extraction from phone camera photos and
scanned lab reports.
"""

import io

import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


# ── Tesseract path (Windows) ──────────────────────────────────────────
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# ── Public API ────────────────────────────────────────────────────────
async def extract_text_from_image(file) -> str:
    """
    Extract text from an uploaded image file using OCR with
    full preprocessing pipeline.

    Args:
        file: FastAPI UploadFile object containing the image.

    Returns:
        str: Extracted text.

    Raises:
        ValueError: If the image cannot be processed.
    """
    try:
        content = await file.read()
        original = Image.open(io.BytesIO(content))

        preprocessed = preprocess_image_for_ocr(original)
        grayscale = _prepare_grayscale_variant(original)

        # Try multiple page segmentation modes; select best by domain-label score.
        ocr_candidates = []
        for variant in (preprocessed, grayscale):
            for config in (r"--oem 3 --psm 6", r"--oem 3 --psm 11", r"--oem 3 --psm 4"):
                text = pytesseract.image_to_string(variant, config=config)
                if text and text.strip():
                    ocr_candidates.append(text)

        if not ocr_candidates:
            return ""

        return max(ocr_candidates, key=_score_ocr_text)

    except Exception as e:
        raise ValueError(f"Failed to extract text from image: {e}")


# ── Image preprocessing pipeline ─────────────────────────────────────
def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Full preprocessing pipeline to maximise OCR accuracy.

    Steps:
        1. Convert to RGB
        2. Up-scale small images (target ≥ 2000 px on longest side)
        3. Convert to greyscale
        4. Auto-rotate / deskew via Tesseract OSD (if available)
        5. Adaptive-threshold binarisation (via numpy)
        6. Noise removal (median filter)
        7. Sharpening
        8. Add white border for edge-text detection
    """
    # 1 – Ensure RGB
    if image.mode != "RGB":
        image = image.convert("RGB")

    # 2 – Up-scale small images for better OCR
    max_dim = max(image.size)
    if max_dim < 2000:
        scale = 2000 / max_dim
        new_w = int(image.width * scale)
        new_h = int(image.height * scale)
        image = image.resize((new_w, new_h), Image.LANCZOS)

    # 3 – Greyscale
    grey = image.convert("L")

    # 4 – Deskew (try Tesseract OSD; silently skip on failure)
    grey = _try_deskew(grey)

    # 5 – Adaptive threshold binarisation
    binary = _adaptive_threshold(grey, block_size=35, offset=15)

    # 6 – Median filter (removes salt-and-pepper noise)
    binary = binary.filter(ImageFilter.MedianFilter(size=3))

    # 7 – Sharpen
    enhancer = ImageEnhance.Sharpness(binary)
    binary = enhancer.enhance(2.0)

    # 8 – Add white border so text at edges isn't clipped
    binary = ImageOps.expand(binary, border=30, fill=255)

    return binary


# ── Helpers ───────────────────────────────────────────────────────────
def _try_deskew(image: Image.Image) -> Image.Image:
    """Attempt to detect and correct skew using Tesseract OSD."""
    try:
        osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
        angle = osd.get("rotate", 0)
        if angle and angle != 0:
            image = image.rotate(-angle, expand=True, fillcolor=255)
    except Exception:
        pass  # OSD can fail on low-text images; that's fine
    return image


def _prepare_grayscale_variant(image: Image.Image) -> Image.Image:
    """Prepare a softer grayscale variant for forms where hard thresholding loses text."""
    if image.mode != "RGB":
        image = image.convert("RGB")

    max_dim = max(image.size)
    if max_dim < 2000:
        scale = 2000 / max_dim
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.LANCZOS)

    grey = image.convert("L")
    grey = _try_deskew(grey)
    contrast = ImageEnhance.Contrast(grey).enhance(1.6)
    sharpened = ImageEnhance.Sharpness(contrast).enhance(1.8)
    return ImageOps.expand(sharpened, border=30, fill=255)


def _score_ocr_text(text: str) -> int:
    """Heuristic score that rewards medically relevant field labels and denser extraction."""
    low = text.lower()
    labels = [
        "name", "gender", "age", "ref", "lab", "entry date", "print date",
        "haematology", "hematology", "platelet", "rbc", "wbc", "hemoglobin",
    ]

    score = 0
    for label in labels:
        if label in low:
            score += 8

    score += min(len(text) // 200, 20)
    score += min(text.count("\n"), 40) // 2
    return score


def _adaptive_threshold(
    image: Image.Image, block_size: int = 35, offset: int = 15
) -> Image.Image:
    """
    Adaptive threshold using a local-mean approach (pure numpy).

    For each pixel, if it is darker than the mean of its local
    neighbourhood minus *offset*, it becomes black; otherwise white.
    """
    arr = np.array(image, dtype=np.float64)

    # Integral image for fast local-mean computation
    integral = arr.cumsum(axis=0).cumsum(axis=1)

    rows, cols = arr.shape
    half = block_size // 2
    out = np.ones_like(arr, dtype=np.uint8) * 255  # start white

    # Pad integral image for boundary handling
    padded = np.zeros((rows + 1, cols + 1), dtype=np.float64)
    padded[1:, 1:] = integral

    y1 = np.clip(np.arange(rows) - half, 0, rows - 1)
    y2 = np.clip(np.arange(rows) + half, 0, rows - 1) + 1
    x1 = np.clip(np.arange(cols) - half, 0, cols - 1)
    x2 = np.clip(np.arange(cols) + half, 0, cols - 1) + 1

    # Vectorised local-mean via integral image
    y1g, x1g = np.meshgrid(y1, x1, indexing="ij")
    y2g, x2g = np.meshgrid(y2, x2, indexing="ij")
    count = (y2g - y1g) * (x2g - x1g)
    local_sum = (
        padded[y2g, x2g]
        - padded[y1g, x2g]
        - padded[y2g, x1g]
        + padded[y1g, x1g]
    )
    local_mean = local_sum / np.maximum(count, 1)

    out[arr < (local_mean - offset)] = 0  # dark pixels → black

    return Image.fromarray(out, mode="L")

