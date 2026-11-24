import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FiCheckSquare, FiEdit3, FiFileText, FiUpload, FiMapPin, FiUsers, FiClock, FiRefreshCw, FiAlertCircle, FiChevronRight,
  FiCheckCircle, FiMessageSquare, FiSend, FiCoffee, FiBookOpen, FiLayers,
} from "react-icons/fi";
import api from "../services/api";
import { format12h } from "../utils/schedule";

const REFRESH_MS = 60_000;

// Where each outstanding-work item leads (existing Faculty pages). A subject is pre-selected only when exactly one subject is involved.
const TASK_META = {
  attendance: { icon: FiCheckSquare, tone: "danger", path: "/faculty/attendance", scoped: true },
  marks_to_enter: { icon: FiEdit3, tone: "warning", path: "/faculty/marks", scoped: true },
  marks_to_publish: { icon: FiSend, tone: "primary", path: "/faculty/marks", scoped: true },
  submissions_to_review: { icon: FiFileText, tone: "secondary", path: "/faculty/assignments", scoped: false },
  doubts_unanswered: { icon: FiMessageSquare, tone: "secondary", path: "/faculty/doubt-wall", scoped: false },
};
const TONES = {
  danger: "bg-danger/10 text-danger", warning: "bg-warning/10 text-warning",
  primary: "bg-primary/10 text-primary", secondary: "bg-secondary/10 text-secondary",
};

const QUICK = [
  { label: "Mark Attendance", hint: "Take today's roll", path: "/faculty/attendance", icon: FiCheckSquare },
  { label: "Enter Marks", hint: "Record & publish", path: "/faculty/marks", icon: FiEdit3 },
  { label: "Manage Assignments", hint: "Create & grade", path: "/faculty/assignments", icon: FiFileText },
  { label: "Upload Study Material", hint: "Share notes", path: "/faculty/notes?upload=1", icon: FiUpload },
];

const hours = (mins) => (mins >= 60 ? `${Math.floor(mins / 60)}h${mins % 60 ? ` ${mins % 60}m` : ""}` : `${mins}m`);
const longDate = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

function classState(c) {
  if (c.ended) return "completed";
  if (c.started) return "live";
  return "upcoming";
}

const STATE_STYLE = {
  live: { label: "Live now", badge: "bg-success/15 text-success", rail: "bg-success" },
  upcoming: { label: "Upcoming", badge: "bg-primary/10 text-primary", rail: "bg-primary" },
  completed: { label: "Completed", badge: "bg-slate-100 dark:bg-white/10 text-slate-500 dark:text-slate-400", rail: "bg-slate-300 dark:bg-white/20" },
};

function AttendancePill({ attendance, started }) {
  const { status, marked, enrolled } = attendance;
  if (status === "complete") return <span className="text-[11px] px-2 py-0.5 rounded-full bg-success/10 text-success font-medium inline-flex items-center gap-1"><FiCheckCircle size={11} /> Attendance marked</span>;
  if (status === "partial") return <span className="text-[11px] px-2 py-0.5 rounded-full bg-warning/10 text-warning font-medium">Marked {marked}/{enrolled}</span>;
  if (status === "no_students") return <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-white/10 text-slate-500 font-medium">No students enrolled</span>;
  return <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${started ? "bg-danger/10 text-danger" : "bg-slate-100 dark:bg-white/10 text-slate-500 dark:text-slate-400"}`}>Attendance not marked</span>;
}

function ClassRow({ c }) {
  const state = classState(c);
  const style = STATE_STYLE[state];
  const r = c.readiness;
  const done = c.attendance.status === "complete";
  return (
    <li className={`group relative flex gap-3 rounded-2xl border p-3.5 transition-all duration-200 motion-reduce:transition-none hover:-translate-y-0.5 hover:shadow-lg hover:shadow-primary/5 ${
      state === "live" ? "border-success/30 bg-success/5" : "border-slate-100 dark:border-white/10 bg-white/60 dark:bg-white/5"
    } ${state === "completed" ? "opacity-80" : ""}`}>
      <span className={`absolute left-0 top-3 bottom-3 w-1 rounded-r-full ${style.rail} ${state === "live" ? "animate-pulse motion-reduce:animate-none" : ""}`} aria-hidden="true" />
      <div className="w-[68px] shrink-0 pl-2 text-center">
        <p className="text-sm font-display font-bold leading-tight">{format12h(c.start_time)}</p>
        <p className="text-[11px] text-slate-400 mt-0.5">to {format12h(c.end_time)}</p>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <p className="font-medium truncate">{c.subject_name}</p>
          {c.subject_code && <span className="text-[11px] text-slate-400">{c.subject_code}</span>}
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${style.badge}`}>{style.label}</span>
        </div>
        <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-slate-500 dark:text-slate-400">
          <span className="inline-flex items-center gap-1"><FiLayers size={11} /> Lecture {c.lecture} of {c.lectures_today}</span>
          <span className="inline-flex items-center gap-1"><FiMapPin size={11} /> {c.classroom}</span>
          <span className="inline-flex items-center gap-1"><FiUsers size={11} /> {c.enrolled_students} students</span>
          <span>{c.department} · Sem {c.semester}</span>
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <AttendancePill attendance={c.attendance} started={c.started} />
          {state !== "completed" && (
            <>
              <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${r.notes_uploaded ? "bg-primary/10 text-primary" : "bg-warning/10 text-warning"}`}>
                {r.notes_uploaded ? `${r.notes_uploaded} study material${r.notes_uploaded === 1 ? "" : "s"}` : "No study material yet"}
              </span>
              {r.open_assignments > 0 && <span className="text-[11px] px-2 py-0.5 rounded-full bg-secondary/10 text-secondary font-medium">{r.open_assignments} open assignment{r.open_assignments === 1 ? "" : "s"}</span>}
            </>
          )}
          {r.submissions_to_review > 0 && <span className="text-[11px] px-2 py-0.5 rounded-full bg-secondary/10 text-secondary font-medium">{r.submissions_to_review} to review</span>}
        </div>
      </div>
      <Link
        to={`/faculty/attendance?subject=${c.subject_id}`}
        className={`self-center shrink-0 text-xs font-semibold px-3 py-2 rounded-xl transition-all ${
          done ? "text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10" : "bg-gradient-to-r from-primary to-secondary text-white shadow-glow hover:brightness-110"
        }`}
      >
        {done ? "Review" : "Mark attendance"}
      </Link>
    </li>
  );
}

function Skeleton() {
  return (
    <div className="grid lg:grid-cols-12 gap-5 p-5 animate-pulse motion-reduce:animate-none" aria-busy="true" aria-label="Loading your classroom activity">
      <div className="lg:col-span-7 space-y-3">{[0, 1, 2].map((i) => <div key={i} className="h-24 rounded-2xl bg-slate-100 dark:bg-white/10" />)}</div>
      <div className="lg:col-span-5 space-y-3"><div className="h-40 rounded-2xl bg-slate-100 dark:bg-white/10" /><div className="h-28 rounded-2xl bg-slate-100 dark:bg-white/10" /></div>
    </div>
  );
}

export default function ClassroomActivityHub() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const alive = useRef(true);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true); else setRefreshing(true);
    try {
      const { data: result } = await api.get("/faculty/me/activity-hub");
      if (!alive.current) return;
      setData(result);
      setError("");
    } catch (err) {
      if (!alive.current) return;
      setError(!err.response ? "Can't reach the server." : typeof err.response.data?.detail === "string" ? err.response.data.detail : "Couldn't load your classroom activity.");
    } finally {
      if (alive.current) { setLoading(false); setRefreshing(false); }
    }
  }, []);

  // Fresh on open, every minute, and whenever the tab regains focus — so counts drop as soon as work is done on another page.
  useEffect(() => {
    alive.current = true;
    load();
    const tick = () => { if (document.visibilityState === "visible") load(true); };
    const timer = setInterval(tick, REFRESH_MS);
    document.addEventListener("visibilitychange", tick);
    window.addEventListener("focus", tick);
    return () => { alive.current = false; clearInterval(timer); document.removeEventListener("visibilitychange", tick); window.removeEventListener("focus", tick); };
  }, [load]);

  const s = data?.summary;
  const hasSubjects = (data?.assigned_subjects || 0) > 0;
  const openTasks = (data?.tasks || []).filter((t) => t.count > 0);

  const openTask = (t) => {
    const meta = TASK_META[t.key];
    const single = meta.scoped && t.breakdown.length === 1 ? `?subject=${t.breakdown[0].subject_id}` : "";
    navigate(`${meta.path}${single}`);
  };

  return (
    <section className="glass-card overflow-hidden" aria-labelledby="hub-title">
      <div className="relative px-5 py-4 border-b border-slate-100 dark:border-white/10 bg-gradient-to-r from-primary/10 via-secondary/5 to-transparent">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="hub-title" className="font-display font-semibold text-lg leading-tight">Classroom Activity Hub</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">{data ? longDate(data.date) : "Your teaching day at a glance"}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {s && (
              <>
                <span className="text-xs px-2.5 py-1 rounded-full bg-white/70 dark:bg-white/10 border border-slate-100 dark:border-white/10"><b>{s.classes_today}</b> class{s.classes_today === 1 ? "" : "es"} today</span>
                {s.teaching_minutes_today > 0 && <span className="text-xs px-2.5 py-1 rounded-full bg-white/70 dark:bg-white/10 border border-slate-100 dark:border-white/10 inline-flex items-center gap-1"><FiClock size={11} /> {hours(s.teaching_minutes_today)} teaching</span>}
                {s.students_today > 0 && <span className="text-xs px-2.5 py-1 rounded-full bg-white/70 dark:bg-white/10 border border-slate-100 dark:border-white/10 inline-flex items-center gap-1"><FiUsers size={11} /> {s.students_today} students</span>}
              </>
            )}
            <button type="button" onClick={() => load(true)} aria-label="Refresh classroom activity" title="Refresh" className="p-2 rounded-lg hover:bg-white/70 dark:hover:bg-white/10 text-slate-500">
              <FiRefreshCw size={14} className={refreshing || loading ? "animate-spin" : ""} />
            </button>
          </div>
        </div>
      </div>

      {loading && !data ? <Skeleton /> : error && !data ? (
        <div role="alert" className="flex flex-col items-center gap-2 py-12 text-center">
          <FiAlertCircle className="text-danger" size={24} />
          <p className="text-sm text-danger">{error}</p>
          <button type="button" onClick={() => load()} className="btn-secondary !py-1.5 text-sm">Retry</button>
        </div>
      ) : data && (
        <div className="p-5">
          {error && <p role="alert" className="mb-3 text-xs text-warning">Showing the last loaded data — couldn't refresh ({error}).</p>}
          <div className="grid lg:grid-cols-12 gap-5">
            <div className="lg:col-span-7">
              <p className="text-sm font-display font-semibold mb-3">Today's classes</p>
              {data.classes.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 dark:border-white/15 px-6 py-10 text-center">
                  <span className="mx-auto mb-3 w-12 h-12 rounded-2xl bg-gradient-to-br from-primary/15 to-secondary/15 text-primary flex items-center justify-center"><FiCoffee size={22} /></span>
                  <p className="font-medium">{hasSubjects ? "No classes scheduled today" : "No subjects assigned yet"}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xs mx-auto">
                    {hasSubjects
                      ? "A good day to catch up on marking, upload study material, or plan upcoming assignments."
                      : "Once your Admin assigns subjects, your classes and tasks will appear here."}
                  </p>
                  {hasSubjects && (
                    <div className="mt-4 flex flex-wrap justify-center gap-2">
                      <Link to="/faculty/notes?upload=1" className="btn-secondary !py-1.5 text-xs inline-flex items-center gap-1.5"><FiBookOpen size={12} /> Upload material</Link>
                      <Link to="/faculty/assignments?new=1" className="btn-secondary !py-1.5 text-xs inline-flex items-center gap-1.5"><FiFileText size={12} /> New assignment</Link>
                    </div>
                  )}
                </div>
              ) : (
                <ul className="space-y-2.5">{data.classes.map((c) => <ClassRow key={c.slot_id} c={c} />)}</ul>
              )}
            </div>

            <div className="lg:col-span-5 space-y-5">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-display font-semibold">Pending tasks</p>
                  {s.tasks_outstanding > 0 && <span className="text-[11px] px-2 py-0.5 rounded-full bg-danger/10 text-danger font-semibold">{s.tasks_outstanding} outstanding</span>}
                </div>
                {openTasks.length === 0 ? (
                  <div className="rounded-2xl bg-success/10 px-4 py-5 flex items-center gap-3">
                    <FiCheckCircle className="text-success shrink-0" size={20} />
                    <div><p className="text-sm font-medium text-success">You're all caught up</p><p className="text-xs text-slate-500 dark:text-slate-400">No attendance, marks, reviews or doubts waiting.</p></div>
                  </div>
                ) : (
                  <ul className="space-y-2">
                    {openTasks.map((t) => {
                      const meta = TASK_META[t.key];
                      const Icon = meta.icon;
                      return (
                        <li key={t.key}>
                          <button type="button" onClick={() => openTask(t)} className="group w-full text-left flex items-center gap-3 rounded-xl border border-slate-100 dark:border-white/10 bg-white/60 dark:bg-white/5 px-3 py-2.5 transition-all duration-200 motion-reduce:transition-none hover:-translate-y-0.5 hover:shadow-md hover:border-primary/30">
                            <span className={`w-9 h-9 shrink-0 rounded-xl flex items-center justify-center ${TONES[meta.tone]}`}><Icon size={16} /></span>
                            <span className="min-w-0 flex-1">
                              <span className="block text-sm font-medium">{t.label}</span>
                              <span className="block text-[11px] text-slate-500 dark:text-slate-400 truncate">{t.breakdown.map((b) => `${b.subject_name} · ${b.count}`).join("  ·  ")}</span>
                            </span>
                            <span className={`min-w-[1.75rem] text-center text-sm font-display font-bold px-2 py-0.5 rounded-lg ${TONES[meta.tone]}`}>{t.count}</span>
                            <FiChevronRight className="text-slate-300 group-hover:text-primary" size={16} />
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              <div>
                <p className="text-sm font-display font-semibold mb-3">Quick actions</p>
                <div className="grid grid-cols-2 gap-2.5">
                  {QUICK.map((q) => {
                    const Icon = q.icon;
                    return hasSubjects ? (
                      <Link key={q.label} to={q.path} className="rounded-xl border border-slate-100 dark:border-white/10 bg-white/60 dark:bg-white/5 p-3 transition-all duration-200 motion-reduce:transition-none hover:-translate-y-0.5 hover:shadow-md hover:border-primary/30">
                        <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary text-white flex items-center justify-center mb-2"><Icon size={14} /></span>
                        <span className="block text-sm font-medium leading-tight">{q.label}</span>
                        <span className="block text-[11px] text-slate-400">{q.hint}</span>
                      </Link>
                    ) : (
                      <div key={q.label} aria-disabled="true" title="Available once subjects are assigned to you" className="rounded-xl border border-slate-100 dark:border-white/10 p-3 opacity-50 cursor-not-allowed">
                        <span className="w-8 h-8 rounded-lg bg-slate-200 dark:bg-white/10 text-slate-500 flex items-center justify-center mb-2"><Icon size={14} /></span>
                        <span className="block text-sm font-medium leading-tight">{q.label}</span>
                        <span className="block text-[11px] text-slate-400">No subjects assigned</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          {hasSubjects && (
            <div className="mt-5 pt-4 border-t border-slate-100 dark:border-white/10 grid sm:grid-cols-3 gap-3">
              <div className="rounded-xl bg-slate-50 dark:bg-white/5 px-4 py-3">
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Attendance today</p>
                {s.attendance_subjects_started === 0 ? (
                  <p className="text-sm font-medium mt-1 text-slate-400">No classes started yet</p>
                ) : (
                  <>
                    <p className="text-sm font-display font-bold mt-1">{s.attendance_subjects_done} of {s.attendance_subjects_started} subject{s.attendance_subjects_started === 1 ? "" : "s"} marked</p>
                    <div className="mt-1.5 h-1.5 rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden"><div className="h-full rounded-full bg-gradient-to-r from-primary to-secondary transition-all duration-500" style={{ width: `${(s.attendance_subjects_done / s.attendance_subjects_started) * 100}%` }} /></div>
                  </>
                )}
              </div>
              <div className="rounded-xl bg-slate-50 dark:bg-white/5 px-4 py-3">
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Assignments due this week</p>
                <p className="text-sm font-display font-bold mt-1">{s.assignments_due_this_week}</p>
              </div>
              <div className="rounded-xl bg-slate-50 dark:bg-white/5 px-4 py-3">
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Outstanding tasks</p>
                <p className={`text-sm font-display font-bold mt-1 ${s.tasks_outstanding ? "text-danger" : "text-success"}`}>{s.tasks_outstanding === 0 ? "None — all clear" : s.tasks_outstanding}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
