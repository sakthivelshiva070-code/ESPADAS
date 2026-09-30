"""Content validation layer (blueprint section 17). Runs BEFORE the teacher sees anything."""
import re

BLOCKED_TERMS = ["kill", "suicide", "sex", "porn", "drugs", "gun", "weapon", "hate", "stupid", "idiot"]


def _check(ok, detail=""):
    return {"ok": bool(ok), "detail": detail}


def validate_activity(content, lesson, params):
    checks = {}
    questions = (content or {}).get("questions") or []
    explanation = (content or {}).get("explanation") or {}

    # structure + answer validation
    ids = [q.get("id") for q in questions]
    bad = []
    for q in questions:
        if not q.get("prompt") or not q.get("answer") or q.get("type") not in ("mcq", "short_answer"):
            bad.append(f"{q.get('id')}: missing prompt/answer/type")
        elif q["type"] == "mcq":
            opts = q.get("options") or []
            if len(opts) < 2 or len(set(opts)) != len(opts) or q["answer"] not in opts:
                bad.append(f"{q.get('id')}: answer must be one of the unique options")
    if len(set(ids)) != len(ids):
        bad.append("question ids are not unique")
    checks["answer_validation"] = _check(questions and not bad, "; ".join(bad) or "answers consistent")

    checks["question_count"] = _check(
        len(questions) == params["question_count"],
        f"expected {params['question_count']}, got {len(questions)}")

    # curriculum alignment: topic keyword appears in the generated material
    text = " ".join([content.get("title", ""), explanation.get("text", "")] +
                    [q.get("prompt", "") for q in questions]).lower()
    keywords = [w for w in re.findall(r"[a-z]+", lesson.topic.lower()) if len(w) > 3] or [lesson.topic.lower()]
    checks["curriculum_alignment"] = _check(
        any(k[:5] in text for k in keywords), f"topic keywords {keywords}")

    diffs_ok = content.get("difficulty") == params["difficulty"] and all(
        q.get("difficulty", params["difficulty"]) == params["difficulty"] for q in questions)
    checks["difficulty_alignment"] = _check(diffs_ok, f"requested {params['difficulty']}")

    # adaptation compliance
    issues = []
    if params["visual_support"] and not (explanation.get("visual") or any(q.get("visual") for q in questions)):
        issues.append("visual support requested but no visual included")
    if params["step_by_step"] and not explanation.get("steps"):
        issues.append("step-by-step requested but no steps included")
    if params["scaffolding"] in ("medium", "high") and any(not q.get("hint") for q in questions):
        issues.append("every question needs a hint at this scaffolding level")
    if params.get("target_error") and questions:
        hits = sum(1 for q in questions if q.get("concept") == params["target_error"])
        if hits < len(questions) / 2:
            issues.append(f"at least half the questions must target '{params['target_error']}'")
    if params["instructions"] == "short" and len(content.get("instructions", "")) > 200:
        issues.append("instructions too long for 'short'")
    checks["adaptation_compliance"] = _check(not issues, "; ".join(issues) or "all requested supports present")

    # safety / relevance
    lowered = re.findall(r"[a-z]+", (text + " " + str(content.get("instructions", ""))).lower())
    flagged = sorted(set(lowered) & set(BLOCKED_TERMS))
    checks["safety_relevance"] = _check(not flagged, f"flagged terms: {flagged}" if flagged else "ok")

    issues_all = [f"{name}: {c['detail']}" for name, c in checks.items() if not c["ok"]]
    return {"passed": not issues_all, "checks": checks, "issues": issues_all}
