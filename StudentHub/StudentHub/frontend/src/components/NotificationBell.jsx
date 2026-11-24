import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { FiBell, FiCheck } from "react-icons/fi";
import { useNotifications } from "../context/NotificationContext";

const TYPE_DOT = {
  missed_deadline: "bg-danger",
  assignment_reminder: "bg-warning",
  leave_status: "bg-success",
  new_announcement: "bg-primary",
};

// Deadline reminders carry an explicit severity (blue=3 days out, orange=tomorrow, red=today) — that
// overrides the generic type colour above when present, matching the Smart Deadline Reminder colour system.
const SEVERITY_DOT = { blue: "bg-primary", orange: "bg-warning", red: "bg-danger" };
const dotClass = (n) => SEVERITY_DOT[n.severity] || TYPE_DOT[n.type] || "bg-secondary";

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function NotificationBell() {
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        aria-label="Notifications"
        className="relative w-10 h-10 flex items-center justify-center rounded-xl glass-card hover:scale-105 active:scale-95 transition-transform duration-150"
      >
        <FiBell />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-danger text-white text-[10px] font-bold flex items-center justify-center">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto glass-card z-50 p-2">
          <div className="flex items-center justify-between px-3 py-2">
            <p className="font-semibold text-sm">Notifications</p>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="text-xs text-primary hover:underline flex items-center gap-1"
              >
                <FiCheck /> Mark all read
              </button>
            )}
          </div>

          <Link to="/notifications" onClick={() => setOpen(false)} className="block text-center text-xs text-primary font-medium py-1.5 hover:underline">
            Open Notification Center →
          </Link>
          {notifications.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">No notifications yet.</p>
          ) : (
            <div className="space-y-1">
              {notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={() => !n.is_read && markRead(n.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl transition-colors ${
                    n.is_read ? "hover:bg-slate-100 dark:hover:bg-white/5" : "bg-primary/5 hover:bg-primary/10"
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${dotClass(n)}`} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{n.title}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">{n.message}</p>
                      <p className="text-[11px] text-slate-400 mt-0.5">{timeAgo(n.created_at)}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
