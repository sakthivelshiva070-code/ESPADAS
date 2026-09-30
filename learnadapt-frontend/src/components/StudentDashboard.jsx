import React, { useEffect, useRef, useState } from "react";
import api, { parse } from "../api";
import AccessibilityToolbar, { defaultA11y } from "./AccessibilityToolbar";

export default function StudentDashboard({ user }) {
  const [a11y, setA11y] = useState(defaultA11y);
  const [activity, setActivity] = useState(null);
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stage, setStage] = useState("home"); // home | activity | summary
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState({});
  const [hints, setHints] = useState({});
  const [seconds, setSeconds] = useState(0);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const timer = useRef(null);

  useEffect(() => {
    api.get(`/api/student/activity/${user.id}`)
      .then(({ data }) => {
        const a = data.activity || data;
        if (a && a.id) { setActivity(a); setContent(parse(a.content_json)); }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user.id]);

  useEffect(() => {
    if (stage !== "activity") return;
    timer.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer.current);
  }, [stage]);

  const questions = content?.questions || [];
  const q = questions[idx];
  const readText = stage === "activity" && content
    ? `${content.explanation}. ${content.step_by_step_example || ""}. Question ${idx + 1}. ${q?.question || ""}`
    : "Welcome back. Your next activity is ready.";

  const submit = async () => {
    clearInterval(timer.current);
    const details = questions.map((x) => ({
      question_id: x.id, selected: answers[x.id] ?? null,
      correct: answers[x.id] === x.correct_answer, hint_used: !!hints[x.id],
    }));
    const score = details.filter((d) => d.correct).length;
    const answered = details.filter((d) => d.selected != null).length;
    const local = { score, total: questions.length, accuracy: Math.round((score / questions.length) * 100) };
    try {
      const { data } = await api.post("/api/student/submit-assessment", {
        student_id: user.id, activity_id: activity.id, answers: details,
        score, accuracy: local.accuracy, response_time_sec: seconds,
        completion_rate: Math.round((answered / questions.length) * 100),
      });
      setSummary({ ...local, ...(data.summary || data) });
    } catch {
      setSummary(local);
      setError("Your results could not be saved. Tell your teacher.");
    }
    setStage("summary");
  };

  const wrapStyle = { fontSize: a11y.large ? "1.35rem" : "1.05rem", lineHeight: a11y.spacing };
  const wrapClass = `min-h-screen ${a11y.contrast ? "a11y-contrast" : ""} ${a11y.dyslexia ? "a11y-dyslexia" : ""}`;

  return (
    <div className={wrapClass} style={wrapStyle}>
      <AccessibilityToolbar settings={a11y} onChange={setA11y} readText={readText} />
      <main className="mx-auto max-w-3xl space-y-6 px-4 py-8">
        {stage === "home" && (
          <>
            <h1 className="text-3xl font-bold">Welcome Back!</h1>
            <section className="rounded-xl border border-stone-200 bg-white p-5">
              <h2 className="font-bold">Today's goal</h2>
              <p>{activity?.learning_objective || "Your teacher will assign a goal soon."}</p>
            </section>
            {loading ? <p>Loading…</p> : activity ? (
              <button onClick={() => { setSeconds(0); setStage("activity"); }} className="rounded-md bg-teal-700 px-6 py-3 font-bold text-white hover:bg-teal-800">
                Start: {activity.topic}
              </button>
            ) : <p className="rounded-lg bg-white p-4">No activity yet. Check back after your teacher approves the next one.</p>}
            <p className="text-slate-600">You're making progress. Keep going!</p>
          </>
        )}

        {stage === "activity" && q && (
          <>
            <header className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-600">{activity.topic}</p>
                <h1 className="text-2xl font-bold">Question {idx + 1} of {questions.length}</h1>
              </div>
              <span aria-label="Time spent" className="rounded-full bg-stone-200 px-3 py-1 font-bold">
                {String(Math.floor(seconds / 60)).padStart(2, "0")}:{String(seconds % 60).padStart(2, "0")}
              </span>
            </header>
            <div className="h-2 rounded bg-stone-200" role="progressbar" aria-valuemin={0} aria-valuemax={questions.length} aria-valuenow={idx + 1}>
              <div className="h-2 rounded bg-teal-700" style={{ width: `${((idx + 1) / questions.length) * 100}%` }} />
            </div>

            {idx === 0 && (
              <details open className="rounded-xl border border-stone-200 bg-white p-4">
                <summary className="cursor-pointer font-bold">Explanation</summary>
                <p className="mt-2">{content.explanation}</p>
                {content.step_by_step_example && <p className="mt-2 whitespace-pre-line">{content.step_by_step_example}</p>}
                {content.visual_cue && <p className="mt-2 rounded bg-amber-50 p-2">Picture this: {content.visual_cue}</p>}
              </details>
            )}

            <fieldset className="rounded-xl border border-stone-200 bg-white p-5">
              <legend className="px-1 text-lg font-bold">{q.question}</legend>
              <div className="mt-3 space-y-2">
                {(q.options || []).map((o, i) => {
                  const letter = ["A", "B", "C", "D"][i];
                  const val = /^[A-D]$/.test(q.correct_answer) ? letter : o;
                  return (
                    <label key={i} className={`flex cursor-pointer items-center gap-3 rounded-md border-2 p-3 ${answers[q.id] === val ? "border-teal-700 bg-teal-50" : "border-slate-200"}`}>
                      <input type="radio" name={`q${q.id}`} checked={answers[q.id] === val} onChange={() => setAnswers({ ...answers, [q.id]: val })} className="h-5 w-5" />
                      <span>{letter}. {o}</span>
                    </label>
                  );
                })}
              </div>
            </fieldset>

            <details onToggle={(e) => e.target.open && setHints({ ...hints, [q.id]: true })} className="rounded-md bg-amber-50 p-3">
              <summary className="cursor-pointer font-bold">Need a hint?</summary>
              <p className="mt-1">{q.hint || "Re-read the explanation above."}</p>
            </details>

            <nav className="flex justify-between">
              <button disabled={idx === 0} onClick={() => setIdx(idx - 1)} className="rounded-md border-2 border-slate-300 px-5 py-2 font-bold disabled:opacity-40">Previous</button>
              {idx < questions.length - 1
                ? <button onClick={() => setIdx(idx + 1)} className="rounded-md bg-teal-700 px-5 py-2 font-bold text-white">Next</button>
                : <button onClick={submit} className="rounded-md bg-green-600 px-5 py-2 font-bold text-white">Submit assessment</button>}
            </nav>
          </>
        )}

        {stage === "summary" && summary && (
          <section className="space-y-4">
            <h1 className="text-3xl font-bold">Your results</h1>
            {error && <p role="alert" className="rounded bg-red-50 p-2 text-red-800">{error}</p>}
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-xl bg-white p-4"><div className="text-3xl font-bold">{summary.score}/{summary.total}</div>Score</div>
              <div className="rounded-xl bg-white p-4"><div className="text-3xl font-bold">{summary.accuracy}%</div>Accuracy</div>
              <div className="rounded-xl bg-white p-4"><div className="text-3xl font-bold">{summary.trend || "New"}</div>Trend</div>
            </div>
            <p>Time taken: {Math.floor(seconds / 60)} min {seconds % 60} sec. Your teacher will review the next activity before it appears.</p>
          </section>
        )}
      </main>
    </div>
  );
}
