import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip } from "chart.js";
import { FiRefreshCw, FiAlertCircle, FiTrendingUp, FiCheckCircle, FiXCircle, FiUsers, FiInfo } from "react-icons/fi";
import api from "../services/api";

ChartJS.register(ArcElement, Tooltip);

// One colour per grade band (best → worst); matches the app's violet/fuchsia theme with semantic ends.
const GRADE_COLORS = { "A+": "#16A34A", A: "#4ADE80", B: "#6D4AFF", C: "#A78BFA", D: "#F59E0B", E: "#FB923C", F: "#EF4444" };
const REFRESH_MS = 60_000;

const fmt = (n, suffix = "") => (n === null || n === undefined ? "—" : `${n}${suffix}`);
const time = (d) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function Metric({ icon: Icon, label, value, hint, tone = "primary" }) {
  const tones = {
    primary: "bg-primary/10 text-primary", success: "bg-success/10 text-success",
    danger: "bg-danger/10 text-danger", secondary: "bg-secondary/10 text-secondary",
  };
  return (
    <div className="rounded-xl border border-slate-100 dark:border-white/10 bg-white/60 dark:bg-white/5 p-3">
      <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
        <span className={`w-6 h-6 rounded-lg flex items-center justify-center ${tones[tone]}`}><Icon size={13} /></span>
        {label}
      </div>
      <p className="mt-1.5 text-xl font-display font-bold leading-none">{value}</p>
      {hint && <p className="mt-1 text-[11px] text-slate-400">{hint}</p>}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="grid lg:grid-cols-12 gap-4 animate-pulse" aria-busy="true" aria-label="Loading student performance">
      <div className="lg:col-span-4 grid grid-cols-2 gap-3">{[0, 1, 2, 3].map((i) => <div key={i} className="h-20 rounded-xl bg-slate-100 dark:bg-white/10" />)}</div>
      <div className="lg:col-span-4 h-44 rounded-xl bg-slate-100 dark:bg-white/10" />
      <div className="lg:col-span-4 h-44 rounded-xl bg-slate-100 dark:bg-white/10" />
    </div>
  );
}

export default function StudentPerformance({ subjects = [] }) {
  const [filters, setFilters] = useState({ department: "", semester: "", subjectId: "", publishedOnly: false });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState(null);
  const requestId = useRef(0);

  const departments = useMemo(() => [...new Set(subjects.map((s) => s.department))].sort(), [subjects]);
  const semesters = useMemo(() => [...new Set(subjects.filter((s) => !filters.department || s.department === filters.department).map((s) => s.semester))].sort((a, b) => a - b), [subjects, filters.department]);
  const subjectOptions = useMemo(
    () => subjects.filter((s) => (!filters.department || s.department === filters.department) && (!filters.semester || s.semester === Number(filters.semester))),
    [subjects, filters.department, filters.semester]
  );

  const load = useCallback(async (silent = false) => {
    const id = ++requestId.current;
    if (!silent) setLoading(true);
    try {
      const params = {};
      if (filters.department) params.department = filters.department;
      if (filters.semester) params.semester = filters.semester;
      if (filters.subjectId) params.subject_id = filters.subjectId;
      if (filters.publishedOnly) params.published_only = true;
      const { data: result } = await api.get("/analytics/student-performance", { params });
      if (id !== requestId.current) return;   // a newer request superseded this one
      setData(result);
      setError("");
      setUpdatedAt(new Date());
    } catch (err) {
      if (id !== requestId.current) return;
      if (!silent || !data) {
        setError(!err.response ? "Can't reach the server." : (typeof err.response.data?.detail === "string" ? err.response.data.detail : "Couldn't load student performance."));
      }
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [filters]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load on mount / filter change; keep fresh so newly entered or published marks show up.
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const tick = () => { if (document.visibilityState === "visible") load(true); };
    const timer = setInterval(tick, REFRESH_MS);
    document.addEventListener("visibilitychange", tick);
    return () => { clearInterval(timer); document.removeEventListener("visibilitychange", tick); };
  }, [load]);

  const setFilter = (patch) => setFilters((f) => {
    const next = { ...f, ...patch };
    if ("department" in patch) { next.semester = ""; next.subjectId = ""; }
    if ("semester" in patch) next.subjectId = "";
    return next;
  });

  const s = data?.summary;
  const dist = data?.grade_distribution || [];
  const hasData = !!s && s.students_eligible > 0;
  const q = data?.data_quality;
  const ignored = q ? q.duplicates_ignored + q.invalid_ignored : 0;

  const chart = {
    labels: dist.map((d) => d.grade),
    datasets: [{ data: dist.map((d) => d.count), backgroundColor: dist.map((d) => GRADE_COLORS[d.grade]), borderWidth: 0, hoverOffset: 4 }],
  };
  const chartOptions = {
    cutout: "68%", responsive: true, maintainAspectRatio: true,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (c) => { const d = dist[c.dataIndex]; return ` ${d.grade} (${d.label}): ${d.count} student${d.count === 1 ? "" : "s"} · ${d.percentage}%`; } } },
    },
  };

  const selectCls = "input-field !py-1.5 !px-2.5 !text-xs w-auto max-w-[170px]";

  return (
    <section className="glass-card p-5" aria-labelledby="perf-title">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <h2 id="perf-title" className="font-display font-semibold">Student performance analytics</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Live from recorded marks{updatedAt ? ` · updated ${time(updatedAt)}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select aria-label="Department" className={selectCls} value={filters.department} onChange={(e) => setFilter({ department: e.target.value })}>
            <option value="">All departments</option>
            {departments.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <select aria-label="Semester" className={selectCls} value={filters.semester} onChange={(e) => setFilter({ semester: e.target.value })}>
            <option value="">All semesters</option>
            {semesters.map((n) => <option key={n} value={n}>Semester {n}</option>)}
          </select>
          <select aria-label="Subject" className={selectCls} value={filters.subjectId} onChange={(e) => setFilter({ subjectId: e.target.value })}>
            <option value="">All subjects</option>
            {subjectOptions.map((sj) => <option key={sj.id} value={sj.id}>{sj.name}</option>)}
          </select>
          <label className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 cursor-pointer select-none">
            <input type="checkbox" className="rounded border-slate-300 text-primary focus:ring-primary" checked={filters.publishedOnly} onChange={(e) => setFilter({ publishedOnly: e.target.checked })} />
            Published only
          </label>
          <button type="button" onClick={() => load()} aria-label="Refresh analytics" title="Refresh" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 text-slate-500">
            <FiRefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {loading && !data ? <Skeleton /> : error && !data ? (
        <div role="alert" className="flex flex-col items-center gap-2 py-8 text-center">
          <FiAlertCircle className="text-danger" size={22} />
          <p className="text-sm text-danger">{error}</p>
          <button type="button" onClick={() => load()} className="btn-secondary !py-1.5 text-sm">Retry</button>
        </div>
      ) : s && (
        <>
          {error && <p role="alert" className="mb-3 text-xs text-warning">Showing the last loaded figures — couldn't refresh ({error}).</p>}
          {!hasData ? (
            <div className="py-8 text-center">
              <FiTrendingUp className="mx-auto text-slate-300 dark:text-slate-600 mb-2" size={26} />
              <p className="text-sm font-medium">No valid marks to analyse yet</p>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                {s.students_total > 0
                  ? `${s.students_total} student${s.students_total === 1 ? " is" : "s are"} in this selection, but none has enough marks recorded. Figures appear as faculty enter marks.`
                  : "No students match this selection."}
              </p>
            </div>
          ) : (
            <div className="grid lg:grid-cols-12 gap-4">
              <div className="lg:col-span-4 grid grid-cols-2 gap-3 content-start">
                <Metric icon={FiTrendingUp} label="Average marks" value={fmt(s.average_percentage, "%")} hint={`across ${s.students_eligible} student${s.students_eligible === 1 ? "" : "s"}`} />
                <Metric icon={FiCheckCircle} tone="success" label="Pass rate" value={fmt(s.pass_rate, "%")} hint={`pass mark ${data.config.pass_percentage}%`} />
                <Metric icon={FiCheckCircle} tone="success" label="Passed" value={s.pass_count} hint={`${fmt(s.pass_rate, "%")} of eligible`} />
                <Metric icon={FiXCircle} tone="danger" label="Failed" value={s.fail_count} hint={`${fmt(s.fail_rate, "%")} of eligible`} />
                <div className="col-span-2 flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400 px-1">
                  <FiUsers size={12} /> {s.students_eligible} of {s.students_total} students counted
                  {s.students_insufficient_data > 0 && <span>· {s.students_insufficient_data} awaiting marks (not counted as fails)</span>}
                </div>
              </div>

              <div className="lg:col-span-4 flex items-center gap-4">
                <div className="relative w-36 shrink-0" role="img" aria-label={`Grade distribution of ${s.students_eligible} students`}>
                  <Doughnut data={chart} options={chartOptions} />
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-xl font-display font-bold leading-none">{s.students_eligible}</span>
                    <span className="text-[10px] text-slate-400">students</span>
                  </div>
                </div>
                <ul className="flex-1 space-y-1 text-xs min-w-0">
                  {dist.map((d) => (
                    <li key={d.grade} className="flex items-center gap-2" title={`${d.label} (${d.min}% and above)`}>
                      <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: GRADE_COLORS[d.grade] }} />
                      <span className="font-semibold w-6">{d.grade}</span>
                      <span className="text-slate-500 dark:text-slate-400 tabular-nums">{d.count}</span>
                      <span className="ml-auto text-slate-400 tabular-nums">{d.percentage}%</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="lg:col-span-4 space-y-4">
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="font-medium">Pass / fail</span>
                    <span className="text-slate-400">{s.pass_count} / {s.fail_count}</span>
                  </div>
                  <div className="flex h-2.5 rounded-full overflow-hidden bg-slate-100 dark:bg-white/10" role="img" aria-label={`${s.pass_rate}% passed, ${s.fail_rate}% failed`}>
                    <div className="bg-success" style={{ width: `${s.pass_rate}%` }} />
                    <div className="bg-danger" style={{ width: `${s.fail_rate}%` }} />
                  </div>
                </div>

                <div>
                  <p className="text-xs font-medium mb-1.5">Average by subject</p>
                  {data.by_subject.length === 0 ? <p className="text-xs text-slate-400">No subject averages yet.</p> : (
                    <ul className="space-y-1.5 max-h-28 overflow-y-auto pr-1">
                      {data.by_subject.map((b) => (
                        <li key={b.subject_id} className="text-xs" title={`${b.students_count} student${b.students_count === 1 ? "" : "s"}`}>
                          <div className="flex justify-between"><span className="truncate pr-2">{b.name}</span><span className="tabular-nums text-slate-500">{b.average_percentage}%</span></div>
                          <div className="h-1.5 rounded-full bg-slate-100 dark:bg-white/10"><div className="h-full rounded-full bg-gradient-to-r from-primary to-secondary" style={{ width: `${Math.min(100, b.average_percentage)}%` }} /></div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}

          <details className="mt-4 text-[11px] text-slate-400">
            <summary className="cursor-pointer inline-flex items-center gap-1 select-none"><FiInfo size={11} /> How these figures are calculated</summary>
            <p className="mt-1.5 max-w-3xl">
              {data.config.method} Pass mark {data.config.pass_percentage}% (set with PASS_PERCENTAGE on the server). Grades:{" "}
              {data.config.grade_bands.map((b) => `${b.grade} ≥${b.min}%`).join(", ")}.
              {ignored > 0 && ` ${q.duplicates_ignored} duplicate and ${q.invalid_ignored} invalid mark record(s) were ignored.`}
              {q?.unpublished_included > 0 && ` Includes ${q.unpublished_included} unpublished (draft) record(s) — tick "Published only" to exclude them.`}
            </p>
          </details>
        </>
      )}
    </section>
  );
}
