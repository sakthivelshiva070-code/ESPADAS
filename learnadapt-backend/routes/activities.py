"""Student side: dashboard, activities, submission -> assessment -> new performance data."""
from flask import Blueprint, current_app, jsonify, request

from extensions import db
from models import Activity, Assessment
from services import pipeline
from services.adaptation_engine import compute_trend, repeated_error, update_mastery
from services.assessment import score_submission, strip_answers
from utils.helpers import current_user, err, role_required

bp = Blueprint("activities", __name__, url_prefix="/api")

MOTIVATION = {"increasing": "You're making progress. Keep going!",
              "decreasing": "Every try helps you learn. You can do this!",
              "stable": "Nice and steady. Keep going!", "new": "Welcome! Let's start learning."}


def _mine(activity_id):
    a = db.session.get(Activity, activity_id)
    user = current_user()
    return a if a and a.student_id == user.id and a.approval_status == "approved" else None


def _brief(a):
    return {"id": a.id, "topic": a.topic, "title": (a.content or {}).get("title"), "difficulty": a.difficulty,
            "question_count": len((a.content or {}).get("questions", [])), "completed": a.is_completed}


@bp.get("/activities")
@role_required("student")
def my_activities():
    rows = (Activity.query.filter_by(student_id=current_user().id, approval_status="approved")
            .order_by(Activity.id).all())
    return jsonify([_brief(a) for a in rows])


@bp.get("/activities/<int:activity_id>")
@role_required("student")
def get_activity(activity_id):
    a = _mine(activity_id)
    if not a:
        return err("activity not found", 404)
    return jsonify({**_brief(a), "params": {k: a.adaptation_params.get(k) for k in
                    ("content_format", "chunking", "presentation", "visual_support", "audio_support",
                     "step_by_step", "instructions")},
                    "content": strip_answers(a.content)})


@bp.post("/activities/<int:activity_id>/submit")
@role_required("student")
def submit(activity_id):
    """Body: {"answers": [{"question_id": "q1", "response": "3/4", "response_time": 12.5, "attempts": 1, "hint_used": false}]}"""
    a = _mine(activity_id)
    if not a:
        return err("activity not found", 404)
    if a.is_completed:
        return err("activity already submitted", 409)
    answers = (request.get_json(silent=True) or {}).get("answers")
    if not isinstance(answers, list) or not answers:
        return err("answers must be a non-empty list")
    cfg = current_app.config["ADAPT"]
    result = score_submission(a, answers)
    history = pipeline.student_history(a.student_id, a.topic)
    prev = history[-1].mastery_after if history else None
    mastery = update_mastery(prev, result["accuracy"], cfg["mastery_alpha"])
    rec = Assessment(activity_id=a.id, student_id=a.student_id, topic=a.topic, score=result["score"],
                     total_questions=result["total_questions"], accuracy=result["accuracy"],
                     avg_response_time=result["avg_response_time"], completion=result["completion"],
                     hint_usage=result["hint_usage"], attempts=result["attempts"],
                     error_patterns=result["error_patterns"], answers=result["answers"], mastery_after=mastery)
    db.session.add(rec)
    db.session.commit()

    history = pipeline.student_history(a.student_id, a.topic)
    trend = compute_trend([h.mastery_after for h in history], cfg["trend_delta"])
    next_status = None
    if current_app.config["AUTO_ADAPT"]:  # close the loop: next adaptation waits for teacher review
        pending = Activity.query.filter_by(lesson_id=a.lesson_id, student_id=a.student_id,
                                           approval_status="pending").first()
        next_status = "already awaiting teacher review" if pending else (
            pipeline.create_adaptation(a.lesson, a.student_id) and "awaiting teacher review")
    return jsonify({
        "summary": {"score": f"{result['score']}/{result['total_questions']}", "accuracy": result["accuracy"],
                    "avg_response_time": result["avg_response_time"], "completion": result["completion"],
                    "repeated_error": repeated_error(history, cfg["repeated_error_min"]),
                    "current_mastery": mastery, "trend": trend,
                    "message": MOTIVATION[trend]},
        "per_question": [{k: q[k] for k in ("question_id", "correct")} for q in result["answers"]],
        "next_activity": next_status,
    }), 201


@bp.get("/student/dashboard")
@role_required("student")
def dashboard():
    user = current_user()
    acts = Activity.query.filter_by(student_id=user.id, approval_status="approved").order_by(Activity.id).all()
    done = [x for x in acts if x.is_completed]
    todo = [x for x in acts if not x.is_completed]
    latest = {}
    for r in Assessment.query.filter_by(student_id=user.id).order_by(Assessment.id).all():
        latest[r.topic] = r
    focus = todo[0] if todo else (acts[-1] if acts else None)
    trend = "new"
    if focus:
        hist = pipeline.student_history(user.id, focus.topic)
        trend = compute_trend([h.mastery_after for h in hist], current_app.config["ADAPT"]["trend_delta"])
    return jsonify({
        "welcome": f"Welcome Back{', ' + user.full_name if user.full_name else ''}!",
        "todays_goal": focus.lesson.objective if focus else None,
        "progress": {"completed": len(done), "total": len(acts)},
        "current_mastery": {t: r.mastery_after for t, r in latest.items()},
        "next_activity": _brief(todo[0]) if todo else None,
        "motivation": MOTIVATION[trend],
    })
