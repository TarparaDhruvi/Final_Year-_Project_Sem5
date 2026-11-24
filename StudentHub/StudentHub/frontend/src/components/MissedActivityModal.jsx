import { FiAlertCircle, FiVolume2 } from "react-icons/fi";
import Modal from "./Modal";
import { useAuth } from "../context/AuthContext";

export default function MissedActivityModal() {
  const { user, missedActivity, clearMissedActivity } = useAuth();

  if (!user || user.role !== "student" || !missedActivity) return null;

  const { days_away, missed_assignments, new_announcements } = missedActivity;

  return (
    <Modal open={true} onClose={clearMissedActivity} title={`Welcome back, ${user.full_name.split(" ")[0]}!`}>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-5">
        You were away for {days_away} day{days_away !== 1 ? "s" : ""}. Here's what happened while you were gone:
      </p>

      {missed_assignments.length > 0 && (
        <div className="mb-5">
          <p className="text-xs font-semibold text-danger uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <FiAlertCircle /> Missed Deadlines
          </p>
          <div className="space-y-2">
            {missed_assignments.map((a, i) => (
              <div key={i} className="p-3 rounded-xl bg-danger/10">
                <p className="text-sm font-medium">{a.title}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{a.subject_name} · was due {a.due_date}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-2">Please contact your faculty if late submissions are allowed.</p>
        </div>
      )}

      {new_announcements.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-primary uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <FiVolume2 /> New While You Were Away
          </p>
          <div className="space-y-2">
            {new_announcements.map((a, i) => (
              <div key={i} className="p-3 rounded-xl bg-primary/5">
                <p className="text-sm font-medium">{a.title}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{a.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <button onClick={clearMissedActivity} className="btn-primary w-full mt-6">Got it</button>
    </Modal>
  );
}
