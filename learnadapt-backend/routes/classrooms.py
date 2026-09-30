from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required

from extensions import db
from models import Classroom, Enrollment, User
from utils.helpers import current_user, err, generate_invite_code, role_required, teacher_owns_classroom

bp = Blueprint("classrooms", __name__, url_prefix="/api/classrooms")


@bp.post("")
@role_required("teacher")
def create_classroom():
    d = request.get_json(silent=True) or {}
    if not d.get("name"):
        return err("name is required")
    c = Classroom(name=d["name"], grade=d.get("grade"), subject=d.get("subject"),
                  learning_objectives=d.get("learning_objectives", ""),
                  invite_code=generate_invite_code(), teacher_id=current_user().id)
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


@bp.get("")
@jwt_required()
def list_classrooms():
    user = current_user()
    if user.role == "teacher":
        rows = Classroom.query.filter_by(teacher_id=user.id).all()
    else:
        rows = (Classroom.query.join(Enrollment, Enrollment.class_id == Classroom.id)
                .filter(Enrollment.student_id == user.id).all())
    return jsonify([c.to_dict() if user.role == "teacher" else
                    {k: v for k, v in c.to_dict().items() if k != "invite_code"} for c in rows])


@bp.get("/<int:class_id>/students")
@role_required("teacher")
def roster(class_id):
    if not teacher_owns_classroom(current_user().id, class_id):
        return err("classroom not found", 404)
    students = (User.query.join(Enrollment, Enrollment.student_id == User.id)
                .filter(Enrollment.class_id == class_id).all())
    return jsonify([s.to_dict() for s in students])


@bp.post("/join")
@role_required("student")
def join():
    code = ((request.get_json(silent=True) or {}).get("invite_code") or "").strip().upper()
    c = Classroom.query.filter_by(invite_code=code).first()
    if not c:
        return err("invalid invite code", 404)
    user = current_user()
    if Enrollment.query.filter_by(class_id=c.id, student_id=user.id).first():
        return err("already enrolled", 409)
    db.session.add(Enrollment(class_id=c.id, student_id=user.id))
    db.session.commit()
    return jsonify({"message": "joined", "classroom": {k: v for k, v in c.to_dict().items() if k != "invite_code"}})
