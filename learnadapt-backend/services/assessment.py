"""Scoring + performance summary (blueprint sections 21-22)."""
from collections import Counter
from fractions import Fraction


def _norm(value):
    return "".join(str(value).lower().split())


def _as_fraction(value):
    try:
        return Fraction(_norm(value))
    except (ValueError, ZeroDivisionError):
        return None


def is_correct(question, response):
    if response is None or str(response).strip() == "":
        return False
    accepted = [question["answer"]] + list(question.get("accepted_answers") or [])
    if any(_norm(response) == _norm(a) for a in accepted):
        return True
    r = _as_fraction(response)  # 6/8 == 3/4 == 0.75
    return r is not None and any(r == _as_fraction(a) for a in accepted if _as_fraction(a) is not None)


def strip_answers(content):
    """Student-safe copy: never send correct answers to the browser."""
    safe = {k: v for k, v in content.items() if not k.startswith("_")}
    safe["questions"] = [{k: v for k, v in q.items() if k not in ("answer", "accepted_answers")}
                         for q in content.get("questions", [])]
    return safe


def score_submission(activity, answers):
    """answers: [{question_id, response, response_time, attempts, hint_used}]"""
    questions = {q["id"]: q for q in activity.content["questions"]}
    total = len(questions)
    by_id = {a.get("question_id"): a for a in answers if a.get("question_id") in questions}

    correct, errors, times, hints, attempts, detail = 0, Counter(), [], 0, 0, []
    for qid, a in by_id.items():
        q = questions[qid]
        ok = is_correct(q, a.get("response"))
        correct += ok
        if not ok:
            errors[q.get("concept", "unknown")] += 1
        if a.get("response_time") is not None:
            times.append(float(a["response_time"]))
        hints += 1 if a.get("hint_used") else 0
        attempts += int(a.get("attempts") or 1)
        detail.append({"question_id": qid, "response": a.get("response"), "correct": ok,
                       "response_time": a.get("response_time"), "attempts": a.get("attempts", 1),
                       "hint_used": bool(a.get("hint_used")), "difficulty": q.get("difficulty"),
                       "concept": q.get("concept")})
    answered = len(by_id)
    return {
        "score": correct, "total_questions": total, "answered": answered,
        "accuracy": round(correct / answered * 100, 1) if answered else 0.0,
        "completion": round(answered / total * 100, 1) if total else 0.0,
        "avg_response_time": round(sum(times) / len(times), 1) if times else 0.0,
        "hint_usage": hints, "attempts": attempts,
        "error_patterns": dict(errors), "answers": detail,
    }
