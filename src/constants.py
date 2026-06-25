EXPECTED_COLUMNS = [
    "телефон",
    "дата и время",
    "длительность мин:сек",
    "статус",
    "запись аудио",
    "причина завершения",
    "история диалога юзер-бот",
]

TECHNICAL_SHORT_RESPONSES = [
    "алло",
    "да",
    "слушаю",
    "что",
    "не слышу",
    "повторите",
    "говорите",
]

BAD_CONNECTION_KEYWORDS = [
    "не слышу",
    "вас не слышно",
    "плохо слышно",
    "повторите",
    "прерывается",
    "связь",
]

NO_INTEREST_KEYWORDS = [
    "не интересно",
    "неинтересно",
    "не надо",
    "не нужно",
    "не актуально",
    "не звоните",
    "не беспокоить",
]

CALLBACK_KEYWORDS = [
    "перезвоните",
    "перезвони",
    "позже",
    "неудобно говорить",
    "сейчас не могу",
    "завтра",
    "через час",
]

INTEREST_KEYWORDS = [
    "интересно",
    "расскажите",
    "подробнее",
    "как это работает",
    "пришлите",
    "что по цене",
    "давайте",
]

MEETING_OFFER_KEYWORDS = [
    "созвон",
    "встреча",
    "демонстрация",
    "презентация",
    "когда удобно",
    "назначить",
    "в календарь",
]

MEETING_CONFIRMATION_KEYWORDS = [
    "договорились",
    "записал",
    "записала",
    "отправлю приглашение",
    "в календаре",
    "поставил встречу",
    "ссылка на встречу",
]

DECISION_MAKER_KEYWORDS = [
    "коммерческий директор",
    "директор по продажам",
    "руководитель отдела продаж",
    "кто принимает решение",
    "это к вам вопрос",
    "кто отвечает",
    "не я решаю",
]

OFFER_KEYWORDS = [
    "искусственный интеллект",
    "ии",
    "бот звонит",
    "голосовой бот",
    "автоматизация продаж",
    "первую линию продаж",
    "теплых клиентов",
    "отдел продаж",
]

TECHNICAL_END_REASONS = {
    "bot_hangup",
    "elevenlabs_hangup",
    "queue_timeout",
    "network_error",
    "bad_number",
}

END_REASON_LABELS = {
    "bot_hangup": "Обрыв ботом",
    "client_hangup": "Обрыв клиентом",
    "elevenlabs_hangup": "Обрыв голосового движка",
    "no_answer": "Нет ответа",
    "hangup": "Сброс",
    "queue_timeout": "Таймаут очереди",
    "answering_machine": "Автоответчик",
    "no_user_speech": "Нет реплики клиента",
    "network_error": "Сетевая ошибка",
    "bad_number": "Неверный номер",
}

DIALOGUE_CATEGORIES = {
    "no_dialogue": "Нет диалога",
    "long_anomalous_call": "Аномально длинный звонок",
    "bad_connection": "Проблема связи",
    "early_client_hangup": "Ранний обрыв клиентом",
    "no_interest": "Нет интереса",
    "callback_requested": "Просьба перезвонить",
    "meeting_confirmed": "Встреча подтверждена",
    "interested_not_converted": "Интерес без следующего шага",
    "not_decision_maker": "Не ЛПР",
    "bot_scenario_issue": "Вероятная проблема сценария",
    "other": "Другое",
}

FUNNEL_STAGE_LABELS = {
    "no_answer": "Попытки звонка",
    "answered": "Клиент ответил",
    "meaningful_contact": "Предметный разговор",
    "offer_revealed": "Оффер раскрыт",
    "meeting_offered": "Предложена встреча",
    "meeting_confirmed": "Встреча подтверждена",
}

FUNNEL_STAGE_ORDER = [
    "no_answer",
    "answered",
    "meaningful_contact",
    "offer_revealed",
    "meeting_offered",
    "meeting_confirmed",
]