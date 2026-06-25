from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .constants import (
    BAD_CONNECTION_KEYWORDS,
    CALLBACK_KEYWORDS,
    DECISION_MAKER_KEYWORDS,
    DIALOGUE_CATEGORIES,
    EXPECTED_COLUMNS,
    INTEREST_KEYWORDS,
    MEETING_CONFIRMATION_KEYWORDS,
    MEETING_OFFER_KEYWORDS,
    NO_INTEREST_KEYWORDS,
    OFFER_KEYWORDS,
    TECHNICAL_SHORT_RESPONSES,
)
from .helpers import collapse_whitespace, contains_any, is_short_technical_response, normalize_for_match
from .parser import join_turns, parse_datetime_safe, parse_duration_to_seconds, split_dialogue_transcript


def _build_keyword_pattern(keywords: list[str]) -> str:
    parts: list[str] = []
    for keyword in keywords:
        escaped = re.escape(keyword.casefold())
        escaped = escaped.replace(r"\ ", r"\s+")
        parts.append(escaped)
    return "|".join(parts)


def _normalize_text_series(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.replace("\u00a0", " ", regex=False)
        .str.casefold()
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def _extract_dialogue_parts(transcript: object) -> pd.Series:
    user_turns, bot_turns = split_dialogue_transcript(transcript)
    return pd.Series(
        {
            "user_transcript": join_turns(user_turns),
            "bot_transcript": join_turns(bot_turns),
            "first_user_phrase": user_turns[0] if user_turns else "",
            "first_bot_phrase": bot_turns[0] if bot_turns else "",
        }
    )


def _assign_first_call_flags(df: pd.DataFrame) -> pd.DataFrame:
    ordered = df.reset_index(names="_source_index").copy()
    ordered = ordered.sort_values(["phone", "datetime", "_source_index"], kind="mergesort")
    ordered["phone_call_number"] = ordered.groupby("phone").cumcount() + 1
    ordered["is_first_call_for_phone"] = ordered["phone_call_number"] == 1
    ordered["is_repeat_call_for_phone"] = ~ordered["is_first_call_for_phone"]
    ordered = ordered.sort_values("_source_index", kind="mergesort").drop(columns=["_source_index"])
    return ordered


def normalize_calls_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame(
            columns=[
                "call_id",
                "phone",
                "datetime",
                "date",
                "hour",
                "duration_seconds",
                "status",
                "audio_url",
                "end_reason",
                "transcript",
                "has_transcript",
                "has_user_speech",
                "has_bot_speech",
                "first_user_phrase",
                "first_bot_phrase",
                "is_short_call_5s",
                "is_short_call_10s",
                "is_long_anomaly",
                "has_bad_connection_signal",
                "has_no_interest_signal",
                "has_callback_signal",
                "has_interest_signal",
                "has_meeting_offer_signal",
                "has_meeting_confirmation_signal",
                "has_decision_maker_signal",
                "has_offer_signal",
                "has_personalization_error",
                "has_meaningful_contact",
                "dialogue_category",
                "funnel_stage",
            ]
        )

    df = raw_df.copy()
    df.columns = [str(column).strip() for column in df.columns]
    missing = [column for column in EXPECTED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    df = df.rename(
        columns={
            "телефон": "phone",
            "дата и время": "datetime_raw",
            "длительность мин:сек": "duration_raw",
            "статус": "status",
            "запись аудио": "audio_url",
            "причина завершения": "end_reason",
            "история диалога юзер-бот": "transcript",
        }
    )

    df["call_id"] = range(1, len(df) + 1)
    df["phone"] = df["phone"].astype(str).str.strip()
    df["datetime"] = df["datetime_raw"].map(parse_datetime_safe)
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce").dt.date
    df["hour"] = pd.to_datetime(df["datetime"], errors="coerce").dt.hour
    df["duration_seconds"] = df["duration_raw"].map(parse_duration_to_seconds)
    df["status"] = df["status"].astype(str).str.strip()
    df["audio_url"] = df["audio_url"].astype(str).str.strip()
    df["end_reason"] = df["end_reason"].astype(str).str.strip()
    df["transcript"] = df["transcript"].fillna("").astype(str)

    extracted = df["transcript"].apply(_extract_dialogue_parts)
    df = pd.concat([df, extracted], axis=1)

    df["has_transcript"] = df["transcript"].str.strip().ne("")
    df["has_user_speech"] = df["user_transcript"].str.strip().ne("")
    df["has_bot_speech"] = df["bot_transcript"].str.strip().ne("")

    normalized_transcript = _normalize_text_series(df["transcript"])
    normalized_first_user = _normalize_text_series(df["first_user_phrase"])
    normalized_first_bot = _normalize_text_series(df["first_bot_phrase"])
    normalized_user = _normalize_text_series(df["user_transcript"])
    normalized_bot = _normalize_text_series(df["bot_transcript"])

    df["is_short_call_5s"] = df["duration_seconds"].fillna(-1).astype(float) <= 5
    df["is_short_call_10s"] = df["duration_seconds"].fillna(-1).astype(float) <= 10
    df["is_long_anomaly"] = df["duration_seconds"].fillna(-1).astype(float) >= 600

    bad_connection_pattern = _build_keyword_pattern(BAD_CONNECTION_KEYWORDS)
    no_interest_pattern = _build_keyword_pattern(NO_INTEREST_KEYWORDS)
    callback_pattern = _build_keyword_pattern(CALLBACK_KEYWORDS)
    interest_pattern = _build_keyword_pattern(INTEREST_KEYWORDS)
    meeting_offer_pattern = _build_keyword_pattern(MEETING_OFFER_KEYWORDS)
    meeting_confirmation_pattern = _build_keyword_pattern(MEETING_CONFIRMATION_KEYWORDS)
    decision_maker_pattern = _build_keyword_pattern(DECISION_MAKER_KEYWORDS)
    offer_pattern = _build_keyword_pattern(OFFER_KEYWORDS)

    df["has_bad_connection_signal"] = normalized_transcript.str.contains(bad_connection_pattern, regex=True, na=False)
    df["has_no_interest_signal"] = normalized_transcript.str.contains(no_interest_pattern, regex=True, na=False)
    df["has_callback_signal"] = normalized_transcript.str.contains(callback_pattern, regex=True, na=False)
    df["has_interest_signal"] = normalized_transcript.str.contains(interest_pattern, regex=True, na=False)
    df["has_meeting_offer_signal"] = normalized_transcript.str.contains(meeting_offer_pattern, regex=True, na=False)
    df["has_meeting_confirmation_signal"] = normalized_transcript.str.contains(meeting_confirmation_pattern, regex=True, na=False)
    df["has_decision_maker_signal"] = normalized_transcript.str.contains(decision_maker_pattern, regex=True, na=False)
    df["has_offer_signal"] = normalized_transcript.str.contains(offer_pattern, regex=True, na=False)
    df["has_personalization_error"] = normalized_bot.str.contains(r"\{|\}|undefined|placeholder|\bnone\b|\bnan\b", regex=True, na=False)

    df["has_meaningful_contact"] = df["has_user_speech"] & ~normalized_first_user.map(is_short_technical_response) & normalized_first_user.str.len().gt(8)

    dialogue_conditions = [
        ~df["has_transcript"],
        df["is_long_anomaly"],
        df["has_bad_connection_signal"],
        df["is_short_call_10s"] & df["end_reason"].eq("client_hangup"),
        df["has_no_interest_signal"],
        df["has_callback_signal"],
        df["has_meeting_confirmation_signal"],
        df["has_interest_signal"] & ~df["has_meeting_confirmation_signal"],
        df["has_decision_maker_signal"],
        df["has_user_speech"]
        & df["duration_seconds"].fillna(-1).astype(float).le(20)
        & ~df["has_offer_signal"]
        & ~df["has_no_interest_signal"]
        & ~df["has_bad_connection_signal"],
    ]
    dialogue_choices = [
        "no_dialogue",
        "long_anomalous_call",
        "bad_connection",
        "early_client_hangup",
        "no_interest",
        "callback_requested",
        "meeting_confirmed",
        "interested_not_converted",
        "not_decision_maker",
        "bot_scenario_issue",
    ]
    df["dialogue_category"] = np.select(dialogue_conditions, dialogue_choices, default="other")

    reached_meaningful_contact = df["has_user_speech"] & df["has_meaningful_contact"]
    reached_offer = reached_meaningful_contact & df["has_offer_signal"]
    reached_meeting_offer = reached_offer & df["has_meeting_offer_signal"]
    reached_meeting_confirmed = reached_meeting_offer & df["has_meeting_confirmation_signal"]

    funnel_conditions = [
        reached_meeting_confirmed,
        reached_meeting_offer,
        reached_offer,
        reached_meaningful_contact,
        df["has_user_speech"],
    ]
    funnel_choices = [
        "meeting_confirmed",
        "meeting_offered",
        "offer_revealed",
        "meaningful_contact",
        "answered",
    ]
    df["funnel_stage"] = np.select(funnel_conditions, funnel_choices, default="no_answer")

    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["date"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour

    df = _assign_first_call_flags(df)
    df = df[
        [
            "call_id",
            "phone",
            "datetime",
            "date",
            "hour",
            "duration_seconds",
            "status",
            "audio_url",
            "end_reason",
            "transcript",
            "user_transcript",
            "bot_transcript",
            "has_transcript",
            "has_user_speech",
            "has_bot_speech",
            "first_user_phrase",
            "first_bot_phrase",
            "is_short_call_5s",
            "is_short_call_10s",
            "is_long_anomaly",
            "has_bad_connection_signal",
            "has_no_interest_signal",
            "has_callback_signal",
            "has_interest_signal",
            "has_meeting_offer_signal",
            "has_meeting_confirmation_signal",
            "has_decision_maker_signal",
            "has_offer_signal",
            "has_personalization_error",
            "has_meaningful_contact",
            "dialogue_category",
            "funnel_stage",
        ]
    ]
    return df