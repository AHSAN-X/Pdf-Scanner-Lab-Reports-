"""LLM-based refinement for parsed lab-report fields."""

from __future__ import annotations

import json
import logging
import os
from difflib import SequenceMatcher
from pathlib import Path
import re
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv


_PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load runtime env first, then fallback defaults if needed.
for _env_file in (".env", ".env.local", ".env.example"):
    _env_path = _PROJECT_ROOT / _env_file
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=False)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a medical data extraction assistant.\n"
    "You will receive OCR text and parsed JSON.\n"
    "Your task is to refine the JSON.\n\n"
    "Rules:\n"
    "- Only use information present in the OCR text\n"
    "- Fix OCR spelling mistakes (e.g. 'Cline' -> 'Clinic', 'yul' -> 'Jul')\n"
    "- Normalize formats (dates, names)\n"
    "- Do NOT invent or guess missing values\n"
    "- If uncertain, keep original value\n"
    "- Output ONLY valid JSON\n"
    "- Keep same schema:\n"
    "  patient_name, patient_age, patient_gender, doctor_name, lab_name, report_date, test_names"
)

TARGET_FIELDS = (
    "patient_name",
    "patient_age",
    "patient_gender",
    "doctor_name",
    "lab_name",
    "report_date",
    "test_names",
)
IGNORED_TOKENS = {"dr", "doctor", "mr", "mrs", "ms", "miss"}
OCR_TOKEN_FIXES = {
    "cline": "clinic",
    "cinic": "clinic",
    "clinc": "clinic",
    "yul": "jul",
    "jui": "jul",
    "iul": "jul",
    "agt": "aug",
    "aog": "aug",
    "auq": "aug",
    "oec": "dec",
    "dece": "dec",
    "nev": "nov",
    "noy": "nov",
    "oot": "oct",
    "oet": "oct",
    "sef": "sep",
    "seo": "sep",
}
TOKEN_ALIASES = {
    "laboratory": "lab",
    "laboratories": "lab",
    "clinic": "clinic",
    "clinics": "clinic",
    "centre": "center",
    "centres": "center",
}
MONTH_TO_NUMBER = {
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
}


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _build_client() -> tuple[str, str, float, Dict[str, str]] | None:
    api_key = _get_env("LLM_API_KEY")
    api_base_url = _get_env("LLM_API_BASE_URL", "https://openrouter.ai/api/v1")
    model = _get_env("LLM_MODEL", "openai/gpt-4o-mini")
    timeout = float(_get_env("LLM_TIMEOUT", "30"))
    openrouter_site_url = _get_env("OPENROUTER_SITE_URL")
    openrouter_app_name = _get_env("OPENROUTER_APP_NAME")

    if not api_key:
        logger.info("LLM_API_KEY is not configured; skipping refinement.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Optional OpenRouter headers for attribution/routing.
    if openrouter_site_url:
        headers["HTTP-Referer"] = openrouter_site_url
    if openrouter_app_name:
        headers["X-Title"] = openrouter_app_name

    return api_base_url.rstrip("/"), model, timeout, headers


def _normalize_text(value: str) -> str:
    normalized = value.lower()
    for source, target in OCR_TOKEN_FIXES.items():
        normalized = re.sub(rf"\b{re.escape(source)}\b", target, normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _canonical_tokens(value: str) -> List[str]:
    tokens = []
    for token in _normalize_text(value).split():
        if token in IGNORED_TOKENS or len(token) < 2:
            continue
        tokens.append(TOKEN_ALIASES.get(token, token))
    return tokens


def _is_string_supported(value: str, extracted_text: str) -> bool:
    if not value or not extracted_text:
        return False

    normalized_value = _normalize_text(value)
    normalized_text = _normalize_text(extracted_text)
    if normalized_value and normalized_value in normalized_text:
        return True

    value_tokens = _canonical_tokens(value)
    if not value_tokens:
        return False

    text_tokens = list(set(_canonical_tokens(extracted_text)))
    return all(_token_supported(token, text_tokens) for token in value_tokens)


def _token_supported(token: str, text_tokens: List[str]) -> bool:
    if token in text_tokens:
        return True

    # Allow minor OCR truncations/typos while staying conservative.
    if len(token) < 4:
        return False

    for text_token in text_tokens:
        if abs(len(token) - len(text_token)) > 1:
            continue

        if token.startswith(text_token) or text_token.startswith(token):
            return True

        if SequenceMatcher(None, token, text_token).ratio() >= 0.82:
            return True

    return False


def _month_to_number(month: str) -> str | None:
    month_key = _normalize_text(month)[:3]
    return MONTH_TO_NUMBER.get(month_key)


def _canonicalize_date(value: str) -> str | None:
    value = value.strip()

    match = re.search(r"^(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(\d{2,4})$", value)
    if match:
        day, month, year = match.groups()
        month_number = _month_to_number(month)
        if month_number:
            year_number = int(year)
            if year_number < 100:
                year_number += 2000 if year_number < 50 else 1900
            return f"{year_number:04d}-{month_number}-{int(day):02d}"

    match = re.search(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", value)
    if match:
        day, month, year = match.groups()
        year_number = int(year)
        if year_number < 100:
            year_number += 2000 if year_number < 50 else 1900
        return f"{year_number:04d}-{int(month):02d}-{int(day):02d}"

    match = re.search(r"^(\d{2,4})[/-](\d{1,2})[/-](\d{1,2})$", value)
    if match:
        year, month, day = match.groups()
        year_number = int(year)
        if year_number < 100:
            year_number += 2000 if year_number < 50 else 1900
        return f"{year_number:04d}-{int(month):02d}-{int(day):02d}"

    return None


def _extract_date_candidates(text: str) -> List[str]:
    candidates = []
    patterns = (
        r"\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{2,4}",
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        r"\d{2,4}[/-]\d{1,2}[/-]\d{1,2}",
    )
    for pattern in patterns:
        candidates.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return candidates


def _is_date_supported(value: str, extracted_text: str) -> bool:
    canonical_value = _canonicalize_date(value)
    if not canonical_value:
        return False

    for candidate in _extract_date_candidates(extracted_text):
        if _canonicalize_date(candidate) == canonical_value:
            return True
    return False


def _is_age_supported(value: str, extracted_text: str) -> bool:
    value = value.strip()
    if not re.match(r"^\d{1,3}$", value):
        return False

    age_num = int(value)
    if age_num <= 0 or age_num > 120:
        return False

    # Require an age-labeled context, not just any numeric hit in the report.
    pattern = rf"(?i)\bage\s*[:\-]?\s*{re.escape(value)}\s*(?:years?|yrs?|y)?"
    match = re.search(pattern, extracted_text)
    if not match:
        return False

    # Reject common OCR merge artifact: "Age 2. Years lab # ..."
    context_after = extracted_text[match.end(): match.end() + 40]
    if age_num <= 5 and re.search(r"(?i)years?\s*lab\s*#?", context_after):
        return False

    return True


def _normalize_gender(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"m", "male"}:
        return "Male"
    if normalized in {"f", "female"}:
        return "Female"
    return ""


def _is_gender_supported(value: str, extracted_text: str) -> bool:
    normalized = _normalize_gender(value)
    if not normalized:
        return False
    return re.search(r"\b(?:male|female|m|f)\b", extracted_text, re.IGNORECASE) is not None


def _is_doctor_name_supported(value: str, extracted_text: str) -> bool:
    cleaned = value.strip()
    words = [w for w in re.split(r"\s+", cleaned) if w]
    if len(words) < 2 or len(words) > 4:
        return False

    if not _is_string_supported(cleaned, extracted_text):
        return False

    # Prefer values tied to doctor/referral context, not footer signatures.
    low_text = extracted_text.lower()
    for token in _canonical_tokens(cleaned):
        if len(token) < 3:
            continue
        idx = low_text.find(token.lower())
        if idx == -1:
            continue
        left = max(0, idx - 60)
        right = min(len(low_text), idx + 60)
        window = low_text[left:right]
        if re.search(r"\b(?:doctor|dr\.?|requesting|ref\.?\s*by|referred\s*by)\b", window):
            return True
    return False


def _coerce_test_names(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[,;\n]", value)
        return [part.strip() for part in parts if part.strip()]
    return []


def _parse_json_payload(content: str) -> Dict[str, Any]:
    stripped = content.strip()

    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1).strip()

    if not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            stripped = stripped[start : end + 1]

    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON must be an object.")
    return parsed


def _validate_refined_data(extracted_text: str, parsed_data: Dict[str, Any], refined_data: Dict[str, Any]) -> Dict[str, Any]:
    final_data = dict(parsed_data)

    for field in TARGET_FIELDS:
        candidate = refined_data.get(field)

        if field == "test_names":
            candidate_tests = _coerce_test_names(candidate)
            validated_tests = [test for test in candidate_tests if _is_string_supported(test, extracted_text)]
            if validated_tests:
                final_data[field] = validated_tests
            continue

        if not isinstance(candidate, str):
            candidate = "" if candidate is None else str(candidate)

        candidate = candidate.strip()
        if not candidate:
            continue

        if field == "patient_name":
            parsed_name = str(parsed_data.get("patient_name", "")).strip()
            if parsed_name:
                parsed_tokens = parsed_name.split()
                candidate_tokens = candidate.split()
                # Do not replace a more complete parsed name with a shorter candidate.
                if len(parsed_tokens) >= 2 and len(candidate_tokens) < len(parsed_tokens):
                    continue

        if field == "patient_age":
            if _is_age_supported(candidate, extracted_text):
                final_data[field] = candidate
            continue

        if field == "patient_gender":
            normalized_gender = _normalize_gender(candidate)
            if normalized_gender and _is_gender_supported(normalized_gender, extracted_text):
                final_data[field] = normalized_gender
            continue

        if field == "report_date":
            if _is_date_supported(candidate, extracted_text):
                final_data[field] = candidate
            continue

        if field == "doctor_name":
            if _is_doctor_name_supported(candidate, extracted_text):
                final_data[field] = candidate
            continue

        if _is_string_supported(candidate, extracted_text):
            final_data[field] = candidate

    return final_data


async def refine_with_llm(extracted_text: str, parsed_data: dict) -> dict:
    """Refine parsed lab-report fields with a single LLM call.

    The function is conservative by design: if the LLM is unavailable,
    returns invalid JSON, or produces unsupported values, the original
    parsed_data is returned unchanged for those fields.
    """

    client_config = _build_client()
    if client_config is None:
        return dict(parsed_data)

    api_base_url, model, timeout, headers = client_config
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "ocr_text": extracted_text,
                        "parsed_json": parsed_data,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            response = await client.post(f"{api_base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        refined_payload = _parse_json_payload(content)
        return _validate_refined_data(extracted_text, parsed_data, refined_payload)

    except Exception as exc:
        logger.warning("LLM refinement failed; using parser output. Error: %s", exc)
        return dict(parsed_data)
