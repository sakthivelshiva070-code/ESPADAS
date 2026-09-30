"""Class-level and student-level analytics (blueprint sections 24-26). Based on measurable data only."""
from collections import defaultdict
from statistics import mean

from extensions import db
from models import Activity, Assessment, Classroom, Enrollment, Lesson, User
from services.adaptation_engine import compute_trend, repeated_error


def _by_topic(student_id):
    rows = (Assessment.query.filter_by(student_id=student_id)
            .order_by(Assessment.created_at, Assessment.id).all())
    grouped = defaultdict(list)
    for a in rows:
        grouped[a.topic].append(a)
    return grouped


def student_overview(student_id, cfg):
    """Student progress view (section 25)."""
    topics = {}
    for topic, rows in _by_topic(student_id).items():
        masteries = [r.mastery_after for r in rows if r.mastery_after is not None]
        topics[topic] = {
            "mastery": masteries[-1] if masteries else None,
            "trend": compute_trend(masteries, cfg["trend_delta"]),
            "main_error": repeated_error(rows, cfg["repeated_error_min"]),
            "recent_performance": [
                {"activity": i + 1, "score": r.accuracy, "mastery": r.mastery_after,
                 "completion": r.completion, "date": r.created_at.isoformat()}
                for i, r in enumerate(rows)],
        }
    all_m = [t["mastery"] for t in topics.values() if t["mastery"] is not None]
    last_act = (Activity.query.filter_by(student_id=student_id, approval_status="approved")
                .order_by(Activity.id.desc()).first())
    return {
        "student_id": student_id,
        "overall_mastery": round(mean(all_m), 1) if all_m else None,
        "topics": topics,
        "current_support": _support_labels(last_act.adaptation_params) if last_act else [],
        "current_focus": next((t["main_error"] for t in topics.values() if t["main_error"]), None),
    }


def _support_labels(p):
    labels = []
    if p.get("visual_support"): labels.append("Visual scaffolding")
    if p.get("chunking") or p.get("question_count", 10) <= 6: labels.append("Short activities")
    if p.get("step_by_step"): labels.append("Step-by-step instructions")
    if p.get("audio_support"): labels.append("Audio support")
    return labels


def attention_list(student_ids, cfg):
    """Students needing attention: low mastery, falling trend or low completion."""
    out = []
    for sid in student_ids:
        student = db.session.get(User, sid)
        for topic, rows in _by_topic(sid).items():
            masteries = [r.mastery_after for r in rows if r.mastery_after is not None]
            if not masteries:
                continue
            trend = compute_trend(masteries, cfg["trend_delta"])
            why = []
            if masteries[-1] < cfg["attention_mastery"]: why.append("low mastery")
            if trend == "decreasing": why.append("decreasing trend")
            if rows[-1].completion is not None and rows[-1].completion < cfg["completion_low"]:
                why.append("low completion")
            if why:
                out.append({"student_id": sid, "name": student.full_name or student.username,
                            "topic": topic, "mastery": masteries[-1], "trend": trend,
                            "main_error": repeated_error(rows, cfg["repeated_error_min"]), "reasons": why})
    return sorted(out, key=lambda x: x["mastery"])


def classroom_metrics(classroom, cfg):
    sids = [e.student_id for e in Enrollment.query.filter_by(class_id=classroom.id).all()]
    rows = (Assessment.query.join(Activity, Activity.id == Assessment.activity_id)
            .join(Lesson, Lesson.id == Activity.lesson_id)
            .filter(Lesson.classroom_id == classroom.id).all())
    latest = {}
    for r in sorted(rows, key=lambda r: (r.created_at, r.id)):
        latest[(r.student_id, r.topic)] = r.mastery_after
    topic_m = defaultdict(list)
    for (_, topic), m in latest.items():
        if m is not None:
            topic_m[topic].append(m)
    base = (Activity.query.join(Lesson, Lesson.id == Activity.lesson_id)
            .filter(Lesson.classroom_id == classroom.id))
    return {
        "classroom_id": classroom.id, "name": classroom.name,
        "students": len(sids),
        "average_mastery": round(mean(latest.values()), 1) if latest else None,
        "average_accuracy": round(mean(r.accuracy for r in rows), 1) if rows else None,
        "activity_completion": round(mean(r.completion for r in rows), 1) if rows else None,
        "topic_performance": {t: round(mean(v), 1) for t, v in topic_m.items()},
        "pending_reviews": base.filter(Activity.approval_status == "pending").count(),
        "active_activities": sum(1 for a in base.filter(Activity.approval_status == "approved").all()
                                 if not a.is_completed),
        "students_needing_attention": attention_list(sids, cfg),
    }


def adaptation_effectiveness(student_ids):
    """Section 26: pre- vs post-adaptation score and repeated-error reduction (demo metrics)."""
    improved, deltas, err_before, err_after, n = 0, [], 0, 0, 0
    for sid in student_ids:
        for rows in _by_topic(sid).values():
            if len(rows) < 2:
                continue
            n += 1
            d = rows[-1].accuracy - rows[0].accuracy
            deltas.append(d)
            improved += d > 0
            top = repeated_error(rows[:1], 1)
            if top:
                err_before += (rows[0].error_patterns or {}).get(top, 0)
                err_after += (rows[-1].error_patterns or {}).get(top, 0)
    return {
        "students_with_multiple_activities": n,
        "successful_adaptations": improved,
        "average_score_change": round(mean(deltas), 1) if deltas else None,
        "repeated_error_before": err_before, "repeated_error_after": err_after,
        "note": "Prototype/demo metrics unless backed by a real user study.",
    }
