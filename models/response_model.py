"""
Response model for lab report extraction.

This module defines the Pydantic model for API responses,
ensuring type safety and automatic JSON serialization.
"""

from pydantic import BaseModel
from typing import List


class LabReportResponse(BaseModel):
    """
    Pydantic model for structured lab report extraction response.

    Attributes:
        patient_name (str): Name of the patient
        patient_age (str): Age of the patient
        patient_gender (str): Gender of the patient
        doctor_name (str): Name of the doctor mentioned in the report
        lab_name (str): Name of the laboratory
        report_date (str): Date of the report
        test_names (List[str]): List of medical tests detected in the report
    """
    patient_name: str = ""
    patient_age: str = ""
    patient_gender: str = ""
    doctor_name: str = ""
    lab_name: str = ""
    report_date: str = ""
    test_names: List[str] = []

    class Config:
        """Pydantic config for JSON schema generation."""
        json_schema_extra = {
            "example": {
                "patient_name": "Jane Doe",
                "patient_age": "45",
                "patient_gender": "Female",
                "doctor_name": "Dr. John Smith",
                "lab_name": "Central Diagnostic Lab",
                "report_date": "15 Mar 2024",
                "test_names": ["CBC", "HbA1c", "Glucose", "Total Cholesterol"]
            }
        }
