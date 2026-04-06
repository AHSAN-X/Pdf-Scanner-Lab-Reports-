# Testing Guide for Medical Lab Report API

## Prerequisites
- Python 3.8+
- Tesseract OCR installed
- FastAPI server running

## Test Cases

### 1. Test with Sample PDF

Create a sample lab report PDF text file and test:

```bash
curl -X POST "http://localhost:8000/scan-report" \
  -H "accept: application/json" \
  -F "file=@sample_report.pdf"
```

### 2. Test with Sample Image

```bash
curl -X POST "http://localhost:8000/scan-report" \
  -H "accept: application/json" \
  -F "file=@lab_report.jpg"
```

### 3. Test with Invalid File Type

```bash
curl -X POST "http://localhost:8000/scan-report" \
  -H "accept: application/json" \
  -F "file=@document.txt"
```
Expected: 400 error about unsupported file type

### 4. Test Debug Endpoint

```bash
curl -X POST "http://localhost:8000/scan-report-debug" \
  -H "accept: application/json" \
  -F "file=@sample_report.pdf"
```

Expected: Response with both `extracted_text` and `parsed_data`

### 5. Swagger UI Testing

Navigate to `http://localhost:8000/docs` and use the interactive Swagger UI:
1. Click "Try it out" on the `/scan-report` endpoint
2. Click "Choose File" and select a lab report
3. Click "Execute"
4. View the response

### 6. Sample Lab Report for Testing

Create a test file `sample_report.txt`:

```
CENTRAL DIAGNOSTIC LABORATORY
123 Medical Plaza, Healthcare City
Tel: +1-234-567-8900
Website: www.centrallab.com

===================================
LABORATORY REPORT
===================================

Patient Name: John Doe
Age: 35 years
Gender: Male
Report Date: 15/03/2024

Referred by: Dr. Michael Johnson
Cardiologist

===================================
CLINICAL TEST RESULTS
===================================

Test Name              | Result    | Unit
-------------------------------------------
Complete Blood Count  | See below | -
Hemoglobin           | 14.5      | g/dL
Hematocrit           | 43%       | %
WBC Count            | 7,200     | /μL
RBC Count            | 4.8       | million/μL
Platelet Count       | 250,000   | /μL

Glucose (Fasting)    | 105       | mg/dL
HbA1c                | 5.9       | %
Total Cholesterol    | 185       | mg/dL
LDL Cholesterol      | 110       | mg/dL
HDL Cholesterol      | 50        | mg/dL
Triglycerides        | 150       | mg/dL

Creatinine           | 1.0       | mg/dL
BUN                  | 18        | mg/dL
Calcium              | 9.5       | mg/dL
Phosphorus           | 3.5       | mg/dL

ALT                  | 25        | U/L
AST                  | 22        | U/L
Bilirubin            | 0.8       | mg/dL

TSH                  | 2.5       | mIU/L
T3                   | 3.2       | ng/mL
T4                   | 8.5       | ng/dL

===================================
INTERPRETATION
===================================

All values are within normal reference ranges.
No abnormalities detected.

===================================
```

To test with this text as a simple PDF:
1. Create the text file
2. Use a tool like `reportlab` or online converter to convert to PDF
3. Test with the API

### Python Test Script

Create `test_api.py`:

```python
import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test health check endpoint"""
    response = requests.get(f"{BASE_URL}/")
    print("Health Check:")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_file_upload(file_path):
    """Test file upload"""
    if not Path(file_path).exists():
        print(f"File not found: {file_path}\n")
        return
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{BASE_URL}/scan-report", files=files)
    
    print(f"Upload Test ({file_path}):")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def test_debug_endpoint(file_path):
    """Test debug endpoint"""
    if not Path(file_path).exists():
        print(f"File not found: {file_path}\n")
        return
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{BASE_URL}/scan-report-debug", files=files)
    
    print(f"Debug Endpoint Test ({file_path}):")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Extracted Text (first 200 chars):\n{data['extracted_text'][:200]}...\n")
        print(f"Parsed Data: {json.dumps(data['parsed_data'], indent=2)}\n")
    else:
        print(f"Error: {response.json()}\n")

if __name__ == "__main__":
    # Run tests
    test_health_check()
    
    # Test with your own files
    test_file_upload("sample_report.pdf")
    test_debug_endpoint("sample_report.pdf")
```

Run:
```bash
python test_api.py
```

## Expected Output Examples

### Successful PDF Upload:
```json
{
  "doctor_name": "Dr. Michael Johnson",
  "lab_name": "CENTRAL DIAGNOSTIC LABORATORY",
  "report_date": "15/03/2024",
  "test_names": [
    "ALT",
    "AST",
    "Bilirubin",
    "BUN",
    "CBC",
    "Calcium",
    "Cholesterol",
    "Creatinine",
    "Glucose",
    "HbA1c",
    "HDL",
    "Hemoglobin",
    "LDL",
    "Phosphorus",
    "Platelets",
    "RBC",
    "T3",
    "T4",
    "Triglycerides",
    "TSH",
    "WBC"
  ]
}
```

## Performance Benchmarks

### Expected Response Times:
- **PDF extraction**: 200-500ms
- **Image OCR**: 1-3 seconds
- **Parsing**: 50-100ms
- **Total (PDF)**: 300-600ms
- **Total (Image)**: 1.1-3.1 seconds

## Accuracy Testing

### For OCR (Images):
- Clear images: 90-95% accuracy
- Moderate quality: 80-90% accuracy
- Poor quality: <80% accuracy

### For PDF:
- Text-based PDF: 99%+ accuracy
- Scanned PDF: Depends on scan quality (60-95%)

## Edge Cases to Test

1. **Empty File**: Should return error
2. **Corrupted PDF**: Should return error
3. **Very Large File** (>50MB): May timeout or consume memory
4. **Encrypted PDF**: Should return error
5. **Image with Heavy Artifacts**: May have low OCR accuracy
6. **Missing Fields**: Should return empty strings for missing fields
7. **Uppercase/Lowercase Variations**: Parser should handle these
8. **Multiple Doctors**: Parser takes the first detected
9. **Multiple Labs**: Parser takes the first detected
10. **Different Date Formats**: Parser should recognize DD/MM/YYYY, DD-MM-YYYY, etc.

## Continuous Integration Testing

For CI/CD pipelines, create `test_integration.py`:

```python
import pytest
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"

class TestLabReportAPI:
    
    def test_health_check(self):
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        assert response.json()["status"] == "running"
    
    def test_unsupported_file_type(self, tmp_path):
        # Create dummy file with wrong extension
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        with open(test_file, 'rb') as f:
            response = requests.post(
                f"{BASE_URL}/scan-report",
                files={'file': f}
            )
        
        assert response.status_code == 400
    
    def test_response_structure(self):
        # Placeholder - requires actual test file
        pass

# Run with: pytest test_integration.py
```

## Load Testing

For performance testing, use Apache Bench or similar:

```bash
# Install Apache Bench (if not available)
# macOS: brew install httpd
# Linux: sudo apt-get install apache2-utils

# Test 100 requests with 10 concurrent connections
ab -n 100 -c 10 http://localhost:8000/
```

## Monitoring

Monitor your API deployment with:

```bash
# Check logs in real-time
tail -f app.log

# Monitor memory usage
watch -n 1 'ps aux | grep "uvicorn\|tesseract"'

# Monitor network connections
netstat -an | grep 8000
```
