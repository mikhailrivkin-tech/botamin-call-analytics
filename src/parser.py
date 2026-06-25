from __future__ import annotations

import datetime as dt
import re
from typing import Iterable

from .helpers import collapse_whitespace


TURN_PATTERN = re.compile(r"(?i)\b(user|bot)\s*:\s*")


def parse_duration_to_seconds(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)

    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)

    parts = text.split(":")
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return None

    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    if len(numbers) == 3:
        hours, minutes, seconds = numbers
        return hours * 3600 + minutes * 60 + seconds
    if len(numbers) == 1:
        return numbers[0]
    return None


def parse_datetime_safe(value: object) -> dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value

    text = str(value).strip()
    if not text:
        return None

    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]
    for fmt in candidates:
        try:
            return dt.datetime.strptime(text, fmt)
        except ValueError:
            continue

    normalized = text.replace("T", " ")
    try:
        date_part, time_part = normalized.split(" ", 1)
        year, month, day = (int(part) for part in date_part.split("-"))
        time_bits = [int(part) for part in time_part.split(":")]
        while len(time_bits) < 3:
            time_bits.append(0)
        hour, minute, second = time_bits[:3]
        return dt.datetime(year, month, day, hour, minute, second)
    except Exception:
        return None


def split_dialogue_transcript(text: object) -> tuple[list[str], list[str]]:
    if text is None:
        return [], []
    raw = str(text)
    if not raw.strip():
        return [], []

    matches = list(TURN_PATTERN.finditer(raw))
    if not matches:
        return [], []

    user_turns: list[str] = []
    bot_turns: list[str] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        utterance = collapse_whitespace(raw[start:end])
        if not utterance:
            continue
        if match.group(1).lower() == "user":
            user_turns.append(utterance)
        else:
            bot_turns.append(utterance)
    return user_turns, bot_turns


def join_turns(turns: Iterable[str]) -> str:
    return collapse_whitespace(" ".join(part for part in turns if part and part.strip()))