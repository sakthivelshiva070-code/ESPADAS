import React, { useState } from "react";
import { parse } from "../api";

const Field = ({ label, children }) => (
  <div className="rounded-md bg-stone-100 p-3">
    <div className="text-xs text-slate-500">{label}</div>
    <div className="font-bold">{children}</div>
  </div>
);

export default function AdaptationCard({ activity, onReview }) {
  const p = parse(activity.adaptation_parameters_json);
  const [content, setContent] = useState(() => parse(activity.content_json));
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);

  const mastery = p.mastery ?? activity.mastery ?? p.accuracy;
  const prev = p.previous_score ?? activity.previous_score ?? p.accuracy;
  const errTag = p.target_error || "";
  const name = activity.student_name || `Student ${activity.student_id}`;

  const act = async (action) => {
    setBusy(true);
    try { await onReview(activity.id, action, action === "modify" ? content : undefined); setEditing(false); }
    finally { setBusy(false); }
  };
  const setQ = (i, key, val) =>
    setContent({ ...content, questions: content.questions.map((q, j) => (j === i ? { ...q, [key]: val } : q)) });

  return (
    <article className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-bold">{name}</h3>
          <p className="text-sm text-slate-600">Topic: {activity.topic}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {mastery != null && <span className="rounded-full bg-teal-100 px-3 py-1 font-bold text-teal-900">Mastery {Math.round(mastery)}%</span>}
          {prev != null && <span className="rounded-full bg-stone-100 px-3 py-1">Previous score {Math.round(prev)}%</span>}
          {errTag && <span className="rounded-full bg-red-100 px-3 py-1 font-bold text-red-800">{errTag}</span>}
        </div>
      </header>

      <h4 className="mb-2 mt-4 font-bold">Recommended adaptation</h4>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Field label="Difficulty">{p.difficulty || activity.difficulty}</Field>
        <Field label="Scaffolding">{p.scaffolding || "—"}</Field>
        <Field label="Visual support">{p.visual_support ? "On" : "Off"}</Field>
        <Field label="Questions">{p.question_count ?? content.questions?.length ?? "—"}</Field>
      </div>

      <div className="mt-4 rounded-md border-l-4 border-amber-500 bg-amber-50 p-3">
        <div className="text-sm font-bold text-amber-900">Why this adaptation</div>
        <p className="text-slate-800">{activity.adaptation_reason || p.adaptation_reason || "No reason provided."}</p>
      </div>

      {editing && (
        <div className="mt-4 space-y-3">
          {(content.questions || []).map((q, i) => (
            <div key={q.id ?? i} className="rounded-md border border-slate-200 p-3">
              <label className="text-sm font-bold">Question {i + 1}
                <textarea className="mt-1 w-full rounded border border-slate-300 p-2 font-normal" rows={2} value={q.question} onChange={(e) => setQ(i, "question", e.target.value)} />
              </label>
              <label className="text-sm font-bold">Hint
                <input className="mt-1 w-full rounded border border-slate-300 p-2 font-normal" value={q.hint || ""} onChange={(e) => setQ(i, "hint", e.target.value)} />
              </label>
            </div>
          ))}
        </div>
      )}

      <footer className="mt-5 flex flex-wrap gap-2">
        <button disabled={busy} onClick={() => act(editing ? "modify" : "approve")} className="rounded-md bg-green-600 px-5 py-2 font-bold text-white hover:bg-green-700 disabled:opacity-60">
          {editing ? "Save changes" : "Approve"}
        </button>
        <button disabled={busy} onClick={() => setEditing(!editing)} className="rounded-md bg-yellow-400 px-5 py-2 font-bold text-slate-900 hover:bg-yellow-500">
          {editing ? "Cancel edit" : "Modify"}
        </button>
        <button disabled={busy} onClick={() => act("reject")} className="rounded-md bg-red-600 px-5 py-2 font-bold text-white hover:bg-red-700 disabled:opacity-60">Reject</button>
      </footer>
    </article>
  );
}
