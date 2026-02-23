from typing import Dict
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Конфигурация приложения с валидацией через Pydantic"""
    
    # Moodle настройки
    moodle_url: str = Field(..., description="URL Moodle сервера", alias="MOODLE_URL")
    moodle_token: str = Field(..., description="Токен для доступа к Moodle API", alias="MOODLE_TOKEN")
    
    # AI настройки
    ai_api_url: str = Field(..., description="URL API для анализа результатов", alias="AI_API_URL")
    ai_model: str = Field(default="GigaChat-2", description="Модель AI для анализа", alias="AI_MODEL")
    
    # GigaChat OAuth настройки
    gigachat_oauth_url: str = Field(..., description="URL OAuth для получения токена GigaChat", alias="GIGACHAT_OAUTH_URL")
    gigachat_authorization_token: str = Field(..., description="Authorization токен для OAuth запроса", alias="GIGACHAT_AUTHORIZATION_TOKEN")
    
    # Настройки тестирования
    entry_test_id: int = Field(default=2, description="ID входного теста", alias="ENTRY_TEST_ID")
    
    # Курсы по уровням
    courses: Dict[int, int] = Field(
        default={
            1: 4,  # курс A1–A2
            2: 5,  # курс B1–B2
            3: 6,  # курс C1+
        },
        description="Соответствие уровней и курсов"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": "",
    }
    
    @field_validator("moodle_url")
    @classmethod
    def validate_moodle_url(cls, v):
        """Валидация URL Moodle"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("MOODLE_URL должен начинаться с http:// или https://")
        return v.rstrip("/")
    
    @field_validator("ai_api_url")
    @classmethod
    def validate_ai_api_url(cls, v):
        """Валидация URL AI API"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("AI_API_URL должен начинаться с http:// или https://")
        return v.rstrip("/")
    
    @field_validator("gigachat_oauth_url")
    @classmethod
    def validate_gigachat_oauth_url(cls, v):
        """Валидация URL OAuth GigaChat"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("GIGACHAT_OAUTH_URL должен начинаться с http:// или https://")
        return v.rstrip("/")
    
    @field_validator("courses")
    @classmethod
    def validate_courses(cls, v):
        """Валидация курсов"""
        if not v:
            raise ValueError("Курсы не могут быть пустыми")
        for level, course_id in v.items():
            if not isinstance(level, int) or level < 1 or level > 3:
                raise ValueError(f"Уровень {level} должен быть от 1 до 3")
            if not isinstance(course_id, int) or course_id < 1:
                raise ValueError(f"ID курса {course_id} должен быть положительным числом")
        return v


# Создаем глобальный экземпляр настроек
settings = Settings()

# Для обратной совместимости экспортируем переменные как раньше
MOODLE_URL = settings.moodle_url
MOODLE_TOKEN = settings.moodle_token
AI_API_URL = settings.ai_api_url
AI_MODEL = settings.ai_model
ENTRY_TEST_ID = settings.entry_test_id
COURSES = settings.courses