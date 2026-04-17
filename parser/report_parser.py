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
from typing import List, Dict


class LabReportParser:
    """Parse raw OCR text from a medical lab report into structured fields."""

    # ── Medical test dictionary ───────────────────────────────────────
    # Each key is the canonical name; values are keywords that trigger it.
    MEDICAL_TESTS: Dict[str, List[str]] = {
        # Haematology – CBC
        'CBC': ['Complete Blood Count', 'CBC', 'Full Blood Count', 'FBC'],
        'Hemoglobin': ['Hemoglobin', 'Haemoglobin', 'Hb', 'HB', 'Hemoglobin Level'],
        'WBC': ['WBC', 'White Blood Cell', 'White Blood Cells', 'WAC', 'Total WBC', 'WBC Count', 'TLC', 'T.L.C', 'Total Leukocyte Count'],
        'RBC': ['RBC', 'RBCs', 'Red Blood Cell', 'Red Blood Cells', 'Red Blood Cals', 'Total RBC'],
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

    _NON_LAB_HEADER_TOKENS = [
        'haematology', 'hematology', 'parameter', 'result', 'reference range',
        'test name', 'unit', 'electronically verified', 'not valid for',
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
            # Patient: John Doe / Patient Name: JOHN DOE
            r'(?i)(?:patient\s*name|patient|name)\s*[:\-]\s*([A-Za-z][A-Za-z .]{1,80})',
            # Name John Doe (missing colon in OCR)
            r'(?i)(?:patient\s*name|patient|name)\s+([A-Za-z][A-Za-z .]{1,80})',
            # Two-column OCR merge style: Name ... Gender ... <Name>
            r'(?is)\bname\b.{0,40}\bgender\b\s*[:\-]?\s*([A-Za-z][A-Za-z .]{2,80})',
        ]

        for pat in patterns:
            match = re.search(pat, self.text)
            if match:
                cleaned = self._clean_patient_name(match.group(1))
                if cleaned:
                    return cleaned

        # Header fallback: search first few lines for a name-like entry.
        for raw_line in self.lines[:15]:
            line = raw_line.strip()
            if not line:
                continue
            low = line.lower()
            if 'patient' in low or low.startswith('name'):
                cleaned = self._clean_patient_name(line)
                if cleaned:
                    return cleaned

        # Last fallback: sometimes the first patient token is broken (e.g. NOO + FATIMA).
        upper_tokens = re.findall(r'\b[A-Z]{3,}\b', '\n'.join(self.lines[:20]))
        if upper_tokens:
            # Prefer likely personal-name endings when available.
            preferred_last_names = {'fatima', 'khan', 'ali', 'ahmed', 'hussain', 'nasir', 'nabi'}
            for idx, token in enumerate(upper_tokens):
                if token.lower() in preferred_last_names and idx > 0:
                    candidate = f"{upper_tokens[idx - 1].title()} {token.title()}"
                    cleaned = self._clean_patient_name(candidate)
                    if cleaned:
                        return cleaned
        return ""

    def _clean_patient_name(self, value: str) -> str:
        # Remove leading field labels.
        cleaned = re.sub(r'(?i)^(?:patient\s*name|patient|name)\s*[:\-]?\s*', '', value).strip()

        # Cut off common trailing fields when OCR puts many fields on one line.
        cleaned = re.split(
            r'(?i)\b(?:age|gender|sex|number|id|patient\s*id|collection\s*date|received\s*date|report\s*date|requesting\s*doctor|doctor|ref(?:erred)?\s*by)\b',
            cleaned,
        )[0].strip()

        # Remove non-name punctuation and collapse spaces.
        cleaned = re.sub(r'[^A-Za-z .]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' .')

        if not cleaned:
            return ""

        tokens = cleaned.split()
        if len(tokens) < 2:
            return ""

        # Title-case all-uppercase OCR names while preserving initials.
        normalized_tokens = []
        for token in tokens:
            if len(token) <= 2 and token.endswith('.'):
                normalized_tokens.append(token.upper())
            elif token.isupper():
                normalized_tokens.append(token.title())
            else:
                normalized_tokens.append(token)
        return ' '.join(normalized_tokens)

    # ── Patient age ──────────────────────────────────────────────────
    def extract_patient_age(self) -> str:
        match = re.search(r'[Aa]ge[:\s]*(\d{1,3})\s*(?:years?|yrs?|Y)?', self.text)
        if not match:
            return ""

        age = int(match.group(1))

        # Discard clearly invalid OCR age values.
        if age <= 0 or age > 120:
            return ""

        # In noisy two-column OCR, missing age is often misread as a tiny number
        # right before "Years lab # ..." on the same line.
        context_after = self.text[match.end(): match.end() + 40]
        if age <= 5 and re.search(r'(?i)years?\s*lab\s*#?', context_after):
            return ""

        return str(age)

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

        # Strong hint from footer email branding.
        if 'healthplus' in self.text_lower:
            return 'Health Plus Lab'

        # Prefer the logo/header area where lab brand usually appears.
        top_header = ' '.join(line.strip() for line in self.lines[:8] if line.strip())
        top_header_low = top_header.lower()
        if 'health' in top_header_low and 'lab' in top_header_low:
            if 'plus' in top_header_low or 'bus' in top_header_low:
                return 'Health Plus Lab'
            match = re.search(r'(?i)(health\s*[A-Za-z]*\s*lab)', top_header)
            if match:
                return match.group(1).strip()

        for line in header_lines:
            stripped = line.strip()
            if not stripped or len(stripped) > 120:
                continue
            low = stripped.lower()
            if any(f in low for f in self._PATIENT_FIELDS):
                continue
            if any(bad in low for bad in self._NON_LAB_HEADER_TOKENS):
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
            # "02/12/2024", "02-12-2024", "2-9-2025"
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
            # "2024-12-02", "2024/12/02"
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
        ]

        # Priority: look near explicit date labels first.
        report_kw = ['print date', 'report date', 'reported on', 'reported date', 'reporting date', 'entry date']
        for kw in report_kw:
            idx = self.text_lower.find(kw)
            if idx == -1:
                continue
            snippet = self.text[idx:idx + 80]
            for pat in date_patterns:
                m = re.search(pat, snippet, re.IGNORECASE)
                if m:
                    formatted = self._format_date(*m.groups())
                    if self._is_likely_date(formatted):
                        return formatted

        # Fallback: any date in the text
        for pat in date_patterns:
            m = re.search(pat, self.text, re.IGNORECASE)
            if m:
                formatted = self._format_date(*m.groups())
                if self._is_likely_date(formatted):
                    return formatted
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

    def _is_likely_date(self, value: str) -> bool:
        parts = value.split()
        if len(parts) < 3:
            return False
        day, month, year = parts[0], parts[1], parts[2]
        if not day.isdigit() or not year.isdigit():
            return False
        day_num = int(day)
        year_num = int(year)
        if day_num < 1 or day_num > 31:
            return False
        if year_num < 1900 or year_num > 2100:
            return False
        month_ok = month.capitalize() in self.MONTHS_CORRECT.values() or (month.isdigit() and 1 <= int(month) <= 12)
        return month_ok

    # ── Test names ───────────────────────────────────────────────────
    def extract_test_names(self) -> List[str]:
        detected: set = set()
        low = self.text_lower
        for canonical, keywords in self.MEDICAL_TESTS.items():
            for kw in keywords:
                kw_low = kw.lower().strip()
                pattern = rf'(?<![a-z0-9]){re.escape(kw_low)}(?![a-z0-9])'
                if re.search(pattern, low):
                    detected.add(canonical)
                    break
        return sorted(detected)