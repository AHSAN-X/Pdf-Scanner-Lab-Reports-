"""
Medical Lab Report Extraction API.

A FastAPI application that accepts medical lab reports as PDF or image files
and extracts structured information including doctor name, lab name, date,
and test names.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Import custom modules
from ocr.image_ocr import extract_text_from_image
from ocr.pdf_reader import extract_text_from_pdf
from parser.report_parser import LabReportParser
from models.response_model import LabReportResponse
from services.llm_refiner import refine_with_llm


# ---------------- ENV LOADING ----------------
_PROJECT_ROOT = Path(__file__).resolve().parent

for _env_file in (".env", ".env.local", ".env.example"):
    _env_path = _PROJECT_ROOT / _env_file
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=False)


# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------- FASTAPI INIT ----------------
app = FastAPI(
    title="Medical Lab Report Extraction API",
    description="API for extracting structured information from medical lab reports",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- HELPERS ----------------
def calculate_confidence(data: dict) -> int:
    score = 0
    if data.get("doctor_name"):
        score += 25
    if data.get("lab_name"):
        score += 25
    if data.get("report_date"):
        score += 25
    if data.get("test_names"):
        score += 25
    return score


def should_refine_with_llm(parsed_data: dict, mode: str) -> bool:
    mode = (mode or "always").strip().lower()
    if mode == "always":
        return True

    critical_fields = ("patient_name", "doctor_name", "lab_name", "report_date")
    for field in critical_fields:
        value = str(parsed_data.get(field, "")).strip().lower()
        if not value:
            return True

        if field == "lab_name" and (len(value) > 90 or value.startswith("notes:")):
            return True

    return False


# ---------------- ROUTES ----------------
@app.get("/")
async def read_root():
    return {
        "message": "Medical Lab Report Extraction API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/scan-report")
async def scan_report(file: UploadFile = File(...)):
    try:
        filename = file.filename.lower()

        # ---------- OCR ----------
        if filename.endswith('.pdf'):
            logger.info(f"Processing PDF file: {filename}")
            extracted_text = await extract_text_from_pdf(file)

        elif filename.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
            logger.info(f"Processing image file: {filename}")
            extracted_text = await extract_text_from_image(file)

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {filename}"
            )

        if not extracted_text or extracted_text.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="No text extracted from file"
            )

        logger.info("Text extraction successful")

        # ---------- PARSER ----------
        parser = LabReportParser(extracted_text)
        parsed_data = parser.parse_report()
        logger.info(f"Parsed data: {parsed_data}")

        # ---------- LLM REFINEMENT ----------
        llm_used = False
        refined_fields = []
        refinement_mode = os.getenv("LLM_REFINEMENT_MODE", "always").strip().lower()

        try:
            if should_refine_with_llm(parsed_data, refinement_mode):
                refined_data = await refine_with_llm(extracted_text, parsed_data)
            else:
                logger.info("Skipping LLM refinement: mode=%s and parser quality gate passed.", refinement_mode)
                refined_data = parsed_data

            if isinstance(refined_data, dict):
                refined_fields = [
                    key for key in parsed_data.keys()
                    if refined_data.get(key) != parsed_data.get(key)
                ]
                llm_used = len(refined_fields) > 0
            else:
                refined_data = parsed_data

        except Exception as e:
            logger.warning(f"LLM failed, fallback used: {str(e)}")
            refined_data = parsed_data

        logger.info(f"Final data after refinement: {refined_data}")

        # ---------- CONFIDENCE ----------
        confidence_score = calculate_confidence(refined_data)

        # ---------- RESPONSE ----------
        response = LabReportResponse(**refined_data)
        response_dict = response.model_dump()

        # Add extra metadata (safe)
        response_dict["llm_used"] = llm_used
        response_dict["refinement_mode"] = refinement_mode
        response_dict["refined_fields"] = refined_fields
        response_dict["confidence_score"] = confidence_score

        logger.info(f"Final output: {response_dict}")

        return response_dict

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.post("/scan-report-debug")
async def scan_report_debug(file: UploadFile = File(...)):
    try:
        filename = file.filename.lower()

        if filename.endswith('.pdf'):
            extracted_text = await extract_text_from_pdf(file)

        elif filename.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
            extracted_text = await extract_text_from_image(file)

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {filename}"
            )

        parser = LabReportParser(extracted_text)
        parsed_data = parser.parse_report()

        return {
            "extracted_text": extracted_text,
            "parsed_data": parsed_data
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )