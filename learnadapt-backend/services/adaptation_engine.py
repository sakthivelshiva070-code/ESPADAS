"""Rule-based adaptation engine (blueprint sections 13-15).

Input : student profile + lesson + the student's past assessments on this topic
Output: adaptation parameters, a human-readable reason, and a performance snapshot
        (the snapshot feeds the teacher's Adaptation Card).
Nothing here calls the AI - it is plain, explainable Python.
"""
from collections import Counter

LEVELS = ["beginner", "intermediate", "advanced"]
SCAFFOLD = ["low", "medium", "high"]
_LEVEL_ALIASES = {"easy": "beginner", "basic": "beginner", "medium": "intermediate",
                  "hard": "advanced", "difficult": "advanced"}


def normalize_level(value):
    v = (value or "intermediate").strip().lower()
    v = _LEVEL_ALIASES.get(v, v)
    return v if v in LEVELS else "intermediate"


def compute_trend(mastery_values, delta=3):
    """mastery_values: oldest -> newest."""
    if len(mastery_values) < 2:
        return "new"
    diff = mastery_values[-1] - mastery_values[-2]
    if diff >= delta:
        return "increasing"
    if diff <= -delta:
        return "decreasing"
    return "stable"


def update_mastery(previous, accuracy, alpha=0.6):
    if previous is None:
        return round(accuracy, 1)
    return round(alpha * accuracy + (1 - alpha) * previous, 1)


def repeated_error(history, minimum=2, window=3):
    """Most frequent error tag across the last `window` assessments, if it repeats."""
    counts = Counter()
    for a in history[-window:]:
        for tag, n in (a.error_patterns or {}).items():
            counts[tag] += n
    if not counts:
        return None
    tag, n = counts.most_common(1)[0]
    return tag if n >= minimum else None


def _rank_up(scaffolding, steps=1):
    return SCAFFOLD[min(SCAFFOLD.index(scaffolding) + steps, len(SCAFFOLD) - 1)]


def build_adaptation(profile, lesson, history, cfg):
    """history: this student's Assessments for this topic, oldest -> newest."""
    support = (profile.support_requirements if profile else {}) or {}
    access = (profile.accessibility if profile else {}) or {}
    preference = (profile.learning_preference if profile else "mixed") or "mixed"

    reasons = []
    level = normalize_level(lesson.difficulty)
    scaffolding = "low"
    q_count = lesson.num_questions or 10
    chunking = False
    target_error = None
    snapshot = {"current_mastery": None, "previous_score": None, "accuracy": None,
                "completion": None, "avg_response_time": None, "repeated_error": None,
                "trend": "new"}

    if not history:
        reasons.append("No performance data yet, so the first activity follows the lesson's "
                       "difficulty and the student's support requirements.")
        difficulty_change = "same"
    else:
        last = history[-1]
        prev_params = (last.activity.adaptation_params or {}) if last.activity else {}
        level = normalize_level(prev_params.get("difficulty", level))
        scaffolding = prev_params.get("scaffolding", "low")
        q_count = prev_params.get("question_count", q_count)
        masteries = [a.mastery_after for a in history if a.mastery_after is not None]
        trend = compute_trend(masteries, cfg["trend_delta"])
        target_error = repeated_error(history, cfg["repeated_error_min"])
        acc, comp, rt = last.accuracy or 0, last.completion or 0, last.avg_response_time or 0
        snapshot.update({
            "current_mastery": masteries[-1] if masteries else None,
            "previous_score": history[-2].accuracy if len(history) > 1 else None,
            "accuracy": acc, "completion": comp, "avg_response_time": rt,
            "repeated_error": target_error, "trend": trend,
        })

        old_level = level
        # 1. Accuracy (section 13.1)
        if acc < cfg["accuracy_significant"]:
            level = LEVELS[max(LEVELS.index(level) - 1, 0)]
            scaffolding = "high"
            reasons.append(f"Accuracy was {acc:.0f}% (below {cfg['accuracy_significant']}%), so "
                           "difficulty is reduced and scaffolding increased.")
        elif acc < cfg["accuracy_moderate"]:
            scaffolding = "medium" if scaffolding == "low" else scaffolding
            reasons.append(f"Accuracy was {acc:.0f}%: same topic with additional support.")
        elif acc < cfg["accuracy_challenge"]:
            reasons.append(f"Accuracy was {acc:.0f}%: continue at the current level.")
        else:
            if trend != "decreasing":
                level = LEVELS[min(LEVELS.index(level) + 1, len(LEVELS) - 1)]
                scaffolding = SCAFFOLD[max(SCAFFOLD.index(scaffolding) - 1, 0)]
                reasons.append(f"Accuracy was {acc:.0f}%: challenge is increased gradually.")
        # 2. Mastery trend
        if trend == "decreasing":
            scaffolding = _rank_up(scaffolding)
            reasons.append("Mastery is decreasing, so extra support is added.")
        elif trend == "increasing" and acc >= cfg["accuracy_moderate"] and level == old_level:
            level = LEVELS[min(LEVELS.index(level) + 1, len(LEVELS) - 1)]
            reasons.append("Mastery is increasing, so challenge is raised gradually.")
        # 3. Completion (13.4) / response time (13.3: supporting metric only)
        if comp < cfg["completion_low"]:
            q_count = max(cfg["min_questions"], round(q_count / 2))
            chunking = True
            reasons.append(f"Only {comp:.0f}% of the activity was completed, so it is shortened "
                           "and split into smaller sections.")
        elif rt > cfg["response_time_high"]:
            q_count = max(cfg["min_questions"], round(q_count * 0.7))
            chunking = True
            scaffolding = _rank_up(scaffolding) if scaffolding == "low" else scaffolding
            reasons.append("Response times were high, so shorter chunks and simpler presentation "
                           "are used (response time is a supporting signal only).")
        elif comp >= 90 and acc >= cfg["accuracy_moderate"] and q_count < (lesson.num_questions or 10):
            q_count = min(lesson.num_questions, q_count + 2)
            reasons.append("Completion was strong, so activity length is gradually restored.")
        # 4. Repeated error (13.2)
        if target_error:
            reasons.append(f"The error '{target_error.replace('_', ' ')}' keeps repeating, so the "
                           "activity adds an explanation and targeted practice for it.")
        difficulty_change = ("decrease" if LEVELS.index(level) < LEVELS.index(old_level)
                             else "increase" if LEVELS.index(level) > LEVELS.index(old_level)
                             else "same")

    # Support requirements from the profile (section 14 matrix)
    reading = support.get("reading_support") or support.get("simplified_instructions")
    visual = bool(support.get("visual_support")) or preference == "visual"
    audio = bool(support.get("audio_support")) or preference == "audio" or bool(access.get("text_to_speech"))
    step_by_step = bool(support.get("step_by_step"))
    if support.get("reduced_distraction") or access.get("one_task_at_a_time") or access.get("content_chunking"):
        chunking = True
    if reading:
        reasons.append("Reading support enabled: simplified wording and short instructions.")
    if visual:
        reasons.append("Visual support enabled: diagrams/visual examples added.")
    if audio:
        reasons.append("Audio support enabled: content is written to be read aloud.")
    if step_by_step:
        reasons.append("Step-by-step enabled: tasks are broken into smaller steps.")

    # Scaffolding drives the concrete support options
    options = {"low": ["hints_on_request"],
               "medium": ["hints", "worked_example"],
               "high": ["hints", "worked_example", "step_by_step_example", "key_word_highlighting"]}[scaffolding]
    if scaffolding == "high":
        visual, step_by_step = True, True
    if step_by_step and "step_by_step_example" not in options:
        options = options + ["step_by_step_example"]
    if visual and "visual_representation" not in options:
        options = options + ["visual_representation"]

    if audio:
        fmt = "audio-supported"
    elif step_by_step:
        fmt = "step-by-step"
    elif visual:
        fmt = "visual"
    elif preference in ("text", "interactive"):
        fmt = preference
    else:
        fmt = "mixed"

    params = {
        "difficulty": level,
        "difficulty_change": difficulty_change,
        "scaffolding": scaffolding,
        "scaffolding_options": options,
        "visual_support": visual,
        "audio_support": audio,
        "step_by_step": step_by_step,
        "content_format": fmt,
        "question_count": int(min(max(q_count, cfg["min_questions"]), cfg["max_questions"])),
        "target_error": target_error,
        "instructions": "short" if (reading or scaffolding == "high" or chunking) else "standard",
        "chunking": chunking,
        "presentation": {
            "large_text": bool(support.get("large_text") or access.get("large_text")),
            "increased_spacing": bool(support.get("increased_spacing")),
            "reduced_distraction": bool(support.get("reduced_distraction")),
        },
    }
    return {"params": params, "reason": " ".join(reasons), "snapshot": snapshot}
