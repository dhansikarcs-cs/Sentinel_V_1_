import re
from fastapi import HTTPException, status, UploadFile


MAX_JOURNAL_LENGTH = 50000
MAX_NOTE_LENGTH = 20000
MAX_FIELD_LENGTH = 5000
MAX_FILE_SIZE_MB = 10
ALLOWED_FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".jpg", ".jpeg", ".png"}

SENSITIVE_KEYWORD_RE = re.compile(
    r"(ssn|social security|credit card|password|secret|api.?key|token)",
    re.IGNORECASE,
)

SQL_INJECTION_RE = re.compile(
    r"(\bunion\s+select\b|\binsert\s+into\b|\bdelete\s+from\b|\bdrop\s+(table|database)\b"
    r"|\balter\s+table\b|\bexec(ute)?\s+|\btruncate\s+|\bdeclare\s+@"
    r"|\bxp_cmdshell\b|\bsp_executesql\b|\bbenchmark\s*\(|\bsleep\s*\()"
    r"|(--[\s])|(\bor\b\s+\d+\s*=\s*\d+)|(\band\b\s+\d+\s*=\s*\d+)",
    re.IGNORECASE,
)

XSS_RE = re.compile(
    r"(<script[^>]*>|</script>|javascript:|on\w+\s*=|<iframe|<object|<embed|<form)",
    re.IGNORECASE,
)


def sanitize_text(text: str, max_length: int = MAX_FIELD_LENGTH) -> str:
    if not text:
        return text
    text = text.strip()
    if len(text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Text exceeds maximum length of {max_length} characters",
        )
    return text


def validate_no_injection(text: str) -> str:
    if not text:
        return text
    if SQL_INJECTION_RE.search(text):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input contains potentially harmful content",
        )
    return text


def validate_no_xss(text: str) -> str:
    if not text:
        return text
    if XSS_RE.search(text):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input contains disallowed HTML content",
        )
    return text


def validate_journal_content(text: str) -> str:
    text = sanitize_text(text, MAX_JOURNAL_LENGTH)
    text = validate_no_injection(text)
    text = validate_no_xss(text)
    return text


def validate_note_content(text: str) -> str:
    text = sanitize_text(text, MAX_NOTE_LENGTH)
    text = validate_no_injection(text)
    text = validate_no_xss(text)
    return text


def validate_free_text(text: str, field_name: str = "field") -> str:
    if not text:
        return text
    text = sanitize_text(text, MAX_FIELD_LENGTH)
    text = validate_no_injection(text)
    text = validate_no_xss(text)
    return text


def validate_sensor_value(value: float, min_val: float, max_val: float, field_name: str) -> float:
    if value < min_val or value > max_val:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be between {min_val} and {max_val}",
        )
    return value


def validate_sensor_data(bpm: int = 0, stress: int = 0, sleep_hours: float = 0, spo2: int = 0, hrv: int = 0):
    if bpm:
        validate_sensor_value(bpm, 30, 250, "Heart rate (bpm)")
    if stress:
        validate_sensor_value(stress, 0, 100, "Stress level")
    if sleep_hours:
        validate_sensor_value(sleep_hours, 0, 24, "Sleep hours")
    if spo2:
        validate_sensor_value(spo2, 50, 100, "SpO2")
    if hrv:
        validate_sensor_value(hrv, 0, 300, "HRV")


async def validate_file_upload(file: UploadFile, max_size_mb: int = MAX_FILE_SIZE_MB):
    ext = ""
    if file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_FILE_EXTENSIONS))}",
        )
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({size_mb:.1f}MB) exceeds maximum of {max_size_mb}MB",
        )
    await file.seek(0)
    return content


def validate_username(username: str) -> str:
    if not username or len(username) < 3 or len(username) > 64:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username must be 3-64 characters",
        )
    if not re.match(r"^[a-zA-Z0-9_\-]+$", username):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username can only contain letters, numbers, hyphens, and underscores",
        )
    validate_no_injection(username)
    return username


def validate_email(email: str) -> str:
    if not email:
        return email
    if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email format",
        )
    return email


def validate_phone(phone: str) -> str:
    if not phone:
        return phone
    cleaned = re.sub(r"[\s\-\(\)\+]", "", phone)
    if not re.match(r"^\d{7,15}$", cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid phone number format",
        )
    return phone
