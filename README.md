## Moodle Entrance Testing

Система автоматического распределения студентов по курсам в Moodle на основе результатов входного теста и анализа через ИИ (GigaChat).

### Архитектура

- **local‑плагин для Moodle** (`entrance_testing`):
  - Отслеживает завершение входного теста (событие `mod_quiz\event\attempt_graded`).
  - Складывает попытки в очередь в собственной таблице БД.
  - Через cron/adhoc‑задачи отправляет данные о попытках на внешний API.
  - Настраивается из админ‑панели Moodle (URL API, ID теста, таймауты, количество попыток и т.п.).
- **FastAPI‑сервис** (`MoodleEntranceTesting`):
  - Принимает запросы от плагина по REST (`/analyze-and-enroll`).
  - Забирает через Moodle REST API подробный review попытки.
  - Подготавливает данные и отправляет их в GigaChat.
  - Получает уровень $1$ / $2$ / $3$ и автоматически зачисляет пользователя на соответствующий курс.

Схема работы:

1. Студент завершает входной тест в Moodle.
2. Плагин `local_entrance_testing` добавляет запись в очередь.
3. Планировщик задач плагина отправляет данные в FastAPI‑сервис.
4. FastAPI‑сервис анализирует попытку через GigaChat и определяет уровень.
5. Сервис вызывает Moodle REST API и зачисляет студента на нужный курс.

### Структура репозитория

- `entrance_testing/` — локальный плагин Moodle:
  - `lib.php` — observer события теста и отправка очереди на внешний API.
  - `classes/task/` — фоновые задачи (cron/adhoc) по обработке очереди.
  - `db/` — описание таблицы очереди и событий.
  - `lang/` — языковые строки (ru/en).
  - `settings.php`, `admin.php`, `task.php`, `version.php` — интеграция с админкой Moodle.
- `MoodleEntranceTesting/` — Python‑сервис и утилиты:
  - `fastapi_server.py` — основной FastAPI‑приложение (эндпоинты, бизнес‑логика).
  - `run_server.py` — удобный скрипт запуска сервера.
  - `config.py` — загрузка и валидация настроек из `.env`.
  - `moodle_api.py` — обёртка над Moodle REST API и парсинг попыток теста.
  - `ai_analyzer.py` — интеграция с GigaChat и определение уровня по результатам.
  - `main.py` — пример одиночной обработки студента.
  - `create_simple_report.py`, `create_practical_documentation.py` — генерация DOCX‑отчётов о проекте.
  - `env.example` — пример файла окружения.
  - `requirements.txt` — зависимости Python.
  - `README.md` — установка/настройка/запуск сервиса.

### Быстрый запуск Python‑сервиса локально (FastAPI)

1. **Создайте виртуальное окружение и установите зависимости**:

```
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r MoodleEntranceTesting/requirements.txt
```

2. **Создайте файл `.env` на основе `env.example` в папке `MoodleEntranceTesting`**:

- Заполните:
  - `MOODLE_URL` — URL вашего Moodle.
  - `MOODLE_TOKEN` — токен для Moodle REST API.
  - `AI_API_URL`, `GIGACHAT_OAUTH_URL`, `GIGACHAT_AUTHORIZATION_TOKEN` — настройки GigaChat.
  - При необходимости измените `ENTRY_TEST_ID` и соответствие уровней/курсов в `config.py`.

3. **Запустите сервер** (из корня проекта или из папки `MoodleEntranceTesting`):

```
cd MoodleEntranceTesting
python run_server.py
```

4. **Проверьте, что сервис работает**:

- Откройте в браузере `http://localhost:8000/health` — должен вернуться JSON со статусом `healthy`.
- Полная инструкция находится в `MoodleEntranceTesting/README.md`.

### Подключение плагина Moodle

1. Скопируйте папку `entrance_testing` в директорию `/local/` вашего Moodle‑сервера.
2. Зайдите под администратором, выполните обновление БД и установку плагина.
3. В админке перейдите в:
   - «Администрирование сайта → Плагины → Локальные плагины → Входное тестирование».
4. В настройках укажите:
   - **URL API**: `http://<ваш-сервер>:8000/analyze-and-enroll`
   - **ID входного теста**: идентификатор теста, по которому идёт распределение.
   - Таймаут запроса, количество попыток, SSL‑настройки — по необходимости.
5. Нажмите «Проверить соединение», чтобы убедиться, что FastAPI‑сервис доступен.

### Технологический стек

- **Backend Moodle**: PHP, local‑плагин, события `mod_quiz`, cron/adhoc‑задачи.
- **API‑сервис**: Python, FastAPI, Uvicorn, aiohttp, BeautifulSoup.
- **ИИ‑анализ**: GigaChat API.
- **Документация**: генерация DOCX‑отчётов через `python-docx`.
