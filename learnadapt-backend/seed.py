"""Demo data:  python seed.py   ->  teacher/teacher123, students student1..3 / student123, class code printed."""
from app import create_app
from extensions import db
from models import Classroom, Enrollment, Lesson, Profile, User
from services import pipeline
from utils.helpers import generate_invite_code

app = create_app()
with app.app_context():
    if User.query.filter_by(username="teacher").first():
        raise SystemExit("Demo data already exists (delete instance/learnadapt.db to reseed).")
    t = User(username="teacher", role="teacher", full_name="Ms. Priya"); t.set_password("teacher123")
    db.session.add(t); db.session.flush()
    c = Classroom(name="Grade 8 Mathematics", grade=8, subject="Mathematics",
                  learning_objectives="Fractions", invite_code=generate_invite_code(), teacher_id=t.id)
    db.session.add(c); db.session.flush()
    specs = [("student1", "Student A", {"reading_support": True}, "text"),
             ("student2", "Student B", {"visual_support": True, "step_by_step": True}, "visual"),
             ("student3", "Student C", {"visual_support": True, "reduced_distraction": True, "large_text": True}, "visual")]
    for uname, name, support, pref in specs:
        s = User(username=uname, role="student", full_name=name); s.set_password("student123")
        db.session.add(s); db.session.flush()
        db.session.add(Profile(user_id=s.id, grade=8, subjects=["Mathematics"], support_requirements=support,
                               accessibility={}, learning_preference=pref))
        db.session.add(Enrollment(class_id=c.id, student_id=s.id))
    lesson = Lesson(classroom_id=c.id, teacher_id=t.id, subject="Mathematics", grade=8, topic="Fractions",
                    objective="Add and subtract fractions with unlike denominators.", difficulty="intermediate",
                    num_questions=10, question_types=["mcq", "short_answer"])
    db.session.add(lesson); db.session.commit()
    for e in Enrollment.query.filter_by(class_id=c.id).all():
        pipeline.create_adaptation(lesson, e.student_id)
    print(f"Seeded. Invite code: {c.invite_code}. Login: teacher/teacher123 or student1/student123")
