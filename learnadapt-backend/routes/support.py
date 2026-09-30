"""Support & reporting: a simple student -> teacher communication channel (not an AI safeguarding tool)."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from extensions import db
from models import Classroom, Enrollment, SupportQuery
from utils.helpers import current_user, err, role_required, teacher_owns_student

bp = Blueprint("support", __name__, url_prefix="/api/support")
CATEGORIES = ("academic", "bullying", "isolation", "general")
STATUSES = ("pending", "in_review", "resolved")


@bp.post("")
@role_required("student")
def create_query():
    d = request.get_json(silent=True) or {}
    if d.get("category") not in CATEGORIES or not (d.get("message") or "").strip():
        return err(f"category must be one of {CATEGORIES} and message is required")
    user = current_user()
    q = Enrollment.query.join(Classroom, Classroom.id == Enrollment.class_id).filter(Enrollment.student_id == user.id)
    if d.get("classroom_id"):
        q = q.filter(Enrollment.class_id == d["classroom_id"])
    enrol = q.first()
    if not enrol:
        return err("join a classroom first so your teacher can see this", 400)
    item = SupportQuery(student_id=user.id, teacher_id=db.session.get(Classroom, enrol.class_id).teacher_id,
                        category=d["category"], message=d["message"].strip())
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@bp.get("")
@jwt_required()
def list_queries():
    user = current_user()
    q = SupportQuery.query.filter_by(**({"teacher_id": user.id} if user.role == "teacher" else {"student_id": user.id}))
    if request.args.get("status") in STATUSES:
        q = q.filter_by(status=request.args["status"])
    return jsonify([x.to_dict() for x in q.order_by(SupportQuery.id.desc()).all()])


@bp.patch("/<int:query_id>")
@role_required("teacher")
def update_status(query_id):
    item = db.session.get(SupportQuery, query_id)
    status = (request.get_json(silent=True) or {}).get("status")
    if not item or item.teacher_id != current_user().id:
        return err("query not found", 404)
    if status not in STATUSES:
        return err(f"status must be one of {STATUSES}")
    item.status = status
    db.session.commit()
    return jsonify(item.to_dict())
