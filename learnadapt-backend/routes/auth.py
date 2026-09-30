from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt, jwt_required

from extensions import db, jwt
from models import Classroom, Enrollment, Profile, User
from utils.helpers import current_user, err

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
_blocklist = set()  # in-memory logout list (use Redis/DB in production)


@jwt.token_in_blocklist_loader
def _is_revoked(_header, payload):
    return payload["jti"] in _blocklist


def _token_for(user):
    return create_access_token(identity=str(user.id), additional_claims={"role": user.role})


@bp.post("/register")
def register():
    d = request.get_json(silent=True) or {}
    username, password, role = (d.get("username") or "").strip(), d.get("password") or "", d.get("role")
    if role not in ("teacher", "student"):
        return err("role must be 'teacher' or 'student'")
    if len(username) < 3 or len(password) < 6:
        return err("username needs 3+ characters and password 6+ characters")
    if User.query.filter_by(username=username).first():
        return err("username already taken", 409)
    classroom = None
    if d.get("invite_code"):
        classroom = Classroom.query.filter_by(invite_code=d["invite_code"].strip().upper()).first()
        if not classroom:
            return err("invalid invite code", 404)
    user = User(username=username, role=role, full_name=d.get("full_name", ""))
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    if role == "student":
        db.session.add(Profile(user_id=user.id, grade=d.get("grade"), subjects=[],
                               support_requirements={}, accessibility={}, learning_preference="mixed"))
        if classroom:
            db.session.add(Enrollment(class_id=classroom.id, student_id=user.id))
    db.session.commit()
    return jsonify({"token": _token_for(user), "user": user.to_dict()}), 201


@bp.post("/login")
def login():
    d = request.get_json(silent=True) or {}
    user = User.query.filter_by(username=(d.get("username") or "").strip()).first()
    if not user or not user.check_password(d.get("password") or ""):
        return err("invalid username or password", 401)
    if d.get("role") and d["role"] != user.role:  # role verification (blueprint section 7)
        return err(f"this account is a {user.role} account", 403)
    return jsonify({"token": _token_for(user), "user": user.to_dict()})


@bp.get("/me")
@jwt_required()
def me():
    return jsonify(current_user().to_dict())


@bp.post("/logout")
@jwt_required()
def logout():
    _blocklist.add(get_jwt()["jti"])
    return jsonify({"message": "logged out"})
