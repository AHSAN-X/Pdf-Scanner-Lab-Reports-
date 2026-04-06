# Medical Lab Report Extraction API

A production-ready FastAPI application for extracting structured information from medical lab reports. Supports both PDF documents and phone camera images (JPG/PNG).

## Features

- **Multi-format Support**: Accepts PDF files and common image formats (JPG, PNG, BMP, GIF)
- **OCR Capability**: Uses Tesseract OCR for image processing via pytesseract
- **PDF Extraction**: Leverages pdfplumber for efficient PDF text extraction
- **Intelligent Parsing**: Detects and extracts:
  - Doctor names
  - Laboratory names
  - Report dates (multiple formats)
  - Medical test names (30+ common tests recognized)
- **Type-Safe API**: Uses Pydantic models for request/response validation
- **CORS Enabled**: Ready for Flutter mobile app integration
- **Debug Mode**: Includes debug endpoint for troubleshooting
- **Comprehensive Logging**: Built-in logging for monitoring and debugging

## Project Structure

```
project/
├── main.py                 # FastAPI application and endpoints
├── ocr/
│   ├── image_ocr.py       # Image OCR using pytesseract
│   └── pdf_reader.py      # PDF text extraction using pdfplumber
├── parser/
│   └── report_parser.py   # Text parsing and information extraction
├── models/
│   └── response_model.py  # Pydantic response model
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Installation

### Prerequisites

- Python 3.8+
- Tesseract OCR engine (for image processing)

### Install Tesseract

**Windows:**
1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (typically installs to `C:\Program Files\Tesseract-OCR`)
3. Update pytesseract path in your code if installed elsewhere

**macOS:**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Running the Server

### Method 1: Using Python directly
```bash
python main.py
```

### Method 2: Using uvicorn directly
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### 1. Health Check
```
GET /
```
Returns API status and version information.

**Response:**
```json
{
  "message": "Medical Lab Report Extraction API",
  "version": "1.0.0",
  "status": "running"
}
```

### 2. Scan Lab Report
```
POST /scan-report
```

Accepts a lab report file (PDF or image) and returns extracted structured data.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (binary) - PDF or image file

**Response:**
```json
{
  "doctor_name": "Dr. John Smith",
  "lab_name": "Central Diagnostic Laboratory",
  "report_date": "15/03/2024",
  "test_names": ["CBC", "HbA1c", "Glucose", "Cholesterol"]
}
```

### 3. Debug Endpoint
```
POST /scan-report-debug
```

Returns both the extracted raw text and parsed data for troubleshooting.

**Response:**
```json
{
  "extracted_text": "Raw extracted text from the file...",
  "parsed_data": {
    "doctor_name": "Dr. John Smith",
    "lab_name": "Central Diagnostic Laboratory",
    "report_date": "15/03/2024",
    "test_names": ["CBC", "HbA1c"]
  }
}
```

## Testing with cURL

### Upload and scan a PDF report:
```bash
curl -X POST "http://localhost:8000/scan-report" \
  -H "accept: application/json" \
  -F "file=@/path/to/lab_report.pdf"
```

### Upload and scan an image report:
```bash
curl -X POST "http://localhost:8000/scan-report" \
  -H "accept: application/json" \
  -F "file=@/path/to/lab_report.jpg"
```

### Use the debug endpoint:
```bash
curl -X POST "http://localhost:8000/scan-report-debug" \
  -H "accept: application/json" \
  -F "file=@/path/to/lab_report.pdf"
```

## Supported Medical Tests

The parser recognizes 30+ common medical tests including:

- **Hematology**: CBC, WBC, RBC, Hemoglobin, Hematocrit, Platelets
- **Chemistry**: Glucose, Creatinine, BUN, Calcium, Phosphorus
- **Liver Function**: ALT, AST, Bilirubin
- **Thyroid**: TSH, T3, T4
- **Lipid Profile**: Cholesterol, LDL, HDL, Triglycerides
- **Coagulation**: PT, aPTT, INR
- **Oncology**: PSA
- **Diabetic Markers**: HbA1c

## Extending the Parser

To add more medical tests:

1. Open `parser/report_parser.py`
2. Add entries to the `MEDICAL_TESTS` dictionary:

```python
MEDICAL_TESTS = {
    'TestName': ['Keyword1', 'Keyword2', 'Full Name'],
    ...
}
```

3. The parser will automatically recognize these tests

## Error Handling

The API provides detailed error messages:

- **400 Bad Request**: Unsupported file type or extraction failed
- **400 Bad Request**: No text could be extracted from the file
- **500 Internal Server Error**: Unexpected server errors

## Production Deployment

### Using Gunicorn (Linux/macOS)
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

### Using Docker
Create a `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t lab-report-api .
docker run -p 8000:8000 lab-report-api
```

## Flutter Integration Example

```dart
import 'dart:io';
import 'package:http/http.dart' as http;
import 'dart:convert';

Future<Map<String, dynamic>> uploadLabReport(File file) async {
  var request = http.MultipartRequest(
    'POST',
    Uri.parse('http://your-api-domain.com/scan-report'),
  );
  
  request.files.add(
    await http.MultipartFile.fromPath('file', file.path),
  );
  
  var response = await request.send();
  var responseData = await response.stream.bytesToString();
  
  return jsonDecode(responseData);
}
```

## Performance Tips

1. **Image Optimization**:
   - Use JPG format for faster processing than PNG
   - Ensure images are well-lit and clear
   - Avoid extreme angles or shadows

2. **PDF Optimization**:
   - Use text-based PDFs (not scanned images)
   - Ensure text layers are present in PDFs

3. **Server Configuration**:
   - Use multiple workers for concurrent requests
   - Cache Tesseract data in production
   - Apply load balancing for high traffic

## Limitations

- OCR accuracy depends on image quality (target 85-95% accuracy for clear images)
- Unusual date formats may not be detected
- Specialized medical tests not in the predefined list won't be recognized
- Large files (>50MB) may cause memory issues

## Troubleshooting

### "Tesseract is not installed" error
Install Tesseract OCR from the links in Installation section above.

### Poor OCR results
- Ensure good lighting and clear image
- Avoid shadows and reflections
- Use higher resolution images
- Check the `/scan-report-debug` endpoint to see extracted text

### PDF extraction returns empty
- Verify PDF is not encrypted
- Try the debug endpoint to see raw extraction
- Check if PDF is a scanned image (use image endpoint instead)

## License

MIT

## Support

For issues, improvements, or questions, please refer to the API documentation at `/docs` endpoint.
