"""Teacher review: Adaptation Card + Approve / Modify / Reject (blueprint sections 15, 18)."""
from flask import Blueprint, jsonify, request

from extensions import db
from models import Activity, User, utcnow
from services import pipeline
from utils.helpers import current_user, err, role_required

bp = Blueprint("reviews", __name__, url_prefix="/api/reviews")


def adaptation_card(a):
    s, p = a.performance_snapshot or {}, a.adaptation_params or {}
    student = db.session.get(User, a.student_id)
    return {
        "activity_id": a.id, "status": a.approval_status, "cycle": a.cycle, "topic": a.topic,
        "student": {"id": student.id, "name": student.full_name or student.username},
        "current_mastery": s.get("current_mastery"), "previous_score": s.get("previous_score"),
        "repeated_error": s.get("repeated_error"), "completion": s.get("completion"),
        "trend": s.get("trend"),
        "recommended_adaptation": {
            "difficulty": p.get("difficulty_change", "same").title(), "difficulty_level": p.get("difficulty"),
            "scaffolding": p.get("scaffolding"), "visual_support": p.get("visual_support"),
            "audio_support": p.get("audio_support"), "step_by_step": p.get("step_by_step"),
            "question_count": p.get("question_count"), "content_format": p.get("content_format"),
            "practice_type": f"Targeted {p['target_error'].replace('_', ' ')} practice" if p.get("target_error") else "General practice",
        },
        "adaptation_reason": a.adaptation_reason,
        "validation": a.validation, "teacher_modified": a.teacher_modified,
        "teacher_note": a.teacher_note,
        "content": a.content,  # teacher sees full content incl. answers
    }


def _get_own(activity_id):
    a = db.session.get(Activity, activity_id)
    return a if a and a.teacher_id == current_user().id else None


@bp.get("")
@role_required("teacher")
def list_reviews():
    status = request.args.get("status", "pending")
    rows = (Activity.query.filter_by(teacher_id=current_user().id, approval_status=status)
            .order_by(Activity.id.desc()).all())
    return jsonify([adaptation_card(a) for a in rows])


@bp.get("/<int:activity_id>")
@role_required("teacher")
def get_card(activity_id):
    a = _get_own(activity_id)
    return jsonify(adaptation_card(a)) if a else err("activity not found", 404)


@bp.post("/<int:activity_id>/approve")
@role_required("teacher")
def approve(activity_id):
    a = _get_own(activity_id)
    if not a:
        return err("activity not found", 404)
    if a.approval_status != "pending":
        return err(f"activity is already {a.approval_status}", 409)
    a.approval_status, a.reviewed_at = "approved", utcnow()
    a.teacher_note = (request.get_json(silent=True) or {}).get("note", a.teacher_note)
    db.session.commit()
    return jsonify(adaptation_card(a))


@bp.post("/<int:activity_id>/modify")
@role_required("teacher")
def modify(activity_id):
    """Body: {"changes": {"difficulty": "beginner", "question_count": 5, ...}, "approve": false, "note": "..."}"""
    a = _get_own(activity_id)
    if not a:
        return err("activity not found", 404)
    if a.approval_status != "pending":
        return err(f"activity is already {a.approval_status}", 409)
    d = request.get_json(silent=True) or {}
    pipeline.regenerate(a, d.get("changes"))
    a.teacher_note = d.get("note", a.teacher_note)
    if d.get("approve"):
        a.approval_status = "approved"
    db.session.commit()
    return jsonify(adaptation_card(a))


@bp.post("/<int:activity_id>/reject")
@role_required("teacher")
def reject(activity_id):
    a = _get_own(activity_id)
    if not a:
        return err("activity not found", 404)
    if a.approval_status != "pending":
        return err(f"activity is already {a.approval_status}", 409)
    a.approval_status, a.reviewed_at = "rejected", utcnow()
    a.teacher_note = (request.get_json(silent=True) or {}).get("reason", "")
    db.session.commit()
    return jsonify(adaptation_card(a))
