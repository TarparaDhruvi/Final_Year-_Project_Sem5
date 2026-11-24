import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  FiChevronLeft, FiChevronRight, FiFileText, FiAward, FiCalendar, FiBookOpen, FiClock, FiMapPin, FiAlertCircle, FiArrowRight, FiSun,
} from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import { format12h } from "../../utils/schedule";

// One entry per event type. A type is only shown (legend/filter) when the user's own data actually contains it.
const TYPE_META = {
  lecture: { label: "Lectures", dot: "bg-primary", chip: "bg-primary/10 text-primary", icon: FiClock },
  assignment: { label: "Deadlines", dot: "bg-warning", chip: "bg-warning/10 text-warning", icon: FiFileText },
  exam: { label: "Exams", dot: "bg-danger", chip: "bg-danger/10 text-danger", icon: FiAward },
  study_session: { label: "Study sessions", dot: "bg-accent", chip: "bg-accent/15 text-cyan-700 dark:text-accent", icon: FiBookOpen },
  leave: { label: "Leave", dot: "bg-secondary", chip: "bg-secondary/10 text-secondary", icon: FiCalendar },
};
const TYPE_ORDER = ["lecture", "assignment", "exam", "study_session", "leave"];
const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const WEEKDAY_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

const pad = (n) => String(n).padStart(2, "0");
const toKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const fromKey = (k) => { const [y, m, d] = k.split("-").map(Number); return new Date(y, m - 1, d); };
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };

/** Always 6 full weeks (Sunday-first, like the previous calendar) so the grid never jumps height between months. */
function buildGrid(year, month) {
  const first = new Date(year, month, 1);
  const start = addDays(first, -first.getDay());
  return Array.from({ length: 42 }, (_, i) => addDays(start, i));
}

// Where each kind of item is acted on (existing pages only).
const linkFor = (type, role) => {
  if (type === "assignment") return role === "faculty" ? "/faculty/assignments" : role === "student" ? "/student/assignments" : null;
  if (type === "lecture") return role === "faculty" ? "/faculty/schedule" : role === "student" ? "/student/schedule" : null;
  if (type === "exam" || type === "study_session") return role === "student" ? "/student/study-coach" : null;
  if (type === "leave") return role === "admin" ? "/admin/leave" : role === "faculty" ? "/faculty/leave" : "/student/leave";
  return null;
};

export default function SmartCalendar() {
  const { user } = useAuth();
  const role = user?.role;
  const [events, setEvents] = useState([]);
  const [weekly, setWeekly] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const todayKey = toKey(new Date());
  const [selectedKey, setSelectedKey] = useState(todayKey);
  const [cursor, setCursor] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const [hidden, setHidden] = useState(() => new Set());
  const cellRefs = useRef({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/calendar/me");
      setEvents(data.events || []);
      setWeekly(data.weekly_classes || []);
      setError("");
    } catch (err) {
      setError(!err.response ? "Can't reach the server." : "Couldn't load your calendar.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const cells = useMemo(() => buildGrid(cursor.getFullYear(), cursor.getMonth()), [cursor]);

  // Everything dated, per day of the visible grid: dated events (leave spans expanded) + the user's weekly lectures.
  const itemsByDate = useMemo(() => {
    const map = {};
    const push = (key, item) => { (map[key] = map[key] || []).push(item); };
    const gridKeys = new Set(cells.map(toKey));
    events.forEach((e) => {
      if (e.type === "leave" && e.end_date && e.end_date > e.date) {
        for (let d = fromKey(e.date); toKey(d) <= e.end_date; d = addDays(d, 1)) { if (gridKeys.has(toKey(d))) push(toKey(d), { ...e, key: `${e.type}-${e.date}-${toKey(d)}` }); }
      } else if (gridKeys.has(e.date)) {
        push(e.date, { ...e, key: `${e.type}-${e.date}-${e.title}` });
      }
    });
    cells.forEach((d) => {
      const dayName = DAY_NAMES[d.getDay()];
      weekly.filter((c) => c.day_of_week === dayName).forEach((c) => push(toKey(d), {
        type: "lecture", key: `lecture-${c.id}-${toKey(d)}`, date: toKey(d), title: c.subject_name,
        start_time: c.start_time, end_time: c.end_time,
        detail: role === "faculty" ? `${c.department} · Sem ${c.semester}` : c.faculty_name || "",
        classroom: c.classroom,
      }));
    });
    Object.values(map).forEach((list) => list.sort((a, b) => (a.type === "lecture" ? 0 : 1) - (b.type === "lecture" ? 0 : 1) || (a.start_time || "").localeCompare(b.start_time || "")));
    return map;
  }, [events, weekly, cells, role]);

  const presentTypes = useMemo(() => {
    const set = new Set(events.map((e) => e.type));
    if (weekly.length > 0) set.add("lecture");
    return TYPE_ORDER.filter((t) => set.has(t));
  }, [events, weekly]);

  const visible = (list) => (list || []).filter((i) => !hidden.has(i.type));
  const monthCounts = useMemo(() => {
    const counts = {};
    cells.forEach((d) => { if (d.getMonth() === cursor.getMonth()) (itemsByDate[toKey(d)] || []).forEach((i) => { counts[i.type] = (counts[i.type] || 0) + 1; }); });
    return counts;
  }, [cells, itemsByDate, cursor]);

  const selectedItems = visible(itemsByDate[selectedKey]);
  const selectedDate = fromKey(selectedKey);
  const classes = selectedItems.filter((i) => i.type === "lecture");
  const others = selectedItems.filter((i) => i.type !== "lecture");

  // "Up next": the nearest dated non-lecture items from today onward (real events only).
  const upNext = useMemo(
    () => events.filter((e) => !hidden.has(e.type) && (e.end_date || e.date) >= todayKey).sort((a, b) => a.date.localeCompare(b.date)).slice(0, 5),
    [events, hidden, todayKey]
  );

  const goToMonthOf = (d) => setCursor(new Date(d.getFullYear(), d.getMonth(), 1));
  const select = (key, { focus = false } = {}) => {
    setSelectedKey(key);
    const d = fromKey(key);
    if (d.getMonth() !== cursor.getMonth() || d.getFullYear() !== cursor.getFullYear()) goToMonthOf(d);
    if (focus) requestAnimationFrame(() => requestAnimationFrame(() => cellRefs.current[key]?.focus()));
  };
  const changeMonth = (delta) => {
    const next = new Date(cursor.getFullYear(), cursor.getMonth() + delta, 1);
    setCursor(next);
    const d = fromKey(selectedKey);
    setSelectedKey(toKey(new Date(next.getFullYear(), next.getMonth(), Math.min(d.getDate(), new Date(next.getFullYear(), next.getMonth() + 1, 0).getDate()))));
  };
  const goToday = () => { setCursor(new Date(new Date().getFullYear(), new Date().getMonth(), 1)); setSelectedKey(todayKey); };

  const onGridKey = (e) => {
    const moves = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
    if (moves[e.key] !== undefined) { e.preventDefault(); select(toKey(addDays(fromKey(selectedKey), moves[e.key])), { focus: true }); }
    else if (e.key === "PageUp" || e.key === "PageDown") {
      e.preventDefault();
      const d = fromKey(selectedKey); const n = new Date(d.getFullYear(), d.getMonth() + (e.key === "PageUp" ? -1 : 1), 1);
      select(toKey(new Date(n.getFullYear(), n.getMonth(), Math.min(d.getDate(), new Date(n.getFullYear(), n.getMonth() + 1, 0).getDate()))), { focus: true });
    } else if (e.key === "Home") { e.preventDefault(); select(todayKey, { focus: true }); }
  };

  const toggle = (type) => setHidden((h) => { const n = new Set(h); n.has(type) ? n.delete(type) : n.add(type); return n; });
  const subtitle = role === "faculty" ? "Your lectures, assignment deadlines and leave in one place."
    : role === "student" ? "Your classes, deadlines, exams and study sessions in one place." : "Approved leave across the institution.";

  return (
    <DashboardLayout>
      <div className="pt-2">
        <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-display font-bold">Calendar</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>
          </div>
          <button type="button" onClick={goToday} className="btn-secondary !py-2 text-sm inline-flex items-center gap-2"><FiSun size={14} /> Today</button>
        </div>

        {error && !loading ? (
          <div role="alert" className="glass-card flex flex-col items-center gap-2 py-16 text-center">
            <FiAlertCircle className="text-danger" size={26} />
            <p className="text-sm text-danger">{error}</p>
            <button type="button" onClick={load} className="btn-secondary !py-1.5 text-sm">Retry</button>
          </div>
        ) : (
          <div className="grid lg:grid-cols-12 gap-5">
            <div className="glass-card p-4 sm:p-5 lg:col-span-8" aria-busy={loading}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-display font-bold leading-none" aria-live="polite">
                    {MONTH_NAMES[cursor.getMonth()]} <span className="text-slate-400 font-medium">{cursor.getFullYear()}</span>
                  </h2>
                </div>
                <div className="flex items-center gap-1 rounded-xl bg-slate-100/80 dark:bg-white/5 p-1">
                  <button type="button" onClick={() => changeMonth(-1)} aria-label="Previous month" className="w-8 h-8 rounded-lg hover:bg-white dark:hover:bg-white/10 flex items-center justify-center transition-colors"><FiChevronLeft /></button>
                  <button type="button" onClick={() => changeMonth(1)} aria-label="Next month" className="w-8 h-8 rounded-lg hover:bg-white dark:hover:bg-white/10 flex items-center justify-center transition-colors"><FiChevronRight /></button>
                </div>
              </div>

              {presentTypes.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4" role="group" aria-label="Show or hide event types">
                  {presentTypes.map((t) => {
                    const m = TYPE_META[t]; const off = hidden.has(t);
                    return (
                      <button key={t} type="button" onClick={() => toggle(t)} aria-pressed={!off}
                        className={`text-xs px-3 py-1.5 rounded-full border inline-flex items-center gap-1.5 transition-all ${off ? "border-slate-200 dark:border-white/10 text-slate-400 line-through" : `border-transparent ${m.chip} font-medium`}`}>
                        <span className={`w-2 h-2 rounded-full ${m.dot}`} /> {m.label}
                        <span className="opacity-70 tabular-nums">{monthCounts[t] || 0}</span>
                      </button>
                    );
                  })}
                </div>
              )}

              <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-400 mb-1.5">
                {WEEKDAY_SHORT.map((d) => <div key={d}>{d}</div>)}
              </div>

              {loading ? (
                <div className="grid grid-cols-7 gap-1 animate-pulse motion-reduce:animate-none" aria-label="Loading calendar">
                  {Array.from({ length: 42 }, (_, i) => <div key={i} className="h-14 md:h-24 rounded-xl bg-slate-100 dark:bg-white/5" />)}
                </div>
              ) : (
                <div role="grid" aria-label={`${MONTH_NAMES[cursor.getMonth()]} ${cursor.getFullYear()}`} onKeyDown={onGridKey} className="grid grid-cols-7 gap-1">
                  {cells.map((d) => {
                    const key = toKey(d);
                    const inMonth = d.getMonth() === cursor.getMonth();
                    const isToday = key === todayKey;
                    const isSelected = key === selectedKey;
                    const items = visible(itemsByDate[key]);
                    return (
                      <button
                        key={key} type="button" role="gridcell" data-date={key} ref={(el) => { cellRefs.current[key] = el; }}
                        tabIndex={isSelected ? 0 : -1} aria-selected={isSelected} aria-current={isToday ? "date" : undefined}
                        aria-label={`${d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}${items.length ? `, ${items.length} item${items.length === 1 ? "" : "s"}` : ", nothing scheduled"}`}
                        onClick={() => select(key)}
                        className={`relative h-14 md:h-24 rounded-xl p-1.5 text-left flex flex-col transition-all duration-150 motion-reduce:transition-none
                          ${isSelected ? "bg-gradient-to-br from-primary to-secondary text-white shadow-glow" : isToday ? "bg-primary/10 ring-1 ring-primary/40" : "hover:bg-slate-100 dark:hover:bg-white/5"}
                          ${!inMonth && !isSelected ? "opacity-40" : ""}`}
                      >
                        <span className={`text-xs font-semibold w-6 h-6 rounded-full flex items-center justify-center ${isToday && !isSelected ? "bg-primary text-white" : ""}`}>{d.getDate()}</span>
                        <span className="hidden md:flex flex-col gap-0.5 mt-1 overflow-hidden w-full">
                          {items.slice(0, 2).map((i) => (
                            <span key={i.key} className={`truncate rounded px-1 py-px text-[10px] leading-tight ${isSelected ? "bg-white/25 text-white" : TYPE_META[i.type]?.chip || "bg-slate-100 text-slate-500"}`}>
                              {i.type === "lecture" ? `${format12h(i.start_time).replace(" ", "").toLowerCase()} ` : ""}{i.title}
                            </span>
                          ))}
                          {items.length > 2 && <span className={`text-[10px] px-1 ${isSelected ? "text-white/90" : "text-slate-400"}`}>+{items.length - 2} more</span>}
                        </span>
                        {items.length > 0 && (
                          <span className="md:hidden flex gap-0.5 mt-auto justify-center">
                            {[...new Set(items.map((i) => i.type))].slice(0, 4).map((t) => <span key={t} className={`w-1.5 h-1.5 rounded-full ${isSelected ? "bg-white" : TYPE_META[t]?.dot || "bg-slate-400"}`} />)}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
              <p className="mt-3 text-[11px] text-slate-400 hidden sm:block">Tip: use the arrow keys to move between days, PageUp / PageDown to change month, Home for today.</p>
            </div>

            <div className="lg:col-span-4 space-y-5">
              <div className="glass-card p-5 lg:sticky lg:top-4">
                <div className="flex items-start justify-between gap-2 mb-4">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-400">{selectedDate.toLocaleDateString(undefined, { weekday: "long" })}</p>
                    <p className="text-lg font-display font-bold leading-tight">{selectedDate.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}</p>
                  </div>
                  {selectedKey === todayKey && <span className="text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary font-semibold">Today</span>}
                </div>

                {loading ? <div className="h-24 rounded-xl bg-slate-100 dark:bg-white/5 animate-pulse motion-reduce:animate-none" /> : selectedItems.length === 0 ? (
                  <div className="text-center py-8">
                    <span className="mx-auto mb-2 w-10 h-10 rounded-xl bg-slate-100 dark:bg-white/5 text-slate-400 flex items-center justify-center"><FiCalendar size={18} /></span>
                    <p className="text-sm font-medium">Nothing scheduled</p>
                    <p className="text-xs text-slate-400 mt-0.5">{hidden.size ? "Some event types are hidden by your filters." : "A free day."}</p>
                  </div>
                ) : (
                  <div className="space-y-5">
                    {classes.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">Classes</p>
                        <ul className="space-y-2">
                          {classes.map((c) => (
                            <li key={c.key} className="flex gap-3 rounded-xl border border-slate-100 dark:border-white/10 bg-white/60 dark:bg-white/5 p-3">
                              <span className="w-1 rounded-full bg-primary shrink-0" aria-hidden="true" />
                              <div className="min-w-0">
                                <p className="text-sm font-medium truncate">{c.title}</p>
                                <p className="text-xs text-slate-500 dark:text-slate-400">{format12h(c.start_time)} – {format12h(c.end_time)}</p>
                                <p className="text-xs text-slate-400 flex flex-wrap items-center gap-x-3 mt-0.5">
                                  {c.classroom && <span className="inline-flex items-center gap-1"><FiMapPin size={10} /> {c.classroom}</span>}
                                  {c.detail && <span className="truncate">{c.detail}</span>}
                                </p>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {others.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">Deadlines & events</p>
                        <ul className="space-y-2">
                          {others.map((e) => {
                            const meta = TYPE_META[e.type] || { chip: "bg-slate-100 text-slate-500", icon: FiCalendar, label: "Event" };
                            const Icon = meta.icon; const href = linkFor(e.type, role);
                            return (
                              <li key={e.key} className="flex items-start gap-3 rounded-xl border border-slate-100 dark:border-white/10 bg-white/60 dark:bg-white/5 p-3">
                                <span className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${meta.chip}`}><Icon size={14} /></span>
                                <div className="min-w-0 flex-1">
                                  <p className="text-sm font-medium">{e.title}</p>
                                  {e.detail && <p className="text-xs text-slate-400">{e.detail}</p>}
                                  <span className={`inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded-full font-medium ${meta.chip}`}>{meta.label}</span>
                                </div>
                                {href && <Link to={href} aria-label={`Open ${meta.label}`} className="text-slate-400 hover:text-primary mt-1"><FiArrowRight size={14} /></Link>}
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {!loading && upNext.length > 0 && (
                <div className="glass-card p-5">
                  <p className="font-display font-semibold mb-3 text-sm">Up next</p>
                  <ul className="space-y-1">
                    {upNext.map((e, i) => {
                      const meta = TYPE_META[e.type] || {}; const when = fromKey(e.date);
                      return (
                        <li key={`${e.type}-${e.date}-${i}`}>
                          <button type="button" onClick={() => select(e.date)} className="w-full flex items-center gap-3 rounded-lg px-2 py-2 text-left hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                            <span className={`w-2 h-2 rounded-full shrink-0 ${meta.dot || "bg-slate-400"}`} />
                            <span className="min-w-0 flex-1 truncate text-sm">{e.title}</span>
                            <span className="text-xs text-slate-400 shrink-0">{when.toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
