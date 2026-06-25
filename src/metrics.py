from __future__ import annotations

import pandas as pd

from .constants import (
    DIALOGUE_CATEGORIES,
    FUNNEL_STAGE_LABELS,
    TECHNICAL_END_REASONS,
)


LOSS_REASON_GROUPS = [
    {
        "code": "contact_not_happened",
        "label": "Контакт не состоялся",
        "description": "Клиент не ответил, связь сорвалась или разговор оборвался до содержательного контакта.",
        "members": {"no_dialogue", "early_client_hangup", "bad_connection", "long_anomalous_call"},
        "color": "#c1121f",
    },
    {
        "code": "no_interest",
        "label": "Нет интереса",
        "description": "Собеседник прямо отказался или не увидел ценность предложения.",
        "members": {"no_interest"},
        "color": "#d62828",
    },
    {
        "code": "no_next_step",
        "label": "Интерес есть, но шаг не зафиксирован",
        "description": "Интерес или просьба перезвонить не дошли до конкретной договорённости.",
        "members": {"callback_requested", "interested_not_converted"},
        "color": "#6c757d",
    },
    {
        "code": "not_lpr",
        "label": "Не ЛПР / нецелевой контакт",
        "description": "Собеседник был заинтересован, но не принимал решение.",
        "members": {"not_decision_maker"},
        "color": "#8d99ae",
    },
    {
        "code": "scenario_or_unknown",
        "label": "Сценарий / не классифицировано",
        "description": "Звонки, которые текущие правила не смогли отнести точнее.",
        "members": {"bot_scenario_issue", "other"},
        "color": "#adb5bd",
    },
]


def calculate_kpis(df: pd.DataFrame) -> dict[str, dict[str, float | str]]:
    total_calls = len(df)
    unique_contacts = df["phone"].nunique() if total_calls else 0

    def share(mask: pd.Series) -> float:
        if total_calls == 0:
            return 0.0
        return float(mask.sum()) / float(total_calls)

    values = {
        "total_calls": {"label": "Звонки", "value": f"{total_calls:,}".replace(",", " "), "caption": "Все попытки дозвона в выбранной выборке."},
        "unique_contacts": {"label": "Контакты", "value": f"{unique_contacts:,}".replace(",", " "), "caption": "Сколько разных телефонов попало в выборку."},
        "response_share": {"label": "Ответил клиент", "value": f"{share(df['has_user_speech']):.1%}", "caption": "Доля звонков, где клиент вообще ответил."},
        "short_5s_share": {"label": "До 5 сек", "value": f"{share(df['is_short_call_5s']):.1%}", "caption": "Быстрые обрывы в первые секунды звонка."},
        "meaningful_contact_share": {"label": "Предметный разговор", "value": f"{share(df['has_meaningful_contact']):.1%}", "caption": "Ответ клиента, который перешёл в предметный разговор."},
        "meeting_confirmed_share": {"label": "Подтверждённая встреча", "value": f"{share(df['has_meeting_confirmation_signal']):.1%}", "caption": "Сколько звонков дошло до подтверждения встречи."},
        "bad_connection_share": {"label": "Проблемы связи", "value": f"{share(df['has_bad_connection_signal']):.1%}", "caption": "Звонки, где в тексте есть сигналы плохой связи."},
        "early_hangup_share": {"label": "Ранний обрыв", "value": f"{share((df['is_short_call_10s']) & df['end_reason'].eq('client_hangup')):.1%}", "caption": "Клиент положил трубку в первые 10 секунд."},
        "interest_without_next_share": {"label": "Интерес без следующего шага", "value": f"{share(df['has_interest_signal'] & ~df['has_meeting_confirmation_signal']):.1%}", "caption": "Есть интерес, но нет подтверждения следующего действия."},
        "technical_end_share": {"label": "Технические завершения", "value": f"{share(df['end_reason'].isin(TECHNICAL_END_REASONS)):.1%}", "caption": "Звонки, завершившиеся по техническим или телеком-причинам."},
        "no_user_speech_share": {"label": "Без ответа", "value": f"{share(~df['has_user_speech']):.1%}", "caption": "Звонки, где клиент не ответил или ответа не распознали."},
        "bad_connection_phrase_share": {"label": "Сигналы связи", "value": f"{share(df['has_bad_connection_signal']):.1%}", "caption": "Доля звонков с явными словами о проблемах связи."},
        "long_calls_share": {"label": "Длинные", "value": f"{share(df['is_long_anomaly']):.1%}", "caption": "Звонки длительностью 600 секунд и дольше."},
    }
    return values


def calculate_funnel_metrics(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    reached_meaningful_contact = df["has_user_speech"] & df["has_meaningful_contact"]
    reached_offer = reached_meaningful_contact & df["has_offer_signal"]
    reached_meeting_offer = reached_offer & df["has_meeting_offer_signal"]
    reached_meeting_confirmed = reached_meeting_offer & df["has_meeting_confirmation_signal"]
    stages = [
        ("no_answer", "Попытки звонка", total),
        ("answered", "Клиент ответил", int(df["has_user_speech"].sum())),
        ("meaningful_contact", "Предметный разговор", int(reached_meaningful_contact.sum())),
        ("offer_revealed", "Оффер раскрыт", int(reached_offer.sum())),
        ("meeting_offered", "Предложена встреча", int(reached_meeting_offer.sum())),
        ("meeting_confirmed", "Встреча подтверждена", int(reached_meeting_confirmed.sum())),
    ]
    rows = []
    previous_count = None
    for code, label, count in stages:
        share_total = 0.0 if total == 0 else count / total
        share_previous = 1.0 if previous_count in (None, 0) else count / previous_count
        rows.append(
            {
                "stage_code": code,
                "stage": label,
                "count": count,
                "share_previous": share_previous,
                "share_total": share_total,
            }
        )
        previous_count = count
    return pd.DataFrame(rows)


def find_main_bottleneck(funnel_df: pd.DataFrame) -> dict[str, float | str]:
    if funnel_df.empty:
        return {
            "from_code": "no_answer",
            "to_code": "no_answer",
            "from_label": "Попытки звонка",
            "to_label": "Попытки звонка",
            "lost_count": 0,
            "lost_share": 0.0,
        }

    max_drop = -1
    best_index = 1 if len(funnel_df) > 1 else 0
    for idx in range(1, len(funnel_df)):
        if idx == 1:
            continue
        previous = int(funnel_df.iloc[idx - 1]["count"])
        current = int(funnel_df.iloc[idx]["count"])
        drop = max(previous - current, 0)
        if drop > max_drop:
            max_drop = drop
            best_index = idx

    if max_drop < 0 and len(funnel_df) > 1:
        previous = int(funnel_df.iloc[0]["count"])
        current = int(funnel_df.iloc[1]["count"])
        max_drop = max(previous - current, 0)
        best_index = 1

    previous_count = int(funnel_df.iloc[best_index - 1]["count"]) if best_index > 0 else int(funnel_df.iloc[best_index]["count"])
    current_count = int(funnel_df.iloc[best_index]["count"])
    lost_count = max(previous_count - current_count, 0)
    lost_share = 0.0 if previous_count == 0 else lost_count / previous_count
    return {
        "from_code": funnel_df.iloc[best_index - 1]["stage_code"] if best_index > 0 else funnel_df.iloc[best_index]["stage_code"],
        "to_code": funnel_df.iloc[best_index]["stage_code"],
        "from_label": funnel_df.iloc[best_index - 1]["stage"] if best_index > 0 else funnel_df.iloc[best_index]["stage"],
        "to_label": funnel_df.iloc[best_index]["stage"],
        "lost_count": lost_count,
        "lost_share": lost_share,
    }


def calculate_category_counts(df: pd.DataFrame) -> pd.DataFrame:
    counts = df["dialogue_category"].value_counts().rename_axis("category").reset_index(name="count")
    counts["label"] = counts["category"].map(DIALOGUE_CATEGORIES).fillna(counts["category"])
    return counts


def calculate_loss_reason_groups(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total = len(df)
    for group in LOSS_REASON_GROUPS:
        count = int(df["dialogue_category"].isin(group["members"]).sum())
        rows.append(
            {
                "group_code": group["code"],
                "label": group["label"],
                "description": group["description"],
                "count": count,
                "share": 0.0 if total == 0 else count / total,
                "color": group["color"],
            }
        )
    return pd.DataFrame(rows)


def quality_first_contact_message(df: pd.DataFrame) -> str:
    if df.empty:
        return "Нет данных для оценки качества первого контакта."

    short_calls_5s_share = float(df["is_short_call_5s"].mean())
    no_user_speech_share = float((~df["has_user_speech"]).mean())
    if short_calls_5s_share > 0.30 and no_user_speech_share > 0.50:
        return (
            "Критичный сигнал:\n"
            "Основная потеря происходит до раскрытия оффера. Вероятная зона проверки — длина, темп и структура первой реплики бота."
        )
    return (
        "Основная потеря не сосредоточена в первых секундах звонка. "
        "Требуется анализ этапов после раскрытия оффера."
    )