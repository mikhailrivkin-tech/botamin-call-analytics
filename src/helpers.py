from __future__ import annotations

import re
from typing import Iterable

from .constants import TECHNICAL_SHORT_RESPONSES


WHITESPACE_RE = re.compile(r"\s+")


def collapse_whitespace(text: object) -> str:
    if text is None:
        return ""
    value = str(text)
    value = value.replace("\u00a0", " ")
    return WHITESPACE_RE.sub(" ", value).strip()


def normalize_for_match(text: object) -> str:
    return collapse_whitespace(text).casefold()


def contains_any(text: object, keywords: Iterable[str]) -> bool:
    haystack = normalize_for_match(text)
    if not haystack:
        return False
    return any(normalize_for_match(keyword) in haystack for keyword in keywords)


def is_short_technical_response(text: object) -> bool:
    value = normalize_for_match(text)
    if not value:
        return False
    if value == "алло":
        return True
    return value in {normalize_for_match(item) for item in TECHNICAL_SHORT_RESPONSES}


def safe_strip(text: object) -> str:
    return collapse_whitespace(text)