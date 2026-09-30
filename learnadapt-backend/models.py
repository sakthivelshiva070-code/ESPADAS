from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # "teacher" | "student"
    full_name = db.Column(db.String(120), default="")
    created_at = db.Column(db.DateTime, default=utcnow)
    profile = db.relationship("Profile", uselist=False, backref="user", cascade="all, delete-orphan")

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def to_dict(self):
        return {"id": self.id, "username": self.username, "full_name": self.full_name, "role": self.role}


class Profile(db.Model):
    __tablename__ = "profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    grade = db.Column(db.Integer)
    subjects = db.Column(db.JSON, default=list)
    support_requirements = db.Column(db.JSON, default=dict)
    accessibility = db.Column(db.JSON, default=dict)
    learning_preference = db.Column(db.String(20), default="mixed")  # visual/text/audio/interactive/mixed

    def to_dict(self):
        return {
            "user_id": self.user_id, "grade": self.grade, "subjects": self.subjects or [],
            "support_requirements": self.support_requirements or {},
            "accessibility": self.accessibility or {},
            "learning_preference": self.learning_preference,
        }


class Classroom(db.Model):
    __tablename__ = "classrooms"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    grade = db.Column(db.Integer)
    subject = db.Column(db.String(80))
    learning_objectives = db.Column(db.Text, default="")
    invite_code = db.Column(db.String(12), unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "grade": self.grade, "subject": self.subject,
            "learning_objectives": self.learning_objectives, "invite_code": self.invite_code,
            "teacher_id": self.teacher_id,
        }


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classrooms.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("class_id", "student_id"),)


class Lesson(db.Model):
    """The teacher's core learning objective, created once (blueprint section 12)."""
    __tablename__ = "lessons"
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.Integer)
    topic = db.Column(db.String(120), nullable=False)
    unit = db.Column(db.String(120), default="")
    objective = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), default="intermediate")
    num_questions = db.Column(db.Integer, default=10)
    question_types = db.Column(db.JSON, default=lambda: ["mcq"])
    expected_minutes = db.Column(db.Integer, default=15)
    target_score = db.Column(db.Integer, default=75)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "classroom_id": self.classroom_id, "subject": self.subject,
            "grade": self.grade, "topic": self.topic, "unit": self.unit, "objective": self.objective,
            "difficulty": self.difficulty, "num_questions": self.num_questions,
            "question_types": self.question_types, "expected_minutes": self.expected_minutes,
            "target_score": self.target_score,
        }


class Activity(db.Model):
    """An individualised, AI-generated activity for one student (one adaptation cycle)."""
    __tablename__ = "activities"
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    topic = db.Column(db.String(120))
    content = db.Column(db.JSON)
    difficulty = db.Column(db.String(20))
    adaptation_params = db.Column(db.JSON)
    adaptation_reason = db.Column(db.Text)
    performance_snapshot = db.Column(db.JSON)
    validation = db.Column(db.JSON)
    # pending | approved | rejected
    approval_status = db.Column(db.String(12), default="pending")
    teacher_modified = db.Column(db.Boolean, default=False)
    teacher_note = db.Column(db.Text)
    cycle = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=utcnow)
    reviewed_at = db.Column(db.DateTime)

    lesson = db.relationship("Lesson", backref="activities")
    student = db.relationship("User", foreign_keys=[student_id])
    assessment = db.relationship("Assessment", uselist=False, backref="activity")

    @property
    def is_completed(self):
        return self.assessment is not None


class Assessment(db.Model):
    __tablename__ = "assessments"
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    topic = db.Column(db.String(120))
    score = db.Column(db.Integer)
    total_questions = db.Column(db.Integer)
    accuracy = db.Column(db.Float)
    avg_response_time = db.Column(db.Float)
    completion = db.Column(db.Float)
    hint_usage = db.Column(db.Integer, default=0)
    attempts = db.Column(db.Integer, default=0)
    error_patterns = db.Column(db.JSON, default=dict)
    answers = db.Column(db.JSON)
    mastery_after = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "activity_id": self.activity_id, "topic": self.topic,
            "score": self.score, "total_questions": self.total_questions,
            "accuracy": self.accuracy, "avg_response_time": self.avg_response_time,
            "completion": self.completion, "hint_usage": self.hint_usage,
            "attempts": self.attempts, "error_patterns": self.error_patterns or {},
            "mastery_after": self.mastery_after,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SupportQuery(db.Model):
    __tablename__ = "queries"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    category = db.Column(db.String(30), nullable=False)  # academic|bullying|isolation|general
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(12), default="pending")  # pending|in_review|resolved
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "student_id": self.student_id, "teacher_id": self.teacher_id,
            "category": self.category, "message": self.message, "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
