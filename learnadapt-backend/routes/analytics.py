from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from extensions import db
from models import Activity, Classroom, Enrollment, Lesson, User
from services import analytics
from utils.helpers import current_user, err, role_required, teacher_owns_classroom, teacher_owns_student

bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


def _cfg():
    return current_app.config["ADAPT"]


@bp.get("/dashboard")
@role_required("teacher")
def teacher_dashboard():
    t = current_user()
    classes = Classroom.query.filter_by(teacher_id=t.id).all()
    cards, attention, goals = [], [], []
    for c in classes:
        m = analytics.classroom_metrics(c, _cfg())
        cards.append({k: m[k] for k in ("classroom_id", "name", "students", "active_activities",
                                        "average_mastery", "pending_reviews")})
        attention += m["students_needing_attention"]
        lesson = Lesson.query.filter_by(classroom_id=c.id).order_by(Lesson.id.desc()).first()
        if lesson:
            goals.append({"classroom": c.name, "subject": lesson.subject, "grade": lesson.grade,
                          "topic": lesson.topic, "goal": lesson.objective})
    pending = Activity.query.filter_by(teacher_id=t.id, approval_status="pending").count()
    return jsonify({
        "welcome": f"Hello, {t.full_name or t.username}",
        "summary": {"classes": len(classes), "students": sum(c["students"] for c in cards),
                    "pending_reviews": pending, "students_requiring_attention": len(attention)},
        "todays_learning_goals": goals, "class_overview": cards, "attention_panel": attention,
    })


@bp.get("/classrooms/<int:class_id>")
@role_required("teacher")
def classroom(class_id):
    if not teacher_owns_classroom(current_user().id, class_id):
        return err("classroom not found", 404)
    return jsonify(analytics.classroom_metrics(db.session.get(Classroom, class_id), _cfg()))


@bp.get("/students/<int:sid>")
@role_required("teacher")
def student(sid):
    if not teacher_owns_student(current_user().id, sid):
        return err("student not found in your classrooms", 404)
    data = analytics.student_overview(sid, _cfg())
    data["student"] = db.session.get(User, sid).to_dict()
    return jsonify(data)


@bp.get("/me")
@role_required("student")
def my_progress():
    return jsonify(analytics.student_overview(current_user().id, _cfg()))


@bp.get("/effectiveness")
@role_required("teacher")
def effectiveness():
    """Pre- vs post-adaptation results for the demo (blueprint section 26)."""
    t = current_user()
    cid = request.args.get("classroom_id", type=int)
    q = Enrollment.query.join(Classroom, Classroom.id == Enrollment.class_id).filter(Classroom.teacher_id == t.id)
    if cid:
        q = q.filter(Enrollment.class_id == cid)
    sids = sorted({e.student_id for e in q.all()})
    return jsonify(analytics.adaptation_effectiveness(sids))
