
import re


def redact_with_count(text: str) -> tuple[str, int]:
    """Redact supported structured identifiers and return the match count."""
    patterns = (
        (
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            "[EMAIL REDACTED]",
            0,
        ),
        (
            r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)",
            "[PHONE REDACTED]",
            0,
        ),
        (
            r"(?<![A-Z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Z0-9])",
            "[PAN REDACTED]",
            re.IGNORECASE,
        ),
        (
            r"(?<!\d)(?:\d{4}[\s-]?){2}\d{4}(?!\d)",
            "[ID NUMBER REDACTED]",
            0,
        ),
    )
    redacted = text
    count = 0
    for pattern, replacement, flags in patterns:
        redacted, matches = re.subn(pattern, replacement, redacted, flags=flags)
        count += matches
    return redacted, count


def redact_personal_information(text: str) -> str:
    """Redact common structured identifiers before external processing."""
    return redact_with_count(text)[0]
