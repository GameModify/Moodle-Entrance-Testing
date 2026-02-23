# Data Processing Service (FastAPI)

Python‑сервис (`data-processing-service/`), который принимает события от Moodle‑плагина, забирает детали попытки через Moodle REST API, анализирует результаты через GigaChat и зачисляет студента на курс нужного уровня.

---

## Что делает сервис

- **Endpoint `POST /analyze-and-enroll`**: принимает `user_id`, `quiz_id`, `attempt_id`, затем:
  - получает review попытки через `mod_quiz_get_attempt_review`;
  - формирует данные и отправляет их в GigaChat;
  - получает уровень **1 / 2 / 3**;
  - зачисляет пользователя в курс по маппингу уровней (`enrol_manual_enrol_users`).

- **Endpoint `POST /test-connection`** — проверка доступа к Moodle REST API.
- **Endpoint `GET /health`** — проверка состояния сервиса.
- **Endpoint `GET /`** — базовая информация о сервисе.

---

## Требования

- Python 3.10+ (рекомендовано)
- Доступ к Moodle REST API (токен и включённые webservice функции)
- Доступ к GigaChat (OAuth + chat completions)

---

## Установка и запуск (Windows)

Из корня репозитория:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r data-processing-service/requirements.txt