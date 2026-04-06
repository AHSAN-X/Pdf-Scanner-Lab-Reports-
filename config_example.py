"""
Example configuration file for the Medical Lab Report Extraction API.

Copy this to config.py and modify as needed for your deployment.
"""

import os
from typing import List

# API Configuration
API_TITLE = "Medical Lab Report Extraction API"
API_VERSION = "1.0.0"
API_DESCRIPTION = "Extract structured data from medical lab reports"

# Server Configuration
HOST = os.getenv("API_HOST", "0.0.0.0")
PORT = int(os.getenv("API_PORT", 8000))
RELOAD = os.getenv("API_RELOAD", "True").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "app.log")

# CORS Configuration
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:19006",  # Flutter dev server
    # Add your frontend URLs here
]

# File Upload Configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB
ALLOWED_FILE_TYPES = {
    "application/pdf": [".pdf"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/bmp": [".bmp"],
    "image/gif": [".gif"],
}

# Tesseract Configuration
TESSERACT_PATH = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Windows default
)

# PDF Processing
PDF_TIMEOUT = int(os.getenv("PDF_TIMEOUT", 30))  # seconds
PDF_MAX_PAGES = int(os.getenv("PDF_MAX_PAGES", 0))  # 0 = no limit

# OCR Configuration
OCR_TIMEOUT = int(os.getenv("OCR_TIMEOUT", 60))  # seconds
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "eng")  # Tesseract language codes

# Cache Configuration
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "False").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))  # seconds

# Database (optional)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./reports.db"
)

# Authentication (optional)
API_KEY_ENABLED = os.getenv("API_KEY_ENABLED", "False").lower() == "true"
API_KEY = os.getenv("API_KEY", "your-secure-api-key-here")

# Rate Limiting (optional)
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "False").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 100))  # requests
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", 60))  # seconds

# Security
SECURE_MODE = os.getenv("SECURE_MODE", "False").lower() == "true"
HTTPS_ONLY = os.getenv("HTTPS_ONLY", "False").lower() == "true"

# Monitoring
SENTRY_DSN = os.getenv("SENTRY_DSN", None)  # For error tracking
PROMETHEUS_METRICS = os.getenv("PROMETHEUS_METRICS", "False").lower() == "true"

# Debug
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
