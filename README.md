# Botamin Call Analytics

Интерактивный dashboard для диагностики конверсии AI-звонков в продажах.  
Собран как тестовое задание Product Owner для Botamin.

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Для Windows:

```bash
.venv\Scripts\activate
```

## Что внутри

- прозрачная классификация звонков по длительности, причинам завершения и тексту диалогов;
- KPI по воронке звонков;
- причины потерь;
- блок качества первого контакта;
- таблица проблемных диалогов;
- автоматическая A/B-гипотеза.

## Публикация

1. Создать GitHub-репозиторий.
2. Загрузить код.
3. Открыть Streamlit Community Cloud.
4. Создать новое приложение.
5. Выбрать GitHub-репозиторий.
6. Указать `app.py`.
7. Нажать `Deploy`.
