from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

try:
    import streamlit as st
except ImportError:  # pragma: no cover - allows importing during lightweight checks
    st = None  # type: ignore[assignment]

from src.classifier import normalize_calls_dataframe
from src.constants import DIALOGUE_CATEGORIES, END_REASON_LABELS, FUNNEL_STAGE_LABELS
from src.loader import load_calls_csv
from src.metrics import (
    calculate_funnel_metrics,
    calculate_loss_reason_groups,
    calculate_kpis,
    find_main_bottleneck,
    quality_first_contact_message,
)


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "calls_week_anon.csv"


if st is not None:
    st.set_page_config(page_title="Аналитика звонков Botamin", layout="wide")
    st.markdown(
        """
        <style>
        [data-testid="stHeader"] { display: none; }
        [data-testid="stToolbar"] { display: none; }
        footer { visibility: hidden; }
        .analysis-shell {
            background: linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
            border: 1px solid #dbe4ee;
            border-radius: 22px;
            padding: 28px 28px 22px;
            margin-top: 20px;
        }
        .analysis-shell h3 {
            margin-top: 0;
        }
        .analysis-grid {
            display: grid;
            grid-template-columns: 1.15fr 0.85fr;
            gap: 16px;
            margin-top: 14px;
        }
        .analysis-card {
            background: white;
            border-radius: 16px;
            border: 1px solid #e5e7eb;
            padding: 16px 18px;
        }
        .analysis-card h4 {
            margin: 0 0 10px 0;
        }
        .analysis-card p {
            margin: 0 0 10px 0;
        }
        .analysis-card ul {
            margin: 0;
            padding-left: 18px;
        }
        .analysis-card li {
            margin-bottom: 6px;
        }
        @media (max-width: 900px) {
            .analysis-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _format_share(value: float) -> str:
    return f"{value:.1%}"


def _format_int(value: float | int) -> str:
    return f"{int(round(value)):,}".replace(",", " ")


if st is not None:

    @st.cache_data(show_spinner=False)
    def cached_load_csv(path_or_bytes: str | bytes) -> pd.DataFrame:
        return load_calls_csv(path_or_bytes)


    @st.cache_data(show_spinner=False)
    def cached_normalize_df(raw_df: pd.DataFrame) -> pd.DataFrame:
        return normalize_calls_dataframe(raw_df)


def apply_filters(
    df: pd.DataFrame,
    date_range: tuple[pd.Timestamp, pd.Timestamp] | None,
    end_reasons: list[str],
    dialogue_categories: list[str],
    only_short_calls: bool,
    only_interested_without_meeting: bool,
    only_first_calls: bool,
    only_repeat_calls: bool,
) -> pd.DataFrame:
    filtered = df.copy()
    if date_range is not None:
        start, end = date_range
        if start > end:
            start, end = end, start
        filtered = filtered[(filtered["date"] >= start.date()) & (filtered["date"] <= end.date())]
    if end_reasons:
        filtered = filtered[filtered["end_reason"].isin(end_reasons)]
    if dialogue_categories:
        filtered = filtered[filtered["dialogue_category"].isin(dialogue_categories)]
    if only_short_calls:
        filtered = filtered[filtered["is_short_call_10s"]]
    if only_interested_without_meeting:
        filtered = filtered[filtered["has_interest_signal"] & ~filtered["has_meeting_confirmation_signal"]]
    if only_first_calls and not only_repeat_calls:
        filtered = filtered[filtered["is_first_call_for_phone"]]
    elif only_repeat_calls and not only_first_calls:
        filtered = filtered[filtered["is_repeat_call_for_phone"]]
    return filtered


def render_metric_card(label: str, value: str, caption: str, delta_color: str = "off") -> None:
    st.metric(label=label, value=value, help=caption, delta=None, delta_color=delta_color)


def render_kpi_grid(kpis: dict[str, dict[str, float | str]]) -> None:
    first_row = st.columns(6)
    first_keys = [
        "total_calls",
        "unique_contacts",
        "response_share",
        "short_5s_share",
        "meaningful_contact_share",
        "meeting_confirmed_share",
    ]
    for col, key in zip(first_row, first_keys, strict=True):
        with col:
            render_metric_card(
                kpis[key]["label"],
                kpis[key]["value"],
                kpis[key]["caption"],
            )

    second_row = st.columns(4)
    second_keys = [
        "bad_connection_share",
        "early_hangup_share",
        "interest_without_next_share",
        "technical_end_share",
    ]
    for col, key in zip(second_row, second_keys, strict=True):
        with col:
            render_metric_card(
                kpis[key]["label"],
                kpis[key]["value"],
                kpis[key]["caption"],
            )


def render_funnel(funnel_df: pd.DataFrame) -> None:
    counts = funnel_df["count"].fillna(0).astype(int).tolist()
    previous = None
    hover_rows: list[list[str]] = []
    for count in counts:
        previous_share = 1.0 if previous in (None, 0) else count / previous
        hover_rows.append(
            [
                _format_int(count),
                f"{previous_share:.0%}",
            ]
        )
        previous = count
    max_count = max(counts) if counts else 0

    fig = go.Figure()
    fig.add_trace(
        go.Funnel(
            y=funnel_df["stage"],
            x=funnel_df["count"],
            customdata=hover_rows,
            textinfo="none",
            hovertemplate=(
                "Этап: %{y}<br>"
                "Значение: %{customdata[0]}<br>"
                "%{customdata[1]} от предыдущего"
                "<extra></extra>"
            ),
            marker={"color": ["#1f4e79", "#2a6f97", "#4e9ec9", "#79c2e0", "#8ecae6", "#8bd3c7"]},
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=20, r=40, t=10, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        funnelmode="stack",
        uniformtext=dict(minsize=12, mode="hide"),
        xaxis=dict(visible=False, range=[0, max_count * 1.28 if max_count else 1]),
    )
    for idx, (stage_name, count) in enumerate(zip(funnel_df["stage"].tolist(), counts, strict=True)):
        previous_share = 1.0 if idx == 0 or counts[idx - 1] == 0 else count / counts[idx - 1]
        fig.add_annotation(
            x=max_count * 1.05 if max_count else 1.0,
            y=stage_name,
            xref="x",
            yref="y",
            text=f"{_format_int(count)}<br>{previous_share:.0%} от предыдущего",
            showarrow=False,
            xanchor="left",
            align="left",
            font=dict(size=16, color="#334155"),
        )
    st.plotly_chart(fig, use_container_width=True)


def render_loss_reasons(df: pd.DataFrame) -> None:
    counts = calculate_loss_reason_groups(df)
    counts = counts[counts["group_code"] != "scenario_or_unknown"].reset_index(drop=True)
    labels = counts["label"].tolist()
    values = counts["count"].tolist()
    colors = counts["color"].tolist()
    descriptions = counts["description"].tolist()
    max_value = max(values) if values else 0
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            customdata=descriptions,
            hovertemplate="%{y}: %{x}<br>%{customdata}<extra></extra>",
        )
    )
    fig.update_layout(
        height=340,
        margin=dict(l=20, r=170, t=10, b=10),
        xaxis_title="Количество звонков",
        yaxis_title="",
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(range=[0, max_value * 1.25 if max_value else 1], showticklabels=False, ticks=""),
        uniformtext=dict(minsize=12, mode="hide"),
    )
    for label, value in zip(labels, values, strict=True):
        fig.add_annotation(
            x=max_value * 1.03 if max_value else 1.0,
            y=label,
            xref="x",
            yref="y",
            text=_format_int(value),
            showarrow=False,
            xanchor="left",
            font=dict(size=16, color="#334155"),
        )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Здесь показаны только управленческие причины потерь. "
        "Категория «Сценарий / не классифицировано» вынесена за рамки графика, потому что это не причина потери, а остаток правил разметки."
    )
    unknown = calculate_loss_reason_groups(df)
    unknown_row = unknown[unknown["group_code"] == "scenario_or_unknown"]
    if not unknown_row.empty:
        unknown_count = int(unknown_row.iloc[0]["count"])
        unknown_share = float(unknown_row.iloc[0]["share"])
        st.caption(
            f"Не классифицировано отдельно: {_format_int(unknown_count)} звонков ({_format_share(unknown_share)})."
        )


def render_analytic_conclusion(df: pd.DataFrame, kpis: dict[str, dict[str, float | str]], funnel_df: pd.DataFrame) -> None:
    if len(df) < 100:
        st.warning("Недостаточно данных для надёжной интерпретации: в выборке менее 100 звонков.")
        return

    total_calls = len(df)
    unique_contacts = df["phone"].nunique()
    no_response_count = int((~df["has_user_speech"]).sum())
    response_count = int(df["has_user_speech"].sum())
    short_calls_5_share = float(df["is_short_call_5s"].mean())
    technical_end_share = float(df["end_reason"].isin({"bot_hangup", "elevenlabs_hangup", "queue_timeout", "network_error", "bad_number"}).mean())
    bad_connection_share = float(df["has_bad_connection_signal"].mean())
    meeting_confirmed_count = int(df["has_meeting_confirmation_signal"].sum())
    long_calls_count = int(df["is_long_anomaly"].sum())

    funnel_map = funnel_df.set_index("stage")
    meaningful_stage = funnel_map.loc["Предметный разговор"] if "Предметный разговор" in funnel_map.index else None
    offer_stage = funnel_map.loc["Оффер раскрыт"] if "Оффер раскрыт" in funnel_map.index else None

    loss_groups = calculate_loss_reason_groups(df)
    actionable_losses = loss_groups[loss_groups["group_code"] != "scenario_or_unknown"].sort_values("count", ascending=False)
    top_loss = actionable_losses.iloc[0] if not actionable_losses.empty else None
    second_loss = actionable_losses.iloc[1] if len(actionable_losses) > 1 else None
    unknown_row = loss_groups[loss_groups["group_code"] == "scenario_or_unknown"]
    unknown_count = int(unknown_row.iloc[0]["count"]) if not unknown_row.empty else 0
    unknown_share = float(unknown_row.iloc[0]["share"]) if not unknown_row.empty else 0.0

    funnel_bullets = []
    for stage_name in ["Попытки звонка", "Клиент ответил", "Предметный разговор", "Оффер раскрыт", "Предложена встреча", "Встреча подтверждена"]:
        if stage_name in funnel_map.index:
            stage_row = funnel_map.loc[stage_name]
            funnel_bullets.append(
                f"{stage_name}: {_format_int(int(stage_row['count']))} "
                f"({_format_share(float(stage_row['share_total']))} от всех попыток, "
                f"{_format_share(float(stage_row['share_previous']))} от предыдущего шага)"
            )

    key_message = (
        f"В текущей выборке {_format_int(total_calls)} попыток звонка и {_format_int(unique_contacts)} уникальных контактов. "
        f"Без ответа клиента осталось {_format_int(no_response_count)} звонков ({_format_share(1 - float(df['has_user_speech'].mean()))}), "
        f"а хотя бы одну реплику клиента получили {_format_int(response_count)} звонков ({_format_share(float(df['has_user_speech'].mean()))}). "
        f"До предметного разговора доходит {_format_share(float(meaningful_stage['share_total'])) if meaningful_stage is not None else 'n/a'} от всех попыток, "
        f"а до раскрытия оффера — {_format_share(float(offer_stage['share_total'])) if offer_stage is not None else 'n/a'}."
    )

    recommendation_message = (
        "Это указывает на слабое место в первых секундах разговора, а не на финальный этап встречи. "
        "Вероятная гипотеза: первая реплика бота перегружена и не успевает подтвердить готовность человека говорить. "
        "Требует проверки сокращение стартовой реплики, пауз между репликами и качества персонализации."
    )

    evidence_items = [
        f"Доля звонков без ответа клиента: {_format_share(1 - float(df['has_user_speech'].mean()))}",
        f"Доля звонков с репликой клиента: {_format_share(float(df['has_user_speech'].mean()))}",
        f"Доля коротких звонков до 5 секунд: {_format_share(short_calls_5_share)}",
        f"Технические завершения: {_format_share(technical_end_share)}",
        f"Признаки проблем связи: {_format_share(bad_connection_share)}",
        f"Аномально длинные звонки: {_format_int(long_calls_count)}",
        f"Подтверждённые встречи: {_format_int(meeting_confirmed_count)}",
    ]

    bottleneck = find_main_bottleneck(funnel_df)
    top_losses_text = []
    if top_loss is not None:
        top_losses_text.append(
            f"{top_loss['label']} — {_format_int(int(top_loss['count']))} звонков ({_format_share(float(top_loss['share']))})"
        )
    if second_loss is not None:
        top_losses_text.append(
            f"{second_loss['label']} — {_format_int(int(second_loss['count']))} звонков ({_format_share(float(second_loss['share']))})"
        )

    limitation_text = (
        "Ограничение данных: в выгрузке нет явных событий CRM вроде «согласие», «встреча назначена» и «встреча состоялась». "
        "Поэтому этапы интерпретируются по расшифровкам и признакам в диалоге, а не по официальной карточке сделки. "
        f"Кроме того, {_format_int(unknown_count)} звонков ({_format_share(unknown_share)}) остаются в группе «Сценарий / не классифицировано»."
    )

    html = f"""
    <div class="analysis-shell">
        <h3>Аналитический вывод и рекомендации</h3>
        <p><strong>Итоговый вывод по текущей выборке с учётом фильтров.</strong> {key_message}</p>
        <div class="analysis-grid">
            <div class="analysis-card">
                <h4>Что это означает</h4>
                <p>{recommendation_message}</p>
                <ul>
                    <li>Главное узкое место: {bottleneck['from_label']} → {bottleneck['to_label']}.</li>
                    <li>Потеря на этом переходе: {_format_int(int(bottleneck['lost_count']))} звонков ({_format_share(float(bottleneck['lost_share']))}).</li>
                    <li>Топ причин потерь: {'; '.join(top_losses_text) if top_losses_text else 'нет достаточного сигнала для ранжирования.'}</li>
                </ul>
            </div>
            <div class="analysis-card">
                <h4>Ключевые факты</h4>
                <ul>
                    {''.join(f'<li>{item}</li>' for item in evidence_items)}
                </ul>
            </div>
        </div>
        <div class="analysis-card" style="margin-top: 14px;">
            <h4>Воронка в цифрах</h4>
            <ul>
                {''.join(f'<li>{item}</li>' for item in funnel_bullets)}
            </ul>
        </div>
        <div class="analysis-grid" style="margin-top: 14px;">
            <div class="analysis-card">
                <h4>Приоритетный эксперимент</h4>
                <p>Сократить первую реплику до короткой проверки доступности контакта и перенести подробный оффер на второй шаг.</p>
                <ul>
                    <li>Контроль: текущий сценарий с длинным стартом.</li>
                    <li>Тест: короткое представление + вопрос, удобно ли поговорить 20 секунд.</li>
                    <li>Основная метрика: доля содержательных контактов.</li>
                    <li>Защитные метрики: короткие звонки, негативные реакции, технические завершения.</li>
                </ul>
            </div>
            <div class="analysis-card">
                <h4>Ограничения</h4>
                <p>{limitation_text}</p>
                <p>Это не отменяет вывод, а просто делает его честным: здесь аналитика строится по правилам интерпретации текста, поэтому часть выводов требует подтверждения CRM-событиями.</p>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_quality_block(df: pd.DataFrame) -> None:
    message = quality_first_contact_message(df)
    col1, col2, col3, col4 = st.columns(4)
    metrics = [
        ("short_5s_share", "Доля звонков до 5 секунд"),
        ("no_user_speech_share", "Доля звонков без ответа клиента"),
        ("bad_connection_phrase_share", "Доля звонков с фразами о связи"),
        ("long_calls_share", "Доля длинных звонков"),
    ]
    values = calculate_kpis(df)
    for col, (key, _label) in zip([col1, col2, col3, col4], metrics, strict=True):
        with col:
            st.metric(
                label=values[key]["label"],
                value=values[key]["value"],
                help=values[key]["caption"],
            )

    st.info(message)

    fig = px.histogram(
        df,
        x="duration_seconds",
        nbins=20,
        title="Распределение длительности звонков",
    )
    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis_title="Длительность, сек",
        yaxis_title="Количество звонков",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_dialog_table(tab_df: pd.DataFrame, key: str) -> None:
    if tab_df.empty:
        st.warning("В этой вкладке нет звонков.")
        return

    table_df = tab_df[
        [
            "datetime",
            "phone",
            "duration_seconds",
            "end_reason",
            "dialogue_category",
            "funnel_stage",
            "first_user_phrase",
            "first_bot_phrase",
        ]
    ].copy()
    table_df["datetime"] = table_df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    table_df["duration_seconds"] = table_df["duration_seconds"].astype("Int64")
    table_df["end_reason"] = table_df["end_reason"].map(END_REASON_LABELS).fillna(table_df["end_reason"])
    table_df["dialogue_category"] = table_df["dialogue_category"].map(DIALOGUE_CATEGORIES).fillna(table_df["dialogue_category"])
    table_df["funnel_stage"] = table_df["funnel_stage"].map(FUNNEL_STAGE_LABELS).fillna(table_df["funnel_stage"])
    table_df.columns = [
        "Дата и время",
        "Телефон",
        "Длительность, сек",
        "Причина завершения",
        "Категория",
        "Этап воронки",
        "Первая реплика клиента",
        "Первая реплика бота",
    ]

    st.dataframe(table_df, use_container_width=True, hide_index=True)

    selection_labels = [
        f"{row.datetime:%d.%m.%Y %H:%M:%S} | {row.phone} | {int(row.duration_seconds)} сек | {DIALOGUE_CATEGORIES.get(row.dialogue_category, row.dialogue_category)}"
        for row in tab_df.itertuples()
    ]
    if not selection_labels:
        st.warning("Нет доступных звонков для выбора.")
        return

    selected_label = st.selectbox(
        "Выберите звонок",
        options=selection_labels,
        key=f"select_{key}",
        help="Введите часть даты, телефона или категории, чтобы быстро найти нужный звонок.",
    )
    selected_pos = selection_labels.index(selected_label)
    selected = tab_df.iloc[selected_pos]

    with st.expander("Полный диалог"):
        st.markdown(
            f"**Телефон:** {selected['phone']}  \n"
            f"**Дата и время:** {selected['datetime'].strftime('%Y-%m-%d %H:%M:%S')}  \n"
            f"**Длительность:** {int(selected['duration_seconds'])} сек  \n"
            f"**Категория:** {DIALOGUE_CATEGORIES.get(selected['dialogue_category'], selected['dialogue_category'])}"
        )
        transcript_text = selected.get("transcript", "")
        if transcript_text:
            st.text(transcript_text)
        else:
            st.caption("Расшифровка пустая.")
        audio_url = str(selected.get("audio_url", "") or "").strip()
        if audio_url:
            st.link_button("Открыть аудиозапись", audio_url)


def render_dialog_tabs(df: pd.DataFrame) -> None:
    tabs = st.tabs(
        [
            "Все звонки",
            "Ранние обрывы",
            "Интерес без следующего шага",
            "Плохая связь",
            "Аномальные звонки",
        ]
    )
    subsets = [
        df,
        df[df["dialogue_category"] == "early_client_hangup"],
        df[df["dialogue_category"] == "interested_not_converted"],
        df[df["dialogue_category"] == "bad_connection"],
        df[df["dialogue_category"] == "long_anomalous_call"],
    ]
    keys = ["all", "early", "interest", "bad", "long"]
    for tab, subset, key in zip(tabs, subsets, keys, strict=True):
        with tab:
            render_dialog_table(subset, key)


def main() -> None:
    if st is None:
        raise RuntimeError("Streamlit is not installed in this environment.")

    st.title("Аналитика звонков Botamin")
    st.subheader("Дашборд для тестового задания на роль руководителя продукта")
    st.caption("Диагностика конверсии ИИ-звонков: от попытки дозвона до назначения встречи.")
    st.write(
        "Источник: обезличенная выгрузка звонков за неделю. "
        "Классификация построена на прозрачных правилах по длительности, причинам завершения и тексту диалогов."
    )

    st.sidebar.header("Источник данных")
    source_mode = st.sidebar.radio(
        "Выберите источник",
        ["Использовать демо-выгрузку", "Загрузить свой CSV-файл"],
        index=0,
    )

    if source_mode == "Использовать демо-выгрузку":
        if DEFAULT_CSV_PATH.exists():
            raw_df = cached_load_csv(str(DEFAULT_CSV_PATH))
        else:
            st.warning("Демо-файл не найден в репозитории. Загрузите CSV-файл через боковую панель.")
            uploaded = st.sidebar.file_uploader("CSV-файл с выгрузкой звонков", type=["csv"])
            if uploaded is None:
                st.info("Загрузите CSV-файл, чтобы построить дашборд.")
                return
            raw_df = cached_load_csv(uploaded.getvalue())
    else:
        uploaded = st.sidebar.file_uploader("CSV-файл с выгрузкой звонков", type=["csv"])
        if uploaded is None:
            st.info("Загрузите CSV-файл, чтобы построить дашборд.")
            return
        raw_df = cached_load_csv(uploaded.getvalue())

    df = cached_normalize_df(raw_df)

    period_start = pd.Timestamp(df["date"].min())
    period_end = pd.Timestamp(df["date"].max())
    unique_contacts = df["phone"].nunique()

    st.sidebar.markdown("### Сводка")
    st.sidebar.metric("Всего звонков", _format_int(len(df)))
    st.sidebar.metric(
        "Период",
        f"{period_start.strftime('%d.%m')}–{period_end.strftime('%d.%m.%Y')}",
    )
    st.sidebar.metric("Уникальных контактов", _format_int(unique_contacts))

    st.sidebar.markdown("### Фильтры")
    available_dates = sorted(df["date"].dropna().unique().tolist())
    start_date = st.sidebar.selectbox(
        "Дата начала",
        available_dates,
        index=0,
        format_func=lambda value: value.strftime("%d.%m.%Y"),
    )
    end_date = st.sidebar.selectbox(
        "Дата окончания",
        available_dates,
        index=len(available_dates) - 1,
        format_func=lambda value: value.strftime("%d.%m.%Y"),
    )
    selected_dates = (pd.Timestamp(start_date), pd.Timestamp(end_date))

    end_reason_options = sorted(df["end_reason"].dropna().astype(str).unique().tolist())
    selected_end_reasons = st.sidebar.multiselect(
        "Причина завершения",
        end_reason_options,
        format_func=lambda key: END_REASON_LABELS.get(key, key),
        placeholder="Выберите варианты",
    )

    dialogue_options = list(DIALOGUE_CATEGORIES.keys())
    selected_dialogues = st.sidebar.multiselect(
        "Категория диалога",
        dialogue_options,
        format_func=lambda key: DIALOGUE_CATEGORIES.get(key, key),
        placeholder="Выберите варианты",
    )

    only_short_calls = st.sidebar.checkbox("Только звонки до 10 секунд")
    only_interested_without_meeting = st.sidebar.checkbox("Только звонки с интересом без встречи")
    only_first_calls = st.sidebar.checkbox("Только первый звонок контакту")
    only_repeat_calls = st.sidebar.checkbox("Только повторные звонки")

    filtered_df = apply_filters(
        df,
        selected_dates,
        selected_end_reasons,
        selected_dialogues,
        only_short_calls,
        only_interested_without_meeting,
        only_first_calls,
        only_repeat_calls,
    )

    st.markdown("## Ключевые метрики")
    kpis = calculate_kpis(filtered_df)
    render_kpi_grid(kpis)

    st.markdown("## Основной аналитический блок")
    left, right = st.columns([1.3, 1])

    with left:
        st.markdown("### Воронка")
        funnel_df = calculate_funnel_metrics(filtered_df)
        render_funnel(funnel_df)
        bottleneck = find_main_bottleneck(funnel_df)
        st.success(
            f"Главное узкое место: {bottleneck['from_label']} → {bottleneck['to_label']}\n\n"
            f"Потеря: {bottleneck['lost_count']} звонков / {bottleneck['lost_share']:.1%}"
        )
        st.caption("Это переход с наибольшей потерей в текущей выборке после входного этапа звонков.")

    with right:
        st.markdown("### Причины потерь")
        render_loss_reasons(filtered_df)

    st.markdown("## Качество первого контакта")
    render_quality_block(filtered_df)

    st.markdown("## Диалоги для анализа")
    render_dialog_tabs(filtered_df.sort_values(["datetime", "call_id"], ascending=[False, False]))

    st.markdown("## Приоритетная гипотеза")
    bottleneck = find_main_bottleneck(calculate_funnel_metrics(filtered_df))
    st.info(
        "Проблема:\n"
        f"{bottleneck['from_label']} → {bottleneck['to_label']}\n\n"
        "Наблюдение:\n"
        f"Клиент ответил в {kpis['response_share']['value']}, "
        f"предметный разговор составляет {kpis['meaningful_contact_share']['value']}, "
        f"подтверждённые встречи — {kpis['meeting_confirmed_share']['value']}.\n\n"
        "Гипотеза:\n"
        "Первая реплика перегружена информацией до подтверждения, что контакт готов говорить.\n\n"
        "Изменение:\n"
        "Вариант A — текущий сценарий.\n"
        "Вариант B — короткое представление + проверка доступности, затем оффер.\n\n"
        "Пример варианта B:\n"
        "«Имя Отчество, добрый день. Это Лариса, Botamin. Удобно 20 секунд?»\n\n"
        "После согласия:\n"
        "«Мы помогаем отделам продаж автоматизировать первый контакт с базой: бот сам прозванивает клиентов и "
        "передаёт менеджерам заинтересованные обращения. Это к Вам вопрос или к руководителю отдела продаж?»\n\n"
        "Основная метрика:\n"
        "Доля содержательных контактов.\n\n"
        "Вторичные метрики:\n"
        "Доля раскрытого оффера, доля предложения встречи, доля подтверждённых встреч.\n\n"
        "Защитные метрики:\n"
        "Негативные реакции, проблемы связи, звонки до 5 секунд."
    )

    st.markdown("## Аналитический вывод и рекомендации")
    render_analytic_conclusion(filtered_df, kpis, funnel_df)


if __name__ == "__main__":
    main()