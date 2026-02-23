import asyncio
import json
from moodle_api import get_latest_attempt, get_attempt_review, enroll_user_to_course
from ai_analyzer import analyze_results
from config import settings

def format_attempt_for_ai(user_id, quiz_id, attempt_id, review_data):
    """Форматирует данные для отправки в ИИ"""
    # Теперь review_data уже содержит обработанные данные из moodle_api
    questions = review_data.get("questions", [])
    
    return {
        "student_id": user_id,
        "quiz_id": quiz_id,
        "attempt_id": attempt_id,
        "answers": questions  # данные уже обработаны в moodle_api
    }

async def process_student(user_id: int):
    attempt_id = await get_latest_attempt(user_id, settings.entry_test_id)
    print(attempt_id)
    if not attempt_id:
        print(f"ОШИБКА: У пользователя {user_id} нет завершённых попыток")
        return

    review = await get_attempt_review(attempt_id)
    results_json = format_attempt_for_ai(user_id, settings.entry_test_id, attempt_id, review)
    print("Данные для нейросети:")
    print(json.dumps(results_json, ensure_ascii=False, indent=2))

    level = await analyze_results(results_json)
    next_course_id = settings.courses.get(level)
    if next_course_id:
        await enroll_user_to_course(user_id, next_course_id)
        print(f"УСПЕХ: Пользователь {user_id} определён на уровень {level}, зачислен в курс {next_course_id}")
    else:
        print(f"ПРЕДУПРЕЖДЕНИЕ: Не удалось определить курс для уровня {level}")

if __name__ == "__main__":
    asyncio.run(process_student(3))
