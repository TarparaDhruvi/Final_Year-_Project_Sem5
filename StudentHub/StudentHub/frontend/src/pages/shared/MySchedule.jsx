import { FiMapPin, FiUser, FiCheckCircle, FiRadio, FiClock } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import NextClassCard from "../../components/NextClassCard";
import useSchedule from "../../hooks/useSchedule";
import useNow from "../../hooks/useNow";
import { useAuth } from "../../context/AuthContext";
import { analyseSchedule, format12h, WEEK_DAYS } from "../../utils/schedule";

const STATUS_STYLE = {
  completed: { label: "Completed", cls: "bg-slate-100 dark:bg-white/10 text-slate-500", icon: FiCheckCircle },
  live: { label: "Live now", cls: "bg-success/10 text-success", icon: FiRadio },
  upcoming: { label: "Upcoming", cls: "bg-primary/10 text-primary", icon: FiClock },
};

export default function MySchedule() {
  const { user } = useAuth();
  const { slots, loading, error } = useSchedule();
  const now = useNow(30000);
  const { dayName, today } = analyseSchedule(slots, now);

  const byDay = (day) => slots.filter((s) => s.day_of_week === day).sort((a, b) => a.start_time.localeCompare(b.start_time));

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">My Schedule</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          Built automatically from the timetable your Admin created — it updates the moment they change it.
        </p>

        {loading ? (
          <p className="text-center py-16 text-slate-400">Loading your schedule...</p>
        ) : error ? (
          <p className="text-center py-16 text-danger">Couldn't load your schedule. Please refresh.</p>
        ) : (
          <>
            <div className="grid lg:grid-cols-3 gap-4 mb-6">
              <div className="lg:col-span-2"><NextClassCard slots={slots} role={user.role} /></div>
              <div className="glass-card p-5 flex flex-col justify-center">
                <p className="text-sm text-slate-500 dark:text-slate-400">{dayName}</p>
                <p className="text-4xl font-display font-bold text-primary mt-1">{today.length}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400">class{today.length !== 1 ? "es" : ""} today</p>
              </div>
            </div>

            <h2 className="font-display font-semibold mb-3">Today's classes</h2>
            {today.length === 0 ? (
              <div className="glass-card p-8 text-center text-slate-400 mb-8">No classes today — enjoy the free time!</div>
            ) : (
              <div className="space-y-3 mb-8">
                {today.map((s) => {
                  const st = STATUS_STYLE[s.status];
                  return (
                    <div key={s.id} className={`glass-card p-4 flex flex-wrap items-center gap-4 ${s.status === "live" ? "ring-2 ring-success/40" : ""}`}>
                      <div className="w-14 text-center flex-shrink-0">
                        <p className="text-[11px] uppercase text-slate-400 font-medium">Lecture</p>
                        <p className="text-xl font-display font-bold">{s.lecture}<span className="text-sm text-slate-400 font-normal">/{s.total}</span></p>
                      </div>
                      <div className="flex-1 min-w-[180px]">
                        <p className="font-semibold">{s.subject_name} {s.subject_code && <span className="text-xs text-slate-400 font-normal">({s.subject_code})</span>}</p>
                        <p className="text-sm text-slate-500 dark:text-slate-400">{format12h(s.start_time)} – {format12h(s.end_time)}</p>
                        <div className="flex flex-wrap gap-x-4 text-xs text-slate-400 mt-1">
                          <span className="flex items-center gap-1"><FiUser size={12} /> {user.role === "student" ? s.faculty_name || "Faculty" : `${s.department} · Sem ${s.semester}`}</span>
                          <span className="flex items-center gap-1"><FiMapPin size={12} /> {s.classroom}</span>
                        </div>
                      </div>
                      <span className={`text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1.5 ${st.cls}`}><st.icon /> {st.label}</span>
                    </div>
                  );
                })}
              </div>
            )}

            <h2 className="font-display font-semibold mb-3">This week</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {WEEK_DAYS.map((day) => (
                <div key={day} className={`glass-card p-4 ${day === dayName ? "ring-2 ring-primary/40" : ""}`}>
                  <h3 className="font-display font-semibold mb-3 flex items-center justify-between">
                    {day} {day === dayName && <span className="text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary">Today</span>}
                  </h3>
                  {byDay(day).length === 0 ? (
                    <p className="text-xs text-slate-400">No classes.</p>
                  ) : (
                    <div className="space-y-2">
                      {byDay(day).map((s) => (
                        <div key={s.id} className="p-2.5 rounded-lg bg-primary/5">
                          <p className="text-sm font-medium">{format12h(s.start_time)} – {format12h(s.end_time)}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">{s.subject_name} · {s.classroom}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
