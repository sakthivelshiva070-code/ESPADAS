from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from extensions import db
from models import Profile, User
from utils.helpers import (ACCESSIBILITY_KEYS, PREFERENCES, SUPPORT_KEYS, clean_flags, current_user, err,
                           role_required, teacher_owns_student)

bp = Blueprint("profiles", __name__, url_prefix="/api")


def _profile_for(user_id):
    p = Profile.query.filter_by(user_id=user_id).first()
    if not p:
        p = Profile(user_id=user_id, subjects=[], support_requirements={}, accessibility={})
        db.session.add(p)
    return p


@bp.get("/profile/me")
@role_required("student")
def my_profile():
    return jsonify(_profile_for(current_user().id).to_dict())


@bp.put("/profile/me")
@role_required("student")
def update_my_profile():
    """Students change their own accessibility settings + learning preference only."""
    d = request.get_json(silent=True) or {}
    p = _profile_for(current_user().id)
    if "accessibility" in d:
        p.accessibility = {**(p.accessibility or {}), **clean_flags(d["accessibility"], ACCESSIBILITY_KEYS)}
    if d.get("learning_preference") in PREFERENCES:
        p.learning_preference = d["learning_preference"]
    db.session.commit()
    return jsonify(p.to_dict())


@bp.get("/students/<int:sid>/profile")
@role_required("teacher")
def student_profile(sid):
    if not teacher_owns_student(current_user().id, sid):
        return err("student not found in your classrooms", 404)
    data = _profile_for(sid).to_dict()
    data["student"] = db.session.get(User, sid).to_dict()
    return jsonify(data)


@bp.put("/students/<int:sid>/profile")
@role_required("teacher")
def update_student_profile(sid):
    """Teachers set support requirements (support needs, not diagnoses)."""
    if not teacher_owns_student(current_user().id, sid):
        return err("student not found in your classrooms", 404)
    d = request.get_json(silent=True) or {}
    p = _profile_for(sid)
    if "support_requirements" in d:
        p.support_requirements = {**(p.support_requirements or {}),
                                  **{k: bool(v) for k, v in clean_flags(d["support_requirements"], SUPPORT_KEYS).items()}}
    if d.get("learning_preference") in PREFERENCES:
        p.learning_preference = d["learning_preference"]
    if "grade" in d:
        p.grade = d["grade"]
    if "subjects" in d and isinstance(d["subjects"], list):
        p.subjects = d["subjects"]
    db.session.commit()
    return jsonify(p.to_dict())
