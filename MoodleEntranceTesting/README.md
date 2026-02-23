## MoodleEntranceTesting (FastAPI сервис)

Python‑сервис, который принимает события от Moodle‑плагина, забирает детали попытки через Moodle REST API, анализирует результаты через GigaChat и зачисляет студента на курс нужного уровня.

### Что делает

- **Endpoint `POST /analyze-and-enroll`**: принимает `user_id`, `quiz_id`, `attempt_id`, затем:
  - получает review попытки (`mod_quiz_get_attempt_review`);
  - формирует данные и отправляет их в GigaChat;
  - получает уровень **1 / 2 / 3**;
  - зачисляет пользователя в курс по маппингу уровней (`enrol_manual_enrol_users`).

### Требования

- Python 3.10+ (рекомендовано)
- Доступ к Moodle REST API (токен и включённые webservice функции)
- Доступ к GigaChat (OAuth + chat completions)

### Установка и запуск (Windows)

Из корня репозитория:

```
python -m venv venv
venv\Scripts\activate
pip install -r MoodleEntranceTesting/requirements.txt
```

Создайте файл `.env` **в папке `MoodleEntranceTesting`** (рядом с `env.example`):

- Скопируйте `MoodleEntranceTesting/env.example` → `MoodleEntranceTesting/.env`
- Заполните значения.

Пример переменных (смысл):

- `MOODLE_URL`: базовый URL Moodle (без слэша на конце)
- `MOODLE_TOKEN`: токен пользователя с доступом к REST API
- `AI_API_URL`: URL chat completions GigaChat
- `AI_MODEL`: модель (по умолчанию `GigaChat-2`)
- `GIGACHAT_OAUTH_URL`: OAuth endpoint для получения access token
- `GIGACHAT_AUTHORIZATION_TOKEN`: Basic‑token для OAuth
- `ENTRY_TEST_ID`: ID входного теста в Moodle

Запуск сервера:

```
cd MoodleEntranceTesting
python run_server.py
```

Проверка:

- `GET http://localhost:8000/health` → `{"status":"healthy", ...}`

### Настройка курсов по уровням

Маппинг задаётся в `config.py` (поле `courses`):

- уровень `1` → курс для начинающих
- уровень `2` → курс среднего уровня
- уровень `3` → продвинутый курс

### API

- `GET /` — базовая информация
- `GET /health` — healthcheck
- `POST /analyze-and-enroll` — основной endpoint (для Moodle‑плагина)
- `POST /test-connection` — проверка доступа к Moodle API (`core_webservice_get_site_info`)

### Важно про секреты

- **Не коммитьте** `.env` в git.
- Для репозитория оставляйте только `env.example`.

### Типичные проблемы

- **`MOODLE_URL должен начинаться с http:// или https://`**: проверьте значение в `.env`.
- **Moodle API exception**: проверьте `MOODLE_TOKEN` и включённые функции webservice.
- **GigaChat OAuth ошибки**: проверьте `GIGACHAT_AUTHORIZATION_TOKEN` и доступность `GIGACHAT_OAUTH_URL`.

