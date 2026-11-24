import { Link } from "react-router-dom";
import { FiClock, FiMapPin, FiUser, FiRadio } from "react-icons/fi";
import useNow from "../hooks/useNow";
import { analyseSchedule, countdownTo, format12h } from "../utils/schedule";

/**
 * "Current / next class" hero card with a live countdown.
 * `role` decides whether we show the faculty name (students) or the batch (faculty).
 */
export default function NextClassCard({ slots, role, scheduleLink }) {
  const now = useNow(1000);
  const { today, current, nextToday, nextLater } = analyseSchedule(slots, now);

  const focus = current || nextToday;
  const detailLine = (s) =>
    role === "student" ? (
      <span className="flex items-center gap-1.5"><FiUser size={13} /> {s.faculty_name || "Faculty"}</span>
    ) : (
      <span className="flex items-center gap-1.5"><FiUser size={13} /> {s.department} · Sem {s.semester}</span>
    );

  return (
    <div className="glass-card p-5 relative overflow-hidden">
      <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-gradient-to-br from-primary/20 to-secondary/20 blur-2xl pointer-events-none" />
      <div className="flex items-center justify-between mb-3 relative">
        <p className="font-display font-semibold flex items-center gap-2"><FiClock /> {current ? "Class in progress" : "Next class"}</p>
        {scheduleLink && <Link to={scheduleLink} className="text-xs text-primary font-medium hover:underline">Full schedule →</Link>}
      </div>

      {focus ? (
        <div className="relative">
          <p className="text-xl font-display font-bold">{focus.subject_name}</p>
          <div className="mt-1 space-y-1 text-sm text-slate-500 dark:text-slate-400">
            <p>{format12h(focus.start_time)} – {format12h(focus.end_time)}</p>
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {detailLine(focus)}
              <span className="flex items-center gap-1.5"><FiMapPin size={13} /> {focus.classroom}</span>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs px-2.5 py-1 rounded-full bg-primary/10 text-primary font-medium">
              Lecture {focus.lecture} of {focus.total} today
            </span>
            {current ? (
              <span className="text-xs px-2.5 py-1 rounded-full bg-success/10 text-success font-semibold flex items-center gap-1.5">
                <FiRadio className="animate-pulse" /> Live — ends in {countdownTo(current.end_time, now)}
              </span>
            ) : (
              <span className="text-xs px-2.5 py-1 rounded-full bg-warning/10 text-warning font-semibold">
                Starts in {countdownTo(nextToday.start_time, now)}
              </span>
            )}
          </div>
        </div>
      ) : nextLater ? (
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">
            {today.length > 0 ? "All of today's classes are done. " : "No classes today. "}Next up:
          </p>
          <p className="text-lg font-display font-bold">{nextLater.subject_name}</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">{nextLater.dayLabel}, {format12h(nextLater.start_time)} · {nextLater.classroom}</p>
        </div>
      ) : (
        <p className="text-sm text-slate-400 py-4">No classes scheduled yet — they'll appear here as soon as the Admin adds them to the timetable.</p>
      )}
    </div>
  );
}
