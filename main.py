"""
Medical Lab Report Extraction API.

A FastAPI application that accepts medical lab reports as PDF or image filescurl -X POST "http://localhost:8000/scan-report" `
  -H "accept: application/json" `
  -F "file=@D:\LABREPOEXT\LabRep.pdf"
and extracts structured information including doctor name, lab name, date,
and test names.

This API is designed to work with both physical lab reports captured via
phone camera (images) and digital PDF reports.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Optional

# Import custom modules
from ocr.image_ocr import extract_text_from_image
from ocr.pdf_reader import extract_text_from_pdf
from parser.report_parser import LabReportParser
from models.response_model import LabReportResponse


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Medical Lab Report Extraction API",
    description="API for extracting structured information from medical lab reports",
    version="1.0.0"
)

# Add CORS middleware for Flutter frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    """
    Health check endpoint.
    
    Returns:
        dict: API status and version information
    """
    return {
        "message": "Medical Lab Report Extraction API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/scan-report", response_model=LabReportResponse)
async def scan_report(file: UploadFile = File(...)) -> LabReportResponse:
    """
    Main endpoint to extract information from a lab report.
    
    Accepts either a PDF file or an image (JPG/PNG) of a lab report.
    Extracts text and parses it to return structured JSON response.
    
    Args:
        file (UploadFile): The uploaded file (PDF or image)
        
    Returns:
        LabReportResponse: Structured extracted information
        
    Raises:
        HTTPException: If file type is not supported or processing fails
    """
    try:
        # Validate file type
        filename = file.filename.lower()
        
        if filename.endswith('.pdf'):
            # Process PDF file
            logger.info(f"Processing PDF file: {filename}")
            extracted_text = await extract_text_from_pdf(file)
            
        elif filename.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
            # Process image file
            logger.info(f"Processing image file: {filename}")
            extracted_text = await extract_text_from_image(file)
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {filename}. Please upload a PDF or image (JPG, PNG, BMP, GIF)."
            )
        
        # Check if text was extracted
        if not extracted_text or extracted_text.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the uploaded file. Please ensure the file is clear and readable."
            )
        
        logger.info("Text extraction successful. Starting parsing...")
        
        # Parse extracted text
        parser = LabReportParser(extracted_text)
        parsed_data = parser.parse_report()
        
        logger.info(f"Parsing complete. Extracted data: {parsed_data}")
        
        # Create response model
        response = LabReportResponse(**parsed_data)
        
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Processing error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Error processing file: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the file."
        )


@app.post("/scan-report-debug")
async def scan_report_debug(file: UploadFile = File(...)):
    """
    Debug endpoint that returns both extracted text and parsed data.
    
    Useful for troubleshooting and improving the parser.
    
    Args:
        file (UploadFile): The uploaded file (PDF or image)
        
    Returns:
        dict: Contains extracted_text and parsed_data
    """
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    # Use: python main.py
    # Then access the API at: http://localhost:8000
    # Swagger UI at: http://localhost:8000/docs
    # ReDoc at: http://localhost:8000/redoc
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
