from __future__ import annotations

import logging
import re

API_KEY_QUERY_PARAM_PATTERN = re.compile(r"(?i)(apiKey=)[^&\s]+")
REDACTED_VALUE = "<redacted>"


def redact_secrets(value: object) -> str:
    return API_KEY_QUERY_PARAM_PATTERN.sub(rf"\1{REDACTED_VALUE}", str(value))


def configure_logging() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
