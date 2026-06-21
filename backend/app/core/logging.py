import logging
import re
from typing import Any

PHI_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN-like
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),  # email
    re.compile(r"\b\d{10,}\b"),  # long numeric identifiers
]


class PhiRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)
        if record.args:
            record.args = tuple(self.redact(arg) if isinstance(arg, str) else arg for arg in record.args)
        return True

    @staticmethod
    def redact(value: str) -> str:
        redacted = value
        for pattern in PHI_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    root = logging.getLogger()
    for handler in root.handlers:
        handler.addFilter(PhiRedactionFilter())


def safe_log_context(**kwargs: Any) -> dict[str, Any]:
    """Return a logging-safe context dict with PHI-like values removed."""
    safe: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key in {"email", "full_name", "password", "token", "transcript", "note"}:
            safe[key] = "[REDACTED]"
        else:
            safe[key] = value
    return safe
