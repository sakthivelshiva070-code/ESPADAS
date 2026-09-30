import secrets
import string
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from extensions import db
from models import Classroom, Enrollment, User

SUPPORT_KEYS = [
    "reading_support", "visual_support", "audio_support", "step_by_step",
    "reduced_distraction", "simplified_instructions", "increased_spacing", "large_text",
]
ACCESSIBILITY_KEYS = [
    "high_contrast", "large_text", "font_size", "line_spacing", "dyslexia_font", "reduced_animation",
    "text_to_speech", "reading_speed", "read_instructions_aloud",
    "keyboard_navigation", "visible_focus", "large_controls",
    "short_instructions", "one_task_at_a_time", "content_chunking", "reduced_distractions",
    "predictable_navigation",
]
PREFERENCES = ["visual", "text", "audio", "interactive", "mixed"]


def err(message, code=400):
    return jsonify({"error": message}), code


def current_user():
    return db.session.get(User, int(get_jwt_identity()))


def role_required(role):
    """Use on a route: @role_required("teacher"). Also checks the JWT is valid."""
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated(*args, **kwargs):
            if get_jwt().get("role") != role:
                return err(f"Forbidden: {role}s only", 403)
            return fn(*args, **kwargs)
        return decorated
    return wrapper


def clean_flags(data, allowed):
    """Keep only known keys (bools stay bools, other scalars pass through)."""
    return {k: v for k, v in (data or {}).items() if k in allowed}


def generate_invite_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        if not Classroom.query.filter_by(invite_code=code).first():
            return code


def teacher_owns_classroom(teacher_id, classroom_id):
    return Classroom.query.filter_by(id=classroom_id, teacher_id=teacher_id).first() is not None


def teacher_owns_student(teacher_id, student_id):
    """Teachers may only access students enrolled in one of their classrooms."""
    return (
        db.session.query(Enrollment.id)
        .join(Classroom, Classroom.id == Enrollment.class_id)
        .filter(Classroom.teacher_id == teacher_id, Enrollment.student_id == student_id)
        .first() is not None
    )


def student_ids_in_classroom(classroom_id):
    return [e.student_id for e in Enrollment.query.filter_by(class_id=classroom_id).all()]
