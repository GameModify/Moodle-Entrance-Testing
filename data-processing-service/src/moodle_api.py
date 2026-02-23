import aiohttp
import re
from bs4 import BeautifulSoup
from config import settings

async def post_ws(params: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{settings.moodle_url}/webservice/rest/server.php", data=params, ssl=False) as r:
            return await r.json()

def to_float_score(s):
    """Конвертирует строку в float для оценки"""
    if s is None or s == "":
        return 0.0
    try:
        # Moodle может использовать запятую
        return float(str(s).replace(",", "."))
    except:
        try:
            return float(re.findall(r"[\d\.]+", str(s))[0])
        except:
            return 0.0

def extract_choice_label(label_el):
    """Извлекает текст варианта ответа из HTML элемента"""
    # обычно есть span.answernumber и div.flex-fill (или текст внутри)
    number = label_el.find("span", class_="answernumber")
    textpart = label_el.find(class_="flex-fill")
    if textpart:
        text = textpart.get_text(" ", strip=True)
    else:
        # fallback — весь текст
        text = label_el.get_text(" ", strip=True)
    if number:
        num = number.get_text(" ", strip=True)
        # убрать дублирование если number включён в text
        text = text if num not in text else text
        return f"{num}{text}".strip()
    return text

async def get_latest_attempt(user_id: int, quiz_id: int):
    """Получает последнюю завершённую попытку пользователя"""
    params = {
        "wstoken": settings.moodle_token,
        "wsfunction": "mod_quiz_get_user_quiz_attempts",
        "moodlewsrestformat": "json",
        "quizid": quiz_id,
        "userid": user_id,
        "status": "finished",
        "includepreviews": 0
    }
    data = await post_ws(params)
    attempts = data.get("attempts", [])
    if not attempts:
        print("Попытки не найдены!")
    return attempts[-1]["id"]

async def get_attempt_review(attempt_id: int):
    """Получает подробный review attempt и парсит данные"""
    params = {
        "wstoken": settings.moodle_token,
        "wsfunction": "mod_quiz_get_attempt_review",
        "moodlewsrestformat": "json",
        "attemptid": attempt_id,
        "page": -1
    }
    review = await post_ws(params)
    if "exception" in review:
        raise Exception("Ошибка при получении review attempt: " + review.get("message", ""))

    questions = review.get("questions", [])
    clean_answers = []

    for q in questions:
        raw_html = q.get("html", "")
        soup = BeautifulSoup(raw_html, "html.parser")

        # --- текст вопроса ---
        qtext_tag = soup.find("div", class_="qtext")
        question_text = qtext_tag.get_text(" ", strip=True) if qtext_tag else soup.get_text(" ", strip=True)

        # --- варианты ответов ---
        choices = []
        labels = soup.select('.answer [data-region="answer-label"]')
        for lab in labels:
            lab_text = extract_choice_label(lab)
            if lab_text:
                choices.append(re.sub(r'\s+', ' ', lab_text).strip())

        # fallback, если нет data-region
        if not choices:
            blocks = soup.select('.answer .r0, .answer .r1')
            for b in blocks:
                text = b.get_text(" ", strip=True)
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    choices.append(text)

        # --- правильный ответ ---
        correct = ""
        right_block = soup.find(class_="rightanswer")
        if right_block:
            # получаем весь текст без тегов
            txt = right_block.get_text(" ", strip=True)
            # убираем префиксы вроде "Правильный ответ:" или "Correct Answer:"
            txt = re.sub(r'^(Правильный ответ|Correct answer|Ответ):\s*', '', txt, flags=re.IGNORECASE)
            # заменяем множественные пробелы на один
            correct = re.sub(r'\s+', ' ', txt).strip()
        # --- ответ студента ---
        student_answer = None

        # 1) checked inputs
        checked = soup.select('input[checked], input[checked="checked"]')
        if checked:
            vals = []
            for inp in checked:
                lab = inp.find_parent(attrs={"data-region": "answer-label"})
                if lab:
                    vals.append(extract_choice_label(lab))
                else:
                    vals.append(inp.parent.get_text(" ", strip=True))
            if vals:
                student_answer = ", ".join(vals)

        # 2) API responses
        if not student_answer and q.get("responses"):
            vals = []
            for r in q.get("responses", []):
                a = r.get("answer", "")
                if a:
                    vals.append(BeautifulSoup(a, "html.parser").get_text(" ", strip=True))
            if vals:
                student_answer = ", ".join(vals)

        # 3) fallback "Сохранено:"
        if not student_answer:
            m = re.search(r'Сохранено:\s*([^<\n\r]+)', raw_html)
            if m:
                student_answer = m.group(1).strip()

        # 4) state mapping
        state = q.get("state", "").lower() or q.get("status", "").lower()
        if not student_answer:
            if state in ("gaveup", "noanswer", "todo", "notanswered"):
                student_answer = "не ответил"
            elif state in ("gradedright", "correct"):
                student_answer = correct or "правильно"
            elif state in ("gradedwrong", "wrong"):
                student_answer = "неверно"
            else:
                student_answer = state or "неизвестно"

        # --- балл ---
        raw_mark = q.get("mark") or q.get("marks") or q.get("score") or q.get("maxmark")
        score = to_float_score(raw_mark)
        if student_answer == "не ответил":
            score = 0.0

        clean_answers.append({
            "slot": q.get("slot"),
            "question": question_text,
            "choices": choices,
            "student_answer": student_answer,
            "correct_answer": correct,
            "score": score,
            "state": q.get("state", "")
        })

    return {
        "questions": clean_answers,
        "raw_review": review
    }


async def enroll_user_to_course(user_id: int, course_id: int):
    params = {
        "wstoken": settings.moodle_token,
        "moodlewsrestformat": "json",
        "wsfunction": "enrol_manual_enrol_users",
    }
    payload = {
        "enrolments[0][roleid]": 5,
        "enrolments[0][userid]": user_id,
        "enrolments[0][courseid]": course_id,
    }

    res = await post_ws({**params, **payload})
    return res
