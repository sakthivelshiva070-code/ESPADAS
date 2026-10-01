import React, { useCallback, useEffect, useState } from "react";
import api, { asList } from "../api";
import AdaptationCard from "./AdaptationCard";

const Stat = ({ label, value }) => (
  <div className="rounded-xl border border-stone-200 bg-white p-4">
    <div className="text-3xl font-bold text-teal-800">{value}</div>
    <div className="text-sm text-slate-600">{label}</div>
  </div>
);

export default function TeacherDashboard({ user }) {
  const [stats, setStats] = useState({});
  const [pending, setPending] = useState([]);
  const [form, setForm] = useState({ subject: "Mathematics", grade: 8, topic: "", objective: "" });
  const [msg, setMsg] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
  if (!user || !user.id) return; // Prevent invalid requests if user isn't loaded yet
  try {
    const [d, p] = await Promise.all([
      api.get(`/teacher/dashboard/${user.id}`),
      api.get(`/teacher/pending-adaptations/${user.id}`),
    ]);
    setStats(d.data.stats || d.data);
    setPending(asList(p.data));
  } catch { 
    setMsg("Could not load dashboard data. Is the backend running?"); 
  }
}, [user]);

  useEffect(() => { load(); }, [load]);

  const create = async (e) => {
    e.preventDefault();
    setCreating(true); setMsg("");
    try {
      await api.post("/lessons/create", {
        teacher_id: user.id, subject: form.subject, grade: Number(form.grade),
        topic: form.topic, objective: form.objective, learning_objective: form.objective,
      });
      setForm({ ...form, topic: "", objective: "" });
      setMsg("Lesson created. Review the adaptation below.");
      load();
    } catch (ex) { setMsg(ex.response?.data?.error || "Could not create the lesson."); }
    finally { setCreating(false); }
  };

  const review = async (activity_id, action, content) => {
    await api.post("/teacher/review-adaptation", { activity_id, action, ...(content ? { content_json: JSON.stringify(content) } : {}) });
    load();
  };

  const attention = stats.students_needing_attention || stats.attention || [];
  const pendingCount = stats.pending_reviews ?? pending.length;

  return (
    <main className="mx-auto max-w-6xl space-y-10 px-4 py-8">
      <section>
        <h1 className="mb-4 text-3xl font-bold">Good Morning, Teacher</h1>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label="Today's Classes" value={stats.todays_classes ?? stats.classes ?? 3} />
          <Stat label="Students" value={stats.total_students ?? stats.students ?? 84} />
          <Stat label="Pending Reviews" value={pendingCount} />
          <Stat label="Attention Needed" value={attention.length || stats.attention_count || 3} />
        </div>
      </section>

      <section aria-labelledby="att">
        <h2 id="att" className="mb-3 text-xl font-bold">Students needing attention</h2>
        <ul className="space-y-2">
          {(attention.length ? attention : [{ name: "Student C", topic: "Fractions", mastery: 48, error: "Denominator Conversion Error" }]).map((s, i) => (
            <li key={i} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border-l-4 border-red-500 bg-white p-3">
              <span className="font-bold">{s.name || s.username || `Student ${s.student_id}`}</span>
              <span className="text-slate-700">{s.topic} · {s.mastery ?? s.accuracy}% · {s.error || s.repeated_errors}</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="create">
        <h2 id="create" className="mb-3 text-xl font-bold">Create a core lesson</h2>
        <form onSubmit={create} className="grid gap-3 rounded-xl border border-stone-200 bg-white p-5 md:grid-cols-2">
          {[["Subject", "subject"], ["Grade", "grade"], ["Topic", "topic"]].map(([l, k]) => (
            <label key={k} className="font-bold">{l}
              <input required type={k === "grade" ? "number" : "text"} className="mt-1 w-full rounded-md border border-slate-300 p-2 font-normal" value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
            </label>
          ))}
          <label className="font-bold md:col-span-2">Learning objective
            <textarea required rows={2} className="mt-1 w-full rounded-md border border-slate-300 p-2 font-normal" value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })} />
          </label>
          <div className="md:col-span-2">
            <button disabled={creating} className="rounded-md bg-teal-700 px-5 py-2.5 font-bold text-white hover:bg-teal-800 disabled:opacity-60">
              {creating ? "Generating…" : "Create lesson"}
            </button>
            {msg && <span role="status" className="ml-3 text-slate-700">{msg}</span>}
          </div>
        </form>
      </section>

      <section aria-labelledby="pend">
        <h2 id="pend" className="mb-3 text-xl font-bold">Pending adaptations ({pending.length})</h2>
        {pending.length === 0 ? (
          <p className="rounded-lg bg-white p-4 text-slate-600">Nothing to review. Create a lesson or wait for a student to submit an assessment.</p>
        ) : (
          <div className="space-y-4">{pending.map((a) => <AdaptationCard key={a.id} activity={a} onReview={review} />)}</div>
        )}
      </section>
    </main>
  );
}
