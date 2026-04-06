"""
Example usage scripts for the Medical Lab Report Extraction API.

These examples show common use cases and integration patterns.
"""

import requests
import json
from pathlib import Path
from typing import Dict, List

# ============================================================================
# EXAMPLE 1: Simple Single Report Upload
# ============================================================================

def example_simple_upload():
    """Upload a single report and retrieve results."""
    file_path = "lab_report.pdf"
    
    # Read and upload the file
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            'http://localhost:8000/scan-report',
            files=files
        )
    
    # Check success
    if response.status_code == 200:
        data = response.json()
        print(f"Doctor: {data['doctor_name']}")
        print(f"Lab: {data['lab_name']}")
        print(f"Date: {data['report_date']}")
        print(f"Tests: {', '.join(data['test_names'])}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())


# ============================================================================
# EXAMPLE 2: Batch Processing Multiple Reports
# ============================================================================

def example_batch_upload(reports_dir="reports/"):
    """Process all reports in a directory."""
    reports_dir = Path(reports_dir)
    results = []
    
    # Process each PDF and image file
    for file_path in reports_dir.glob("*.pdf"):
        print(f"Processing {file_path.name}...")
        
        with open(file_path, 'rb') as f:
            response = requests.post(
                'http://localhost:8000/scan-report',
                files={'file': f}
            )
        
        if response.status_code == 200:
            results.append({
                'file': file_path.name,
                'data': response.json()
            })
        else:
            print(f"  ⚠️ Failed to process: {response.json()['detail']}")
    
    return results


# ============================================================================
# EXAMPLE 3: Error Handling with Retry Logic
# ============================================================================

def example_upload_with_retry(file_path, max_retries=3):
    """Upload with automatic retry on failure."""
    import time
    
    for attempt in range(max_retries):
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    'http://localhost:8000/scan-report',
                    files={'file': f},
                    timeout=30
                )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code >= 500:
                # Server error, retry
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Server error. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            else:
                # Client error, don't retry
                raise requests.exceptions.HTTPError(response.text)
        
        except requests.exceptions.Timeout:
            print(f"Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    
    raise Exception(f"Failed to upload {file_path} after {max_retries} attempts")


# ============================================================================
# EXAMPLE 4: Using Debug Endpoint for Troubleshooting
# ============================================================================

def example_debug_upload(file_path):
    """Use debug endpoint to see raw extraction."""
    with open(file_path, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/scan-report-debug',
            files={'file': f}
        )
    
    data = response.json()
    
    # Show extracted text (first 500 chars)
    print("=== RAW EXTRACTED TEXT ===")
    print(data['extracted_text'][:500])
    print("...")
    
    # Show parsed data
    print("\n=== PARSED DATA ===")
    print(json.dumps(data['parsed_data'], indent=2))


# ============================================================================
# EXAMPLE 5: Save Results to JSON
# ============================================================================

def example_save_results_json(reports_dir="reports/", output_file="results.json"):
    """Process reports and save results to JSON."""
    results = []
    
    for file_path in Path(reports_dir).glob("*.pdf"):
        with open(file_path, 'rb') as f:
            response = requests.post(
                'http://localhost:8000/scan-report',
                files={'file': f}
            )
        
        if response.status_code == 200:
            results.append({
                'filename': file_path.name,
                **response.json()
            })
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {output_file}")
    return results


# ============================================================================
# EXAMPLE 6: Save Results to CSV
# ============================================================================

def example_save_results_csv(reports_dir="reports/", output_file="results.csv"):
    """Process reports and save results to CSV."""
    import csv
    
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['filename', 'doctor_name', 'lab_name', 'report_date', 'test_names']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for file_path in Path(reports_dir).glob("*.pdf"):
            with open(file_path, 'rb') as f:
                response = requests.post(
                    'http://localhost:8000/scan-report',
                    files={'file': f}
                )
            
            if response.status_code == 200:
                data = response.json()
                writer.writerow({
                    'filename': file_path.name,
                    'doctor_name': data['doctor_name'],
                    'lab_name': data['lab_name'],
                    'report_date': data['report_date'],
                    'test_names': '; '.join(data['test_names'])
                })
    
    print(f"Results saved to {output_file}")


# ============================================================================
# EXAMPLE 7: Save Results to Database (SQLite)
# ============================================================================

def example_save_results_database(reports_dir="reports/", db_file="reports.db"):
    """Process reports and save results to SQLite database."""
    import sqlite3
    import json
    from datetime import datetime
    
    # Create database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lab_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            doctor_name TEXT,
            lab_name TEXT,
            report_date TEXT,
            test_names TEXT,  -- JSON array
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert data
    for file_path in Path(reports_dir).glob("*.pdf"):
        with open(file_path, 'rb') as f:
            response = requests.post(
                'http://localhost:8000/scan-report',
                files={'file': f}
            )
        
        if response.status_code == 200:
            data = response.json()
            cursor.execute('''
                INSERT INTO lab_reports
                (filename, doctor_name, lab_name, report_date, test_names)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                file_path.name,
                data['doctor_name'],
                data['lab_name'],
                data['report_date'],
                json.dumps(data['test_names'])
            ))
    
    conn.commit()
    print(f"Results saved to {db_file}")
    
    # Example query
    cursor.execute('SELECT * FROM lab_reports LIMIT 5')
    for row in cursor.fetchall():
        print(row)
    
    conn.close()


# ============================================================================
# EXAMPLE 8: API with Custom Headers and Authentication
# ============================================================================

def example_upload_with_auth(file_path, api_key="your-api-key"):
    """Upload with authentication headers."""
    headers = {
        'X-API-Key': api_key,
        'User-Agent': 'MyLabApp/1.0'
    }
    
    with open(file_path, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/scan-report',
            files={'file': f},
            headers=headers,
            timeout=30
        )
    
    return response.json() if response.status_code == 200 else None


# ============================================================================
# EXAMPLE 9: Performance Benchmarking
# ============================================================================

def example_performance_test():
    """Benchmark API performance with multiple files."""
    import time
    import statistics
    
    test_file = "lab_report.pdf"
    num_requests = 5
    response_times = []
    
    print(f"Running {num_requests} requests...")
    
    for i in range(num_requests):
        start_time = time.time()
        
        with open(test_file, 'rb') as f:
            response = requests.post(
                'http://localhost:8000/scan-report',
                files={'file': f}
            )
        
        elapsed = time.time() - start_time
        response_times.append(elapsed)
        
        status = "✓" if response.status_code == 200 else "✗"
        print(f"  Request {i+1}: {elapsed:.2f}s {status}")
    
    # Statistics
    print(f"\n=== Performance Statistics ===")
    print(f"Min: {min(response_times):.2f}s")
    print(f"Max: {max(response_times):.2f}s")
    print(f"Average: {statistics.mean(response_times):.2f}s")
    print(f"Median: {statistics.median(response_times):.2f}s")
    print(f"Std Dev: {statistics.stdev(response_times):.2f}s")


# ============================================================================
# EXAMPLE 10: Concurrent Processing with ThreadPoolExecutor
# ============================================================================

def example_concurrent_upload(reports_dir="reports/", max_workers=5):
    """Process multiple reports concurrently."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def upload_file(file_path):
        with open(file_path, 'rb') as f:
            response = requests.post(
                'http://localhost:8000/scan-report',
                files={'file': f}
            )
        return file_path.name, response.json() if response.status_code == 200 else None
    
    results = {}
    files = list(Path(reports_dir).glob("*.pdf"))
    
    print(f"Uploading {len(files)} files with {max_workers} workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(upload_file, f): f for f in files}
        
        for future in as_completed(futures):
            filename, data = future.result()
            results[filename] = data
            print(f"  ✓ {filename}")
    
    return results


# ============================================================================
# EXAMPLE 11: Flask Web Interface
# ============================================================================

def example_flask_integration():
    """
    Example Flask app that wraps the API.
    
    Usage:
        python examples.py
        # Then visit http://localhost:5000
    """
    from flask import Flask, render_template, request, jsonify
    import requests
    
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return '''
        <html>
            <head><title>Lab Report Upload</title></head>
            <body>
                <h1>Medical Lab Report Extraction</h1>
                <form action="/upload" method="post" enctype="multipart/form-data">
                    <input type="file" name="file" accept=".pdf,.jpg,.png" required>
                    <button type="submit">Extract</button>
                </form>
                <div id="results"></div>
                <script>
                    document.querySelector('form').addEventListener('submit', async (e) => {
                        e.preventDefault();
                        const formData = new FormData();
                        formData.append('file', document.querySelector('input[type=file]').files[0]);
                        
                        const response = await fetch('/api/scan', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const data = await response.json();
                        document.getElementById('results').innerHTML = 
                            '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    });
                </script>
            </body>
        </html>
        '''
    
    @app.route('/api/scan', methods=['POST'])
    def scan():
        file = request.files['file']
        
        # Forward to backend API
        response = requests.post(
            'http://localhost:8000/scan-report',
            files={'file': (file.filename, file.stream, file.content_type)}
        )
        
        return jsonify(response.json())
    
    app.run(debug=True, port=5000)


# ============================================================================
# EXAMPLE 12: Command Line Tool
# ============================================================================

def example_cli_tool():
    """
    Example command-line interface.
    
    Usage:
        python examples.py scan report.pdf
        python examples.py batch reports/
        python examples.py debug report.pdf
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Medical Lab Report Extraction CLI')
    subparsers = parser.add_subparsers(dest='command')
    
    # scan command
    scan_parser = subparsers.add_parser('scan', help='Scan a report')
    scan_parser.add_argument('file', help='Report file (PDF or image)')
    scan_parser.add_argument('--json', action='store_true', help='Output JSON')
    
    # batch command
    batch_parser = subparsers.add_parser('batch', help='Batch process reports')
    batch_parser.add_argument('directory', help='Directory containing reports')
    batch_parser.add_argument('--output', help='Output file (JSON or CSV)')
    
    # debug command
    debug_parser = subparsers.add_parser('debug', help='Debug mode')
    debug_parser.add_argument('file', help='Report file')
    
    args = parser.parse_args()
    
    # Handle commands
    if args.command == 'scan':
        result = example_upload_with_retry(args.file)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Doctor: {result['doctor_name']}")
            print(f"Lab: {result['lab_name']}")
            print(f"Date: {result['report_date']}")
            print(f"Tests: {', '.join(result['test_names'])}")


# ============================================================================
# Run Examples
# ============================================================================

if __name__ == "__main__":
    # Uncomment to run examples:
    
    # example_simple_upload()
    # results = example_batch_upload("reports/")
    # data = example_upload_with_retry("lab_report.pdf")
    # example_debug_upload("lab_report.pdf")
    # example_save_results_json()
    # example_save_results_csv()
    # example_save_results_database()
    # example_performance_test()
    # example_concurrent_upload()
    
    print("See the example functions to learn how to use the API!")
