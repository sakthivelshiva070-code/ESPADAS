"""End-to-end test of the closed loop.  Run:  pytest -v"""
import pytest

from app import create_app


@pytest.fixture()
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "ANTHROPIC_API_KEY": ""})
    return app.test_client()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def register(c, **kw):
    r = c.post("/api/auth/register", json=kw)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["token"]


def test_closed_loop(client):
    c = client
    t = register(c, username="teacher1", password="secret123", role="teacher", full_name="Ms Priya")
    cls = c.post("/api/classrooms", json={"name": "8A Maths", "grade": 8, "subject": "Mathematics"}, headers=auth(t))
    assert cls.status_code == 201
    code, cid = cls.get_json()["invite_code"], cls.get_json()["id"]

    s = register(c, username="studentc", password="secret123", role="student", full_name="Student C", invite_code=code)
    sid = c.get("/api/auth/me", headers=auth(s)).get_json()["id"]

    # teacher sets support requirements; student sets accessibility
    r = c.put(f"/api/students/{sid}/profile", headers=auth(t),
              json={"support_requirements": {"visual_support": True, "step_by_step": True}, "learning_preference": "visual"})
    assert r.get_json()["support_requirements"]["visual_support"] is True
    r = c.put("/api/profile/me", headers=auth(s), json={"accessibility": {"large_text": True, "text_to_speech": True}})
    assert r.get_json()["accessibility"]["text_to_speech"] is True

    # core lesson -> adapted activity (pending review)
    lesson = c.post("/api/lessons", headers=auth(t), json={
        "classroom_id": cid, "subject": "Mathematics", "grade": 8, "topic": "Fractions",
        "objective": "Add fractions with unlike denominators.", "difficulty": "intermediate",
        "num_questions": 10, "question_types": ["mcq", "short_answer"]}).get_json()
    gen = c.post(f"/api/lessons/{lesson['id']}/generate", headers=auth(t), json={}).get_json()
    assert len(gen["created_activity_ids"]) == 1

    # student cannot see unapproved work
    assert c.get("/api/activities", headers=auth(s)).get_json() == []

    card = c.get("/api/reviews", headers=auth(t)).get_json()[0]
    assert card["validation"]["passed"] and card["recommended_adaptation"]["visual_support"] is True
    aid = card["activity_id"]
    assert c.post(f"/api/reviews/{aid}/approve", headers=auth(t)).get_json()["status"] == "approved"

    # student view hides answers
    act = c.get(f"/api/activities/{aid}", headers=auth(s)).get_json()
    assert all("answer" not in q for q in act["content"]["questions"])

    # student answers: only 3/10 right -> accuracy 30%
    answers = []
    for i, q in enumerate(card["content"]["questions"]):
        right = i < 3
        answers.append({"question_id": q["id"], "response": q["answer"] if right else "wrong",
                        "response_time": 20, "attempts": 1, "hint_used": not right})
    res = c.post(f"/api/activities/{aid}/submit", headers=auth(s), json={"answers": answers})
    assert res.status_code == 201, res.get_json()
    summary = res.get_json()["summary"]
    assert summary["accuracy"] == 30.0 and summary["repeated_error"] == "denominator_conversion"
    assert c.post(f"/api/activities/{aid}/submit", headers=auth(s), json={"answers": answers}).status_code == 409

    # the loop closed: next adaptation is pending, easier, more support, targeted practice
    nxt = c.get("/api/reviews", headers=auth(t)).get_json()[0]
    p = nxt["recommended_adaptation"]
    assert p["difficulty_level"] == "beginner" and p["difficulty"] == "Decrease"
    assert p["scaffolding"] == "high" and "denominator conversion" in p["practice_type"].lower()
    assert nxt["validation"]["passed"]

    # teacher MODIFY then approve
    mod = c.post(f"/api/reviews/{nxt['activity_id']}/modify", headers=auth(t),
                 json={"changes": {"question_count": 5}, "approve": True}).get_json()
    assert mod["status"] == "approved" and len(mod["content"]["questions"]) == 5 and mod["teacher_modified"]

    # dashboards / analytics
    assert c.get("/api/student/dashboard", headers=auth(s)).get_json()["progress"]["total"] == 2
    d = c.get("/api/analytics/dashboard", headers=auth(t)).get_json()
    assert d["summary"]["students_requiring_attention"] == 1
    assert c.get(f"/api/analytics/classrooms/{cid}", headers=auth(t)).status_code == 200
    assert c.get(f"/api/analytics/students/{sid}", headers=auth(t)).get_json()["topics"]["Fractions"]["mastery"] == 30.0
    assert c.get("/api/analytics/effectiveness", headers=auth(t)).status_code == 200

    # support channel
    q = c.post("/api/support", headers=auth(s), json={"category": "general", "message": "I need help"})
    assert q.status_code == 201
    assert c.patch(f"/api/support/{q.get_json()['id']}", headers=auth(t), json={"status": "in_review"}).status_code == 200


def test_access_control(client):
    c = client
    t1 = register(c, username="teacherA", password="secret123", role="teacher")
    t2 = register(c, username="teacherB", password="secret123", role="teacher")
    code = c.post("/api/classrooms", json={"name": "A"}, headers=auth(t1)).get_json()["invite_code"]
    s = register(c, username="kid", password="secret123", role="student", invite_code=code)
    sid = c.get("/api/auth/me", headers=auth(s)).get_json()["id"]

    assert c.get(f"/api/students/{sid}/profile", headers=auth(t2)).status_code == 404   # other teacher
    assert c.get(f"/api/analytics/students/{sid}", headers=auth(t2)).status_code == 404
    assert c.get("/api/reviews", headers=auth(s)).status_code == 403                      # student on teacher route
    assert c.post("/api/classrooms", json={"name": "x"}, headers=auth(s)).status_code == 403
    assert c.get("/api/activities").status_code == 401                                   # no token
    assert c.post("/api/auth/login", json={"username": "kid", "password": "secret123", "role": "teacher"}).status_code == 403
