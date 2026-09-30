"""Orchestrates the closed loop: engine -> AI -> validation -> pending Activity."""
from flask import current_app

from extensions import db
from models import Activity, Assessment, Profile, utcnow
from services import adaptation_engine as engine
from services.ai_generation import build_request, generate_activity
from services.validation import validate_activity


def student_history(student_id, topic):
    return (Assessment.query.filter_by(student_id=student_id, topic=topic)
            .order_by(Assessment.created_at, Assessment.id).all())


def _generate_validated(lesson, params):
    cfg = current_app.config
    feedback, content, source, result = None, None, None, None
    for _ in range(cfg["AI_MAX_REGENERATIONS"] + 1):
        content, source = generate_activity(build_request(lesson, params), cfg, feedback)
        result = validate_activity(content, lesson, params)
        if result["passed"]:
            break
        feedback = result["issues"]
    result["source"] = source
    result["flagged_for_teacher"] = not result["passed"]  # invalid output is flagged, never silently sent
    return content, result


def create_adaptation(lesson, student_id):
    """Create the next pending activity for one student."""
    cfg = current_app.config["ADAPT"]
    profile = Profile.query.filter_by(user_id=student_id).first()
    history = student_history(student_id, lesson.topic)
    plan = engine.build_adaptation(profile, lesson, history, cfg)
    content, validation = _generate_validated(lesson, plan["params"])
    cycle = Activity.query.filter_by(lesson_id=lesson.id, student_id=student_id).count() + 1
    activity = Activity(
        lesson_id=lesson.id, student_id=student_id, teacher_id=lesson.teacher_id, topic=lesson.topic,
        content=content, difficulty=plan["params"]["difficulty"], adaptation_params=plan["params"],
        adaptation_reason=plan["reason"], performance_snapshot=plan["snapshot"],
        validation=validation, approval_status="pending", cycle=cycle,
    )
    db.session.add(activity)
    db.session.commit()
    return activity


def regenerate(activity, overrides):
    """Teacher MODIFY: apply parameter overrides, regenerate + revalidate the content."""
    allowed = {"difficulty", "scaffolding", "visual_support", "audio_support", "step_by_step",
               "question_count", "target_error", "instructions", "chunking", "content_format"}
    params = dict(activity.adaptation_params)
    for k, v in (overrides or {}).items():
        if k in allowed:
            params[k] = v
    params["difficulty"] = engine.normalize_level(params["difficulty"])
    cfg = current_app.config["ADAPT"]
    params["question_count"] = int(min(max(int(params["question_count"]), cfg["min_questions"]), cfg["max_questions"]))
    if params["scaffolding"] in ("medium", "high"):
        params["scaffolding_options"] = sorted(set(params.get("scaffolding_options", []) + ["hints"]))
    content, validation = _generate_validated(activity.lesson, params)
    activity.adaptation_params = params
    activity.difficulty = params["difficulty"]
    activity.content = content
    activity.validation = validation
    activity.teacher_modified = True
    activity.reviewed_at = utcnow()
    db.session.commit()
    return activity
