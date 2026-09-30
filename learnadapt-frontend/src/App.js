import React, { useState } from "react";
import api from "./api";
import Navbar from "./components/Navbar";
import TeacherDashboard from "./components/TeacherDashboard";
import StudentDashboard from "./components/StudentDashboard";

const LOOP = ["Profile", "Learn", "Measure", "Adapt", "Review", "Learn again"];

function Landing({ onLogin }) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-16">
      <h1 className="max-w-3xl text-4xl font-bold leading-tight md:text-5xl">
        Personalized Learning. Continuous Adaptation. Inclusive Classrooms.
      </h1>
      <p className="mt-5 max-w-2xl text-lg text-slate-700">
        LearnAdapt AI helps teachers give every student an activity that fits what they actually did last time.
        Each result feeds the next activity, and you approve it before a student sees it.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <button onClick={() => onLogin("teacher")} className="rounded-md bg-teal-700 px-6 py-3 font-bold text-white hover:bg-teal-800">Login as Teacher</button>
        <button onClick={() => onLogin("student")} className="rounded-md border-2 border-teal-700 px-6 py-3 font-bold text-teal-800 hover:bg-teal-50">Login as Student</button>
      </div>

      <section id="loop" className="mt-20" aria-labelledby="loop-h">
        <h2 id="loop-h" className="mb-6 text-2xl font-bold">The adaptation loop</h2>
        <ol className="flex flex-wrap items-center gap-2">
          {LOOP.map((s, i) => (
            <React.Fragment key={s}>
              <li className={`rounded-full px-5 py-2 font-bold ${i === LOOP.length - 1 ? "bg-amber-200 text-amber-900" : "bg-teal-100 text-teal-900"}`}>{s}</li>
              {i < LOOP.length - 1 && <span aria-hidden className="text-slate-400">→</span>}
            </React.Fragment>
          ))}
        </ol>
        <p className="mt-4 max-w-2xl text-slate-600">
          The last step returns to the first: new results update the student's data and the loop starts again.
        </p>
      </section>

      <section id="accessibility" className="mt-16 max-w-2xl" aria-labelledby="a11y-h">
        <h2 id="a11y-h" className="mb-2 text-2xl font-bold">Built for every learner</h2>
        <p className="text-slate-700">High contrast, large text, dyslexia-friendly font, line spacing and read-aloud are always one click away in the student view.</p>
      </section>
    </main>
  );
}

function Login({ role, onSuccess }) {
  const [form, setForm] = useState({ username: role === "teacher" ? "teacher" : "student1", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const { data } = await api.post("/auth/login", form);
      const user = data.user || data;
      const r = user.role || data.role;
      if (role && r !== role) { setErr(`This account is a ${r} account. Use "Login as ${r === "teacher" ? "Teacher" : "Student"}".`); return; }
      onSuccess({ ...user, id: user.id ?? user.user_id, role: r });
    } catch (ex) {
      setErr(ex.response?.data?.error || "Could not log in. Check your details and that the backend is running on port 5000.");
    } finally { setBusy(false); }
  };

  return (
    <main className="mx-auto max-w-md px-4 py-16">
      <h1 className="mb-6 text-3xl font-bold capitalize">{role || "User"} login</h1>
      <form onSubmit={submit} className="space-y-4 rounded-xl border border-stone-200 bg-white p-6">
        <label className="block">
          <span className="font-bold">Username</span>
          <input className="mt-1 w-full rounded-md border border-slate-300 p-2" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
        </label>
        <label className="block">
          <span className="font-bold">Password</span>
          <input type="password" className="mt-1 w-full rounded-md border border-slate-300 p-2" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
        </label>
        {err && <p role="alert" className="rounded-md bg-red-50 p-2 text-red-800">{err}</p>}
        <button disabled={busy} className="w-full rounded-md bg-teal-700 py-2.5 font-bold text-white hover:bg-teal-800 disabled:opacity-60">
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>
    </main>
  );
}

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [activeView, setActiveView] = useState("landing");
  const [loginRole, setLoginRole] = useState(null);

  const goLogin = (role = null) => { setLoginRole(role); setActiveView("login"); };
  const onSuccess = (u) => { setCurrentUser(u); setActiveView(u.role === "teacher" ? "teacher_dashboard" : "student_dashboard"); };
  const logout = () => { setCurrentUser(null); setActiveView("landing"); };

  return (
    <>
      <Navbar user={currentUser} onHome={() => !currentUser && setActiveView("landing")} onLogin={goLogin} onLogout={logout} />
      {activeView === "landing" && <Landing onLogin={goLogin} />}
      {activeView === "login" && <Login role={loginRole} onSuccess={onSuccess} />}
      {activeView === "teacher_dashboard" && currentUser && <TeacherDashboard user={currentUser} />}
      {activeView === "student_dashboard" && currentUser && <StudentDashboard user={currentUser} />}
    </>
  );
}
