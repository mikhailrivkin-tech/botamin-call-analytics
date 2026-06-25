import pandas as pd

from src.classifier import normalize_calls_dataframe
from src.metrics import calculate_funnel_metrics, calculate_loss_reason_groups, find_main_bottleneck


def test_funnel_and_bottleneck_work_on_simple_sample():
    raw = pd.DataFrame(
        [
            {
                "телефон": "79990000001",
                "дата и время": "2026-05-29 09:00:00",
                "длительность мин:сек": "0:03",
                "статус": "ended",
                "запись аудио": "",
                "причина завершения": "bot_hangup",
                "история диалога юзер-бот": "",
            },
            {
                "телефон": "79990000002",
                "дата и время": "2026-05-29 09:01:00",
                "длительность мин:сек": "0:20",
                "статус": "ended",
                "запись аудио": "",
                "причина завершения": "client_hangup",
                "история диалога юзер-бот": "user: давайте созвонимся",
            },
        ]
    )
    df = normalize_calls_dataframe(raw)
    funnel = calculate_funnel_metrics(df)
    bottleneck = find_main_bottleneck(funnel)
    assert not funnel.empty
    assert bottleneck["lost_count"] >= 0


def test_loss_reason_groups_are_aggregated():
    raw = pd.DataFrame(
        [
            {
                "телефон": "79990000001",
                "дата и время": "2026-05-29 09:00:00",
                "длительность мин:сек": "0:03",
                "статус": "ended",
                "запись аудио": "",
                "причина завершения": "client_hangup",
                "история диалога юзер-бот": "",
            },
            {
                "телефон": "79990000002",
                "дата и время": "2026-05-29 09:01:00",
                "длительность мин:сек": "0:20",
                "статус": "ended",
                "запись аудио": "",
                "причина завершения": "bot_hangup",
                "история диалога юзер-бот": "user: не интересно",
            },
            {
                "телефон": "79990000003",
                "дата и время": "2026-05-29 09:02:00",
                "длительность мин:сек": "0:20",
                "статус": "ended",
                "запись аудио": "",
                "причина завершения": "bot_hangup",
                "история диалога юзер-бот": "user: давайте созвонимся",
            },
        ]
    )
    df = normalize_calls_dataframe(raw)
    grouped = calculate_loss_reason_groups(df)
    assert int(grouped["count"].sum()) == len(df)
    assert "Контакт не состоялся" in grouped["label"].tolist()