import pandas as pd

from src.classifier import normalize_calls_dataframe


def make_row(transcript: str, duration: str = "0:30", end_reason: str = "bot_hangup") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "телефон": "79990000000",
                "дата и время": "2026-05-29 09:00:00",
                "длительность мин:сек": duration,
                "статус": "ended",
                "запись аудио": "",
                "причина завершения": end_reason,
                "история диалога юзер-бот": transcript,
            }
        ]
    )


def test_empty_dialogue_is_no_dialogue():
    df = normalize_calls_dataframe(make_row(""))
    assert df.loc[0, "dialogue_category"] == "no_dialogue"


def test_bad_connection_keyword_is_detected():
    df = normalize_calls_dataframe(make_row("user: не слышу вас"))
    assert df.loc[0, "dialogue_category"] == "bad_connection"


def test_no_interest_keyword_is_detected():
    df = normalize_calls_dataframe(make_row("user: не интересно"))
    assert df.loc[0, "dialogue_category"] == "no_interest"


def test_callback_keyword_is_detected():
    df = normalize_calls_dataframe(make_row("user: перезвоните завтра"))
    assert df.loc[0, "dialogue_category"] == "callback_requested"


def test_meeting_offer_keyword_is_detected():
    df = normalize_calls_dataframe(make_row("user: давайте созвонимся"))
    assert bool(df.loc[0, "has_meeting_offer_signal"]) is True


def test_meeting_confirmation_keyword_is_detected():
    df = normalize_calls_dataframe(make_row("user: договорились, отправлю приглашение"))
    assert df.loc[0, "dialogue_category"] == "meeting_confirmed"


def test_long_call_is_anomaly():
    df = normalize_calls_dataframe(make_row("bot: привет", duration="10:00"))
    assert df.loc[0, "dialogue_category"] == "long_anomalous_call"


def test_allo_is_not_meaningful_contact():
    df = normalize_calls_dataframe(make_row("user: Алло"))
    assert bool(df.loc[0, "has_meaningful_contact"]) is False