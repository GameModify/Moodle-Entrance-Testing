#!/usr/bin/env python3
"""
FastAPI сервер для обработки запросов от Moodle модуля
Автоматически анализирует результаты теста и зачисляет студента на курс
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import uvicorn

from moodle_api import get_latest_attempt, get_attempt_review, enroll_user_to_course
from ai_analyzer import analyze_results
from config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Moodle Entrance Testing API",
    description="API для автоматического анализа результатов входного теста и зачисления студентов",
    version="1.0.0"
)


class TestCompletionRequest(BaseModel):
    """Модель запроса от Moodle модуля"""
    user_id: int = Field(..., description="ID пользователя в Moodle")
    quiz_id: int = Field(..., description="ID теста")
    attempt_id: int = Field(..., description="ID попытки")
    course_id: Optional[int] = Field(None, description="ID курса (опционально)")


class TestCompletionResponse(BaseModel):
    """Модель ответа API"""
    success: bool = Field(..., description="Успешность операции")
    message: str = Field(..., description="Сообщение о результате")
    user_id: int = Field(..., description="ID пользователя")
    level: Optional[int] = Field(None, description="Определенный уровень студента")
    course_id: Optional[int] = Field(None, description="ID курса для зачисления")
    error: Optional[str] = Field(None, description="Описание ошибки, если есть")


def format_attempt_for_ai(user_id: int, quiz_id: int, attempt_id: int, review_data: Dict[str, Any]) -> Dict[str, Any]:
    """Форматирует данные для отправки в ИИ"""
    questions = review_data.get("questions", [])
    
    return {
        "student_id": user_id,
        "quiz_id": quiz_id,
        "attempt_id": attempt_id,
        "answers": questions
    }


@app.get("/")
async def root():
    """Корневой endpoint для проверки работы API"""
    return {
        "message": "Moodle Entrance Testing API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {"status": "healthy", "service": "moodle-entrance-testing"}


@app.post("/analyze-and-enroll", response_model=TestCompletionResponse)
async def analyze_and_enroll(request: TestCompletionRequest):
    """
    Основной endpoint для анализа результатов теста и зачисления студента
    
    Moodle модуль отправляет сюда данные о завершенном тесте,
    API анализирует результаты через ИИ и зачисляет студента на соответствующий курс
    """
    try:
        logger.info(f"Получен запрос на анализ для пользователя {request.user_id}, попытка {request.attempt_id}")
        
        # Проверяем, что это наш входной тест
        if request.quiz_id != settings.entry_test_id:
            logger.warning(f"Получен запрос для теста {request.quiz_id}, но ожидается {settings.entry_test_id}")
            return TestCompletionResponse(
                success=False,
                message=f"Этот API предназначен только для входного теста (ID: {settings.entry_test_id})",
                user_id=request.user_id,
                error=f"Неверный ID теста: {request.quiz_id}"
            )
        
        # Получаем детальную информацию о попытке
        logger.info(f"Получение детальной информации о попытке {request.attempt_id}")
        review = await get_attempt_review(request.attempt_id)
        
        if not review or not review.get("questions"):
            logger.error(f"Не удалось получить данные о попытке {request.attempt_id}")
            return TestCompletionResponse(
                success=False,
                message="Не удалось получить данные о попытке теста",
                user_id=request.user_id,
                error="Отсутствуют данные о попытке"
            )
        
        # Форматируем данные для ИИ
        results_json = format_attempt_for_ai(
            request.user_id, 
            request.quiz_id, 
            request.attempt_id, 
            review
        )
        logger.info(f"Отправка данных в ИИ для анализа пользователя {request.user_id}")
        
        # Анализируем результаты через ИИ
        level = await analyze_results(results_json)

        if not level or level not in settings.courses:
            logger.error(f"ИИ вернул неверный уровень {level} для пользователя {request.user_id}")
            return TestCompletionResponse(
                success=False,
                message=f"Не удалось определить корректный уровень студента (получен: {level})",
                user_id=request.user_id,
                level=level,
                error="Некорректный уровень от ИИ"
            )
        
        # Определяем курс для зачисления
        course_id = settings.courses[level]
        
        logger.info(f"Зачисление пользователя {request.user_id} на уровень {level}, курс {course_id}")
        
        # Зачисляем студента на курс
        enrollment_result = await enroll_user_to_course(request.user_id, course_id)

        if enrollment_result:
            # Moodle возвращает "Message was not sent." даже при успешном зачислении
            if enrollment_result.get("errorcode") == "Message was not sent.":
                logger.info(f"Пользователь {request.user_id} успешно зачислен на курс {course_id} (Moodle: сообщение не отправлено)")
                return TestCompletionResponse(
                    success=True,
                    message=f"Студент успешно зачислен на уровень {level}, курс {course_id}",
                    user_id=request.user_id,
                    level=level,
                    course_id=course_id
                )

            # Если ответ не содержит этого кода — значит, произошла ошибка
            logger.error(f"Ошибка зачисления пользователя {request.user_id}: {enrollment_result}")
            error_msg = enrollment_result.get("message", "Неизвестная ошибка")
            return TestCompletionResponse(
                success=False,
                message=f"Не удалось зачислить студента на курс {course_id}",
                user_id=request.user_id,
                level=level,
                course_id=course_id,
                error=error_msg
            )

        else:
            logger.error(f"Пустой ответ от Moodle при зачислении пользователя {request.user_id}")
            return TestCompletionResponse(
                success=False,
                message=f"Не удалось зачислить студента на курс {course_id}",
                user_id=request.user_id,
                level=level,
                course_id=course_id,
                error="Пустой ответ от Moodle API"
            )
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса для пользователя {request.user_id}: {str(e)}")
        return TestCompletionResponse(
            success=False,
            message="Внутренняя ошибка сервера",
            user_id=request.user_id,
            error=str(e)
        )


@app.post("/test-connection")
async def test_connection():
    """Тестовый endpoint для проверки соединения с Moodle"""
    try:
        # Простая проверка доступности Moodle API
        from moodle_api import post_ws
        
        params = {
            "wstoken": settings.moodle_token,
            "wsfunction": "core_webservice_get_site_info",
            "moodlewsrestformat": "json"
        }
        
        result = await post_ws(params)
        
        if "exception" in result:
            raise HTTPException(status_code=500, detail=f"Moodle API error: {result.get('message', 'Unknown error')}")
        
        return {
            "success": True,
            "message": "Соединение с Moodle установлено",
            "moodle_url": settings.moodle_url,
            "site_info": result
        }
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании соединения с Moodle: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка соединения с Moodle: {str(e)}")


if __name__ == "__main__":
    logger.info("Запуск FastAPI сервера для Moodle Entrance Testing")
    logger.info(f"Moodle URL: {settings.moodle_url}")
    logger.info(f"Entry Test ID: {settings.entry_test_id}")
    logger.info(f"Courses mapping: {settings.courses}")
    
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
