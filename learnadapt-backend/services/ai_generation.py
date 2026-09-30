"""AI content-generation layer (blueprint section 16).

Receives ONLY structured, privacy-safe parameters (no names / IDs).
- With ANTHROPIC_API_KEY set -> calls Claude and expects JSON.
- Without a key -> offline demo generator so the team can build/test the whole loop.
"""
import json
import random
from fractions import Fraction

SYSTEM_PROMPT = """You create classroom learning activities for teachers of students with mild to \
moderate learning support needs. Follow the given parameters EXACTLY. Use plain, friendly, age-appropriate \
language and short sentences. Return ONLY valid JSON (no markdown, no commentary) in this schema:
{
 "title": str,
 "difficulty": "<same as requested>",
 "instructions": str,
 "explanation": {"text": str, "example": str, "steps": [str], "visual": {"type": str, "description": str} | null},
 "questions": [{"id": "q1", "type": "mcq" | "short_answer", "prompt": str, "options": [str] (mcq only),
   "answer": str, "accepted_answers": [str], "hint": str, "concept": "snake_case_skill_tag",
   "difficulty": "<same as requested>", "visual": {"type": str, "description": str} | null}]
}
Rules: exactly `question_count` questions; every mcq answer must appear in options; if visual_support is true \
include a visual in the explanation; if step_by_step is true give explanation.steps; if scaffolding is medium \
or high give every question a hint; if target_error is set, at least half of the questions must practise that \
concept and use it as their `concept` tag; instructions must be under 200 characters when instructions='short'."""


def build_request(lesson, params):
    """Privacy-safe payload: grade, subject, topic, objective, metrics, preferences, accommodations."""
    return {
        "subject": lesson.subject, "grade": lesson.grade, "topic": lesson.topic,
        "learning_objective": lesson.objective,
        "question_types": lesson.question_types or ["mcq"],
        "difficulty": params["difficulty"],
        "scaffolding": params["scaffolding"],
        "scaffolding_options": params["scaffolding_options"],
        "visual_support": params["visual_support"],
        "audio_support": params["audio_support"],
        "step_by_step": params["step_by_step"],
        "content_format": params["content_format"],
        "question_count": params["question_count"],
        "target_error": params["target_error"],
        "instructions": params["instructions"],
    }


def generate_activity(request, cfg, feedback=None):
    """Returns (content_dict, source) where source is 'claude' or 'demo'."""
    if cfg.get("ANTHROPIC_API_KEY"):
        try:
            return _call_claude(request, cfg, feedback), "claude"
        except Exception as exc:  # network / parse errors -> fall back so the loop never breaks
            content = _demo_content(request)
            content["_generation_warning"] = f"AI call failed, demo content used: {exc}"
            return content, "demo"
    return _demo_content(request), "demo"


def _call_claude(request, cfg, feedback):
    import anthropic

    client = anthropic.Anthropic(api_key=cfg["ANTHROPIC_API_KEY"])
    user_msg = "Create the activity for these parameters:\n" + json.dumps(request, indent=2)
    if feedback:
        user_msg += "\n\nYour previous attempt failed validation. Fix these issues:\n- " + "\n- ".join(feedback)
    msg = client.messages.create(
        model=cfg["AI_MODEL"], max_tokens=4000, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return parse_json(text)


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in AI response")
    return json.loads(text[start:end + 1])


# ---------------------------------------------------------------- demo generator
_PAIRS = {
    "beginner": [(2, 4), (3, 6), (2, 6), (5, 10), (4, 8)],
    "intermediate": [(2, 3), (3, 4), (4, 6), (3, 5), (2, 5)],
    "advanced": [(5, 6), (4, 7), (6, 9), (3, 8), (7, 10)],
}


def _fmt(fr):
    return f"{fr.numerator}/{fr.denominator}"


def _demo_content(req):
    level = req["difficulty"]
    topic = req["topic"]
    is_fractions = "fraction" in topic.lower()
    rng = random.Random(f"{topic}-{level}-{req['question_count']}-{req.get('target_error')}")
    types = req.get("question_types") or ["mcq"]
    needs_hint = req["scaffolding"] in ("medium", "high")
    questions = []
    fractions_used = []
    for i in range(req["question_count"]):
        qtype = types[i % len(types)]
        if is_fractions:
            d1, d2 = rng.choice(_PAIRS.get(level, _PAIRS["intermediate"]))
            a, c = rng.randint(1, d1 - 1), rng.randint(1, d2 - 1)
            f1, f2 = Fraction(a, d1), Fraction(c, d2)
            fractions_used.append([f"{a}/{d1}", f"{c}/{d2}"])
            answer = _fmt(f1 + f2)
            wrong = {f"{a + c}/{d1 + d2}", _fmt(f1 + f2 + Fraction(1, d1 * d2)), _fmt(abs(f1 - f2) or Fraction(1, 2))}
            wrong.discard(answer)
            options = [answer] + sorted(wrong)[:3]
            rng.shuffle(options)
            q = {"id": f"q{i + 1}", "type": qtype, "prompt": f"What is {a}/{d1} + {c}/{d2}?",
                 "answer": answer, "accepted_answers": [], "concept": "denominator_conversion",
                 "difficulty": level,
                 "hint": "Make the bottom numbers (denominators) the same first." if needs_hint else ""}
            if qtype == "mcq":
                q["options"] = options
            if req["visual_support"]:
                q["visual"] = {"type": "fraction_bars", "description": f"Two bars: {a}/{d1} and {c}/{d2}",
                               "fractions": [f"{a}/{d1}", f"{c}/{d2}"]}
        else:
            q = {"id": f"q{i + 1}", "type": "mcq", "prompt": f"[demo] Question {i + 1} about {topic}",
                 "options": ["Option A", "Option B", "Option C"], "answer": "Option A",
                 "accepted_answers": [], "concept": "general_understanding", "difficulty": level,
                 "hint": "Think about what you learned." if needs_hint else ""}
            if req["visual_support"]:
                q["visual"] = {"type": "diagram", "description": f"Simple picture about {topic}"}
        questions.append(q)

    steps = []
    if req["step_by_step"] or req["scaffolding"] == "high":
        steps = ["Look at the bottom numbers (denominators).", "Change them to the same number.",
                 "Add the top numbers (numerators).", "Write the answer. Make it simple if you can."] \
            if is_fractions else ["Read the question.", "Think about what you know.", "Choose your answer."]
    short = req["instructions"] == "short"
    return {
        "title": f"{topic} ({level})",
        "difficulty": level,
        "instructions": "Read. Answer one at a time." if short else
                        f"Read each question carefully and answer all {req['question_count']} questions.",
        "explanation": {
            "text": f"Today we practise: {req['learning_objective']}",
            "example": "1/2 + 1/4 = 2/4 + 1/4 = 3/4" if is_fractions else f"Example about {topic}.",
            "steps": steps,
            "visual": ({"type": "fraction_bars", "description": "Bars showing 1/2 and 2/4 are equal",
                        "fractions": ["1/2", "2/4"]} if is_fractions else
                       {"type": "diagram", "description": f"Picture about {topic}"})
            if req["visual_support"] else None,
        },
        "questions": questions,
        "_demo": True,
    }
