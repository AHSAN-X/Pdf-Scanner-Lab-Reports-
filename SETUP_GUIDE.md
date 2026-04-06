# Medical Lab Report Extraction API - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### Step 1: Install Tesseract OCR

**Windows:**
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run installer (select default location: `C:\Program Files\Tesseract-OCR`)
3. Restart your terminal

**macOS:**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr
```

### Step 2: Install Python Dependencies

```bash
# Navigate to project directory
cd d:\LABREPOEXT

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Run the Server

```bash
# Option 1: Using Python directly
python main.py

# Option 2: Using uvicorn directly
uvicorn main:app --reload --port 8000
```

The server will start at `http://localhost:8000`

### Step 4: Test the API (Choose one)

#### Using Swagger UI (Interactive):
1. Open browser: `http://localhost:8000/docs`
2. Click on `/scan-report` endpoint
3. Click "Try it out"
4. Select a PDF or image file
5. Click "Execute"

#### Using cURL (Command line):

**Test with a PDF:**
```bash
curl -X POST "http://localhost:8000/scan-report" \
  -H "accept: application/json" \
  -F "file=@C:\path\to\lab_report.pdf"
```

**Test with an image:**
```bash
curl -X POST "http://localhost:8000/scan-report" \
  -H "accept: application/json" \
  -F "file=@C:\path\to\lab_report.jpg"
```

**Test debug endpoint:**
```bash
curl -X POST "http://localhost:8000/scan-report-debug" \
  -H "accept: application/json" \
  -F "file=@C:\path\to\lab_report.pdf"
```

#### Using Python:

Create `test_quick.py`:
```python
import requests

def test_api(file_path):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post('http://localhost:8000/scan-report', files=files)
    
    print(response.json())

# Test
test_api('lab_report.pdf')
```

Run:
```bash
python test_api.py
```

---

## 📁 Project Structure

```
d:\LABREPOEXT\
├── main.py                      # FastAPI app (START HERE)
├── requirements.txt             # Python packages to install
├── README.md                    # Full documentation
├── TESTING_GUIDE.md            # Testing instructions
├── SETUP_GUIDE.md              # This file
│
├── ocr/                         # Text extraction
│   ├── __init__.py
│   ├── image_ocr.py            # Image OCR (pytesseract)
│   └── pdf_reader.py           # PDF reader (pdfplumber)
│
├── parser/                      # Data parsing
│   ├── __init__.py
│   └── report_parser.py        # Parse lab reports
│
└── models/                      # API models
    ├── __init__.py
    └── response_model.py       # Pydantic response model
```

---

## 🔧 Configuration

### Tesseract Path (if not in default location)

Edit `ocr/image_ocr.py` and add near the top:

```python
import pytesseract

# Set path to Tesseract if not in PATH
pytesseract.pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### API Configuration

In `main.py`, you can modify:

```python
# Change port
uvicorn.run(app, host="0.0.0.0", port=8001)

# Change allowed origins for CORS (Flutter frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:19006"],  # Your Flutter dev server
)
```

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/scan-report` | Extract lab report data |
| POST | `/scan-report-debug` | Debug endpoint (returns raw text) |
| GET | `/docs` | Swagger UI documentation |
| GET | `/redoc` | ReDoc documentation |

---

## ✅ What Gets Extracted

The API automatically detects and returns:

- **Doctor Name**: Looks for "Dr.", "Doctor" patterns
- **Lab Name**: Identifies "Laboratory", "Diagnostics", "Clinic", etc.
- **Report Date**: Recognizes DD/MM/YYYY, DD-MM-YYYY, and other formats
- **Test Names**: Detects 30+ common medical tests:
  - Blood tests: CBC, WBC, RBC, Hemoglobin, Platelets
  - Chemistry: Glucose, Creatinine, Cholesterol, etc.
  - Thyroid: TSH, T3, T4
  - Liver: ALT, AST, Bilirubin
  - And more...

---

## 🐛 Troubleshooting

### "Tesseract is not installed" error
```
Solution: Install from https://github.com/UB-Mannheim/tesseract/wiki
```

### "ModuleNotFoundError: No module named 'fastapi'"
```bash
pip install -r requirements.txt
```

### Poor OCR results
- Ensure image is clear and well-lit
- Avoid shadows and reflections
- Use `/scan-report-debug` endpoint to see raw extraction
- Try different angles

### PDF shows empty results
- Verify PDF is not encrypted/password protected
- Use `/scan-report-debug` to check if text was extracted
- If PDF is scanned (image-based), use image extraction instead

### Port 8000 already in use
```bash
# Use different port
uvicorn main:app --port 8001
```

---

## 📱 Flutter Integration

In your Flutter app:

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';

class LabReportAPI {
  static const String baseUrl = 'http://your-api-domain.com';

  static Future<Map<String, dynamic>> uploadReport(File file) async {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/scan-report'),
    );
    
    request.files.add(
      await http.MultipartFile.fromPath('file', file.path),
    );
    
    var streamedResponse = await request.send();
    var response = await http.Response.fromStream(streamedResponse);
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to upload report');
    }
  }
}

// Usage:
final report = await LabReportAPI.uploadReport(File('path/to/file.pdf'));
print('Doctor: ${report['doctor_name']}');
print('Lab: ${report['lab_name']}');
print('Date: ${report['report_date']}');
print('Tests: ${report['test_names'].join(', ')}');
```

---

## 🚀 Production Deployment

### Using Gunicorn (Linux/macOS):
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### Using Docker:
```bash
# Build
docker build -t lab-report-api .

# Run
docker run -p 8000:8000 lab-report-api
```

### Cloud Platforms:
- **Heroku**: Add Procfile with `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
- **AWS EC2**: Use Gunicorn + Nginx
- **Google Cloud**: Use Cloud Run
- **Azure**: Use App Service

---

## 📚 Full Documentation

See:
- `README.md` - Complete documentation
- `TESTING_GUIDE.md` - Testing and validation
- Code comments - Implementation details

---

## 💡 Common Use Cases

### 1. Batch Process Multiple Reports
```python
import os
from pathlib import Path

files_dir = 'reports/'
for file in Path(files_dir).glob('*.pdf'):
    with open(file, 'rb') as f:
        files = {'file': f}
        response = requests.post('http://localhost:8000/scan-report', files=files)
        print(f"{file.name}: {response.json()}")
```

### 2. Save Results to Database
```python
import requests
import sqlite3
import json

conn = sqlite3.connect('reports.db')
cursor = conn.cursor()

with open('report.pdf', 'rb') as f:
    response = requests.post('http://localhost:8000/scan-report', files={'file': f})
    data = response.json()
    
    cursor.execute('''
        INSERT INTO reports (doctor_name, lab_name, report_date, tests)
        VALUES (?, ?, ?, ?)
    ''', (data['doctor_name'], data['lab_name'], data['report_date'], 
          json.dumps(data['test_names'])))
    
conn.commit()
conn.close()
```

### 3. Export Results to CSV
```python
import csv
import requests

with open('results.csv', 'w', newline='') as csvfile:
    fieldnames = ['doctor_name', 'lab_name', 'report_date', 'test_names']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    
    for report_file in ['report1.pdf', 'report2.jpg']:
        with open(report_file, 'rb') as f:
            response = requests.post('http://localhost:8000/scan-report', files={'file': f})
            writer.writerow(response.json())
```

---

## ❓ FAQ

**Q: Can I process batches of files?**
A: Yes, the API accepts one file per request. For batch processing, make multiple requests or implement a queue system.

**Q: How accurate is the OCR?**
A: Clear images: 90-95%, Moderate: 80-90%, Poor: <80%

**Q: Can it handle encrypted PDFs?**
A: No, PDFs must be unencrypted/password-free.

**Q: What's the max file size?**
A: Currently no hard limit, but files >50MB may cause memory issues.

**Q: Can I add custom medical tests?**
A: Yes, edit `MEDICAL_TESTS` dict in `parser/report_parser.py`

**Q: Is it production-ready?**
A: Yes, but add authentication, rate limiting, and error monitoring for production.

---

## 📞 Support

For detailed information, see README.md or TESTING_GUIDE.md
