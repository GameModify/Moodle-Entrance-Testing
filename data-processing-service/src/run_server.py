#!/usr/bin/env python3
"""
Скрипт запуска FastAPI сервера для Moodle Entrance Testing
"""

import uvicorn
import logging
from config import settings

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Запуск FastAPI сервера для Moodle Entrance Testing")
    logger.info(f"Moodle URL: {settings.moodle_url}")
    logger.info(f"Entry Test ID: {settings.entry_test_id}")
    logger.info(f"Courses mapping: {settings.courses}")
    logger.info(f"AI Model: {settings.ai_model}")
    
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )





