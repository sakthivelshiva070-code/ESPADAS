from flask import Blueprint, jsonify, request

from extensions import db
from models import Activity, Lesson
from services import pipeline
from utils.helpers import current_user, err, role_required, student_ids_in_classroom, teacher_owns_classroom

bp = Blueprint("lessons", __name__, url_prefix="/api/lessons")


@bp.post("")
@role_required("teacher")
def create_lesson():
    """Teacher defines the core learning objective ONCE."""
    d = request.get_json(silent=True) or {}
    missing = [k for k in ("classroom_id", "subject", "topic", "objective") if not d.get(k)]
    if missing:
        return err(f"missing fields: {', '.join(missing)}")
    teacher = current_user()
    if not teacher_owns_classroom(teacher.id, d["classroom_id"]):
        return err("classroom not found", 404)
    lesson = Lesson(
        classroom_id=d["classroom_id"], teacher_id=teacher.id, subject=d["subject"], grade=d.get("grade"),
        topic=d["topic"], unit=d.get("unit", ""), objective=d["objective"],
        difficulty=(d.get("difficulty") or "intermediate").lower(),
        num_questions=int(d.get("num_questions", 10)),
        question_types=d.get("question_types") or ["mcq"],
        expected_minutes=int(d.get("expected_minutes", 15)), target_score=int(d.get("target_score", 75)))
    db.session.add(lesson)
    db.session.commit()
    return jsonify(lesson.to_dict()), 201


@bp.get("")
@role_required("teacher")
def list_lessons():
    q = Lesson.query.filter_by(teacher_id=current_user().id)
    if request.args.get("classroom_id"):
        q = q.filter_by(classroom_id=int(request.args["classroom_id"]))
    return jsonify([l.to_dict() for l in q.order_by(Lesson.id.desc()).all()])


@bp.post("/<int:lesson_id>/generate")
@role_required("teacher")
def generate(lesson_id):
    """Create adapted activities (pending teacher review) for the class, or for chosen students."""
    lesson = db.session.get(Lesson, lesson_id)
    if not lesson or lesson.teacher_id != current_user().id:
        return err("lesson not found", 404)
    roster = student_ids_in_classroom(lesson.classroom_id)
    wanted = (request.get_json(silent=True) or {}).get("student_ids") or roster
    created, skipped = [], []
    for sid in wanted:
        if sid not in roster:
            skipped.append({"student_id": sid, "reason": "not in this classroom"})
            continue
        open_acts = [a for a in Activity.query.filter_by(lesson_id=lesson.id, student_id=sid).all()
                     if a.approval_status == "pending" or (a.approval_status == "approved" and not a.is_completed)]
        if open_acts:
            skipped.append({"student_id": sid, "reason": "already has an open activity"})
            continue
        created.append(pipeline.create_adaptation(lesson, sid).id)
    return jsonify({"created_activity_ids": created, "skipped": skipped}), 201
