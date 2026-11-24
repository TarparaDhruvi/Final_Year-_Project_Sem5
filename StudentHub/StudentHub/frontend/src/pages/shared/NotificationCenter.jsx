import { useEffect, useMemo, useState } from "react";
import { FiCheck, FiBell } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";
import { useNotifications } from "../../context/NotificationContext";

const TYPE_DOT = {
  missed_deadline: "bg-danger",
  assignment_reminder: "bg-warning",
  leave_status: "bg-success",
  leave_request: "bg-warning",
  new_announcement: "bg-primary",
  new_submission: "bg-secondary",
  timetable_update: "bg-secondary",
};
const SEVERITY_DOT = { blue: "bg-primary", orange: "bg-warning", red: "bg-danger" };
const dotClass = (n) => SEVERITY_DOT[n.severity] || TYPE_DOT[n.type] || "bg-secondary";

function dayLabel(iso) {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  const sameDay = (a, b) => a.toDateString() === b.toDateString();
  if (sameDay(date, today)) return "Today";
  if (sameDay(date, yesterday)) return "Yesterday";

  const daysAgo = Math.floor((today - date) / (1000 * 60 * 60 * 24));
  if (daysAgo < 7) return `${daysAgo} days ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function NotificationCenter() {
  const { markRead, markAllRead } = useNotifications();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all"); // all | unread | read

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/notifications", { params: { limit: 200 } });
      setNotifications(data);
    } catch {
      // silent — the page just shows empty state
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (filter === "unread") return notifications.filter((n) => !n.is_read);
    if (filter === "read") return notifications.filter((n) => n.is_read);
    return notifications;
  }, [notifications, filter]);

  const grouped = useMemo(() => {
    const groups = {};
    filtered.forEach((n) => {
      const label = dayLabel(n.created_at);
      groups[label] = groups[label] || [];
      groups[label].push(n);
    });
    return groups;
  }, [filtered]);

  const handleMarkRead = async (id) => {
    await markRead(id);
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
  };

  const handleMarkAllRead = async () => {
    await markAllRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <DashboardLayout>
      <div className="pt-2">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-display font-bold">Notification Center</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{unreadCount} unread</p>
          </div>
          <div className="flex items-center gap-2">
            {["all", "unread", "read"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors ${filter === f ? "bg-primary text-white" : "glass-card text-slate-500"}`}
              >
                {f}
              </button>
            ))}
            {unreadCount > 0 && (
              <button onClick={handleMarkAllRead} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-success/10 text-success hover:bg-success/20">
                <FiCheck /> Mark all read
              </button>
            )}
          </div>
        </div>

        {loading ? (
          <p className="text-center py-16 text-slate-400">Loading...</p>
        ) : Object.keys(grouped).length === 0 ? (
          <div className="glass-card p-12 text-center">
            <FiBell className="mx-auto text-3xl text-slate-300 mb-3" />
            <p className="text-slate-400">No {filter !== "all" ? filter : ""} notifications.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(grouped).map(([label, items]) => (
              <div key={label}>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">{label}</p>
                <div className="glass-card divide-y divide-slate-100 dark:divide-white/5 overflow-hidden">
                  {items.map((n) => (
                    <button
                      key={n.id}
                      onClick={() => !n.is_read && handleMarkRead(n.id)}
                      className={`w-full text-left px-4 py-3.5 flex items-start gap-3 transition-colors ${n.is_read ? "hover:bg-slate-50 dark:hover:bg-white/5" : "bg-primary/5 hover:bg-primary/10"}`}
                    >
                      <span className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${dotClass(n)}`} />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium">{n.title}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{n.message}</p>
                      </div>
                      <span className="text-[11px] text-slate-400 flex-shrink-0">{new Date(n.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
