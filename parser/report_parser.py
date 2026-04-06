"""
Lab report parser – extracts structured data from OCR text.

Designed to be resilient against OCR noise:
    • Fuzzy keyword matching for lab/clinic names
    • Multiple date-format support with OCR-typo correction
    • Broad medical-test dictionary with common OCR misspellings
    • Doctor-name extraction with multiple patterns
    • Patient info extraction (name, age, gender, patient ID)
"""

import re
from typing import List, Dict, Optional


class LabReportParser:
    """Parse raw OCR text from a medical lab report into structured fields."""

    # ── Medical test dictionary ───────────────────────────────────────
    # Each key is the canonical name; values are keywords that trigger it.
    MEDICAL_TESTS: Dict[str, List[str]] = {
        # Haematology – CBC
        'CBC': ['Complete Blood Count', 'CBC', 'Full Blood Count', 'FBC'],
        'Hemoglobin': ['Hemoglobin', 'Haemoglobin', 'Hb', 'HB', 'Hemoglobin Level'],
        'WBC': ['WBC', 'White Blood Cell', 'White Blood Cells', 'WAC', 'Total WBC', 'WBC Count'],
        'RBC': ['RBC', 'Red Blood Cell', 'Red Blood Cells', 'Red Blood Cals', 'Total RBC'],
        'Platelets': ['Platelets', 'Platelet Count', 'Platelet'],
        'Hematocrit': ['Hematocrit', 'Haematocrit', 'Hct', 'HCT', 'Hematocit'],
        'PCV': ['PCV', 'Packed Cell Volume'],
        'MCV': ['MCV', 'Mean Corpuscular Volume'],
        'MCH': ['MCH', 'Mean Corpuscular Hemoglobin', 'Mean Corpuscular Haemoglobin'],
        'MCHC': ['MCHC', 'Mean Corpuscular Hemoglobin Concentration'],
        'RDW': ['RDW', 'Red Cell Distribution Width'],
        'ESR': ['ESR', 'Erythrocyte Sedimentation Rate'],

        # Differential WBC
        'Neutrophils': ['Neutrophils', 'Neutrophil', 'Neutro'],
        'Lymphocytes': ['Lymphocytes', 'Lymphocyte', 'Lympho'],
        'Eosinophils': ['Eosinophils', 'Eosinophil', 'Eosino'],
        'Monocytes': ['Monocytes', 'Monocyte', 'Mono'],
        'Basophils': ['Basophils', 'Basophil', 'Baso'],

        # Diabetes
        'HbA1c': ['HbA1c', 'Glycated Hemoglobin', 'Hemoglobin A1c', 'Glycated Haemoglobin', 'A1C'],
        'Glucose': ['Glucose', 'Fasting Glucose', 'Blood Glucose', 'FBS', 'PPBS',
                     'Random Blood Sugar', 'Blood Sugar'],

        # Lipid Panel
        'Total Cholesterol': ['Total Cholesterol', 'Cholesterol'],
        'HDL': ['HDL', 'High Density Lipoprotein'],
        'LDL': ['LDL', 'Low Density Lipoprotein'],
        'Triglycerides': ['Triglycerides', 'TG', 'Triglyceride'],
        'VLDL': ['VLDL', 'Very Low Density Lipoprotein'],

        # Liver Function Tests
        'SGOT/AST': ['SGOT', 'AST', 'Aspartate Aminotransferase', 'Aspartate Transaminase'],
        'SGPT/ALT': ['SGPT', 'ALT', 'Alanine Aminotransferase', 'Alanine Transaminase'],
        'Bilirubin': ['Bilirubin', 'Total Bilirubin', 'Direct Bilirubin'],
        'Alkaline Phosphatase': ['Alkaline Phosphatase', 'ALP'],
        'GGT': ['GGT', 'Gamma GT', 'Gamma Glutamyl Transferase'],
        'Albumin': ['Albumin'],
        'Total Protein': ['Total Protein'],

        # Kidney Function Tests
        'Creatinine': ['Creatinine', 'Serum Creatinine'],
        'BUN': ['BUN', 'Blood Urea Nitrogen'],
        'Urea': ['Urea', 'Blood Urea'],
        'Uric Acid': ['Uric Acid'],
        'eGFR': ['eGFR', 'GFR', 'Glomerular Filtration Rate'],

        # Thyroid Panel
        'TSH': ['TSH', 'Thyroid Stimulating Hormone'],
        'T3': ['T3', 'Triiodothyronine'],
        'T4': ['T4', 'Thyroxine', 'Free T4', 'FT4'],

        # Electrolytes / Minerals
        'Sodium': ['Sodium', 'Na+', 'Serum Sodium'],
        'Potassium': ['Potassium', 'K+', 'Serum Potassium'],
        'Calcium': ['Calcium', 'Serum Calcium'],
        'Iron': ['Iron', 'Serum Iron', 'Iron Studies'],
        'Ferritin': ['Ferritin'],
        'Vitamin D': ['Vitamin D', 'Vit D', '25-OH Vitamin D', '25 Hydroxy'],
        'Vitamin B12': ['Vitamin B12', 'Vit B12', 'Cobalamin'],

        # Urinalysis
        'Urinalysis': ['Urinalysis', 'Urine Routine', 'Urine Analysis', 'Urine Test'],

        # Coagulation
        'PT': ['Prothrombin Time', 'PT/INR'],
        'INR': ['INR'],
        'aPTT': ['aPTT', 'APTT', 'Activated Partial Thromboplastin'],

        # Infection / Serology
        'CRP': ['CRP', 'C-Reactive Protein', 'C Reactive Protein'],
        'HIV': ['HIV'],
        'HBsAg': ['HBsAg', 'Hepatitis B'],
        'HCV': ['HCV', 'Hepatitis C'],
        'Dengue': ['Dengue', 'NS1', 'Dengue NS1'],
        'Malaria': ['Malaria', 'MP', 'Malaria Parasite'],
        'Widal': ['Widal', 'Typhoid'],
        'Covid': ['COVID', 'SARS-CoV', 'RT-PCR', 'Covid-19'],
    }

    # ── Month OCR corrections ────────────────────────────────────────
    MONTHS_CORRECT: Dict[str, str] = {
        "jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr",
        "may": "May", "jun": "Jun", "jul": "Jul", "aug": "Aug",
        "sep": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec",
        # OCR common typos
        "juy": "Jul", "yul": "Jul", "iul": "Jul",
        "agt": "Aug", "aog": "Aug", "auq": "Aug",
        "dece": "Dec", "oec": "Dec",
        "noy": "Nov", "nev": "Nov",
        "oet": "Oct", "oot": "Oct",
        "seo": "Sep", "sef": "Sep",
    }

    # ── Patient-field markers (used to skip non-lab-name lines) ──────
    _PATIENT_FIELDS = [
        'number:', 'age:', 'gender:', 'patient:', 'existing',
        'collection date:', 'received date:', 'report date:',
        'reported on:', 'registered on:', 'collected on:',
        'sex:', 'pid:', 'sample collected',
    ]

    # ── Lab/clinic keywords (including OCR variants) ─────────────────
    _LAB_KEYWORDS = [
        'lab', 'laboratory', 'pathology',
        'clinic', 'cline', 'cinic', 'clinc',
        'hospital', 'diagnostic', 'diagnostics',
        'center', 'centre', 'medical',
        'health', 'healthcare',
    ]

    # ──────────────────────────────────────────────────────────────────
    def __init__(self, text: str):
        self.text = text
        self.text_lower = text.lower()
        self.lines = [l for l in text.split('\n')]

    def parse_report(self) -> Dict[str, object]:
        """Return all extracted fields."""
        return {
            'patient_name': self.extract_patient_name(),
            'patient_age': self.extract_patient_age(),
            'patient_gender': self.extract_patient_gender(),
            'doctor_name': self.extract_doctor_name(),
            'lab_name': self.extract_lab_name(),
            'report_date': self.extract_report_date(),
            'test_names': self.extract_test_names(),
        }

    # ── Doctor name ──────────────────────────────────────────────────
    def extract_doctor_name(self) -> str:
        patterns = [
            # "Requesting doctor: Dr. First Last" / "Ref. By: Dr. First Last"
            r'(?:requesting\s+doctor|ref\.?\s*(?:by)?|referred\s+by)[:\s]*'
            r'(?:Dr\.?|Or\.?)?\s*([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)',
            # "Dr. First Last" standalone
            r'(?:Dr|Or)\.?\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)',
        ]
        for pat in patterns:
            match = re.search(pat, self.text)
            if match:
                return match.group(1).strip()
        return ""

    # ── Patient name ─────────────────────────────────────────────────
    def extract_patient_name(self) -> str:
        patterns = [
            r'[Pp]atient[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)',
            r'[Nn]ame[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)',
        ]
        for pat in patterns:
            match = re.search(pat, self.text)
            if match:
                return match.group(1).strip()
        return ""

    # ── Patient age ──────────────────────────────────────────────────
    def extract_patient_age(self) -> str:
        match = re.search(r'[Aa]ge[:\s]*(\d{1,3})\s*(?:years?|yrs?|Y)?', self.text)
        return match.group(1) if match else ""

    # ── Patient gender ───────────────────────────────────────────────
    def extract_patient_gender(self) -> str:
        match = re.search(
            r'(?:gender|sex)[:\s]*(male|female|m|f)\b', self.text, re.IGNORECASE
        )
        if match:
            val = match.group(1).strip().capitalize()
            return {"M": "Male", "F": "Female"}.get(val, val)
        return ""

    # ── Lab / clinic name ────────────────────────────────────────────
    def extract_lab_name(self) -> str:
        header_lines = self.lines[:20]

        for line in header_lines:
            stripped = line.strip()
            if not stripped or len(stripped) > 120:
                continue
            low = stripped.lower()
            if any(f in low for f in self._PATIENT_FIELDS):
                continue
            # Must contain a lab-like keyword
            if any(kw in low for kw in self._LAB_KEYWORDS):
                return stripped

        # Fallback: first non-empty, non-patient-field line
        for line in header_lines:
            stripped = line.strip()
            if stripped:
                low = stripped.lower()
                if not any(f in low for f in self._PATIENT_FIELDS):
                    return stripped
        return ""

    # ── Report date ──────────────────────────────────────────────────
    def extract_report_date(self) -> str:
        date_patterns = [
            # "02 Dec 2024", "02 Dec, 2024", "02 Dec, 2X"
            r'(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(\d{2,4}[0-9X]*)',
            # "02/12/2024", "02-12-2024"
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
            # "2024-12-02", "2024/12/02"
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
        ]

        # Priority: look near "report date" / "reported on" labels
        report_kw = ['reported on', 'report date', 'reported date', 'reporting date']
        for kw in report_kw:
            idx = self.text_lower.find(kw)
            if idx == -1:
                continue
            snippet = self.text[idx:idx + 60]
            for pat in date_patterns:
                m = re.search(pat, snippet, re.IGNORECASE)
                if m:
                    return self._format_date(*m.groups())

        # Fallback: any date in the text
        for pat in date_patterns:
            m = re.search(pat, self.text, re.IGNORECASE)
            if m:
                return self._format_date(*m.groups())
        return ""

    def _format_date(self, a: str, b: str, c: str) -> str:
        """Normalise a captured date triple into a readable string."""
        # If first group is 4-digit year → ISO format
        if re.match(r'^\d{4}$', a):
            day, month, year = c, b, a
        else:
            day, month, year = a, b, c

        # If month is alphabetic, fix OCR typos
        if re.match(r'^[A-Za-z]+$', month):
            month = self.MONTHS_CORRECT.get(month.lower(), month.capitalize())

        # If year looks valid (4 digits), include it
        if re.match(r'^\d{4}$', year):
            return f"{day} {month} {year}"
        return f"{day} {month}"

    # ── Test names ───────────────────────────────────────────────────
    def extract_test_names(self) -> List[str]:
        detected: set = set()
        low = self.text_lower
        for canonical, keywords in self.MEDICAL_TESTS.items():
            for kw in keywords:
                if kw.lower() in low:
                    detected.add(canonical)
                    break
        return sorted(detected)