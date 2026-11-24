import { useEffect, useMemo, useState } from "react";
import { Bar } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from "chart.js";
import {
  FiCheckSquare, FiFileText, FiClock, FiBell, FiAlertCircle, FiBook, FiEdit3, FiCpu, FiCalendar,
} from "react-icons/fi";
import { Link } from "react-router-dom";
import DashboardLayout from "../../layouts/DashboardLayout";
import QuickActions from "../../components/QuickActions";
import SkillWalletWidget from "../../components/SkillWalletWidget";
import StatCard from "../../components/StatCard";
import NextClassCard from "../../components/NextClassCard";
import api from "../../services/api";
import useNow from "../../hooks/useNow";
import useSchedule from "../../hooks/useSchedule";
import { analyseSchedule, formatSeconds } from "../../utils/schedule";
import { useAuth } from "../../context/AuthContext";
import { useNotifications } from "../../context/NotificationContext";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const pad = (n) => String(n).padStart(2, "0");
const localDateStr = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const dayDiff = (dueStr, now) => {
  const [y, m, d] = dueStr.split("-").map(Number);
  const due = new Date(y, m - 1, d);
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((due - today) / 86400000);
};

const QUICK = [
  { to: "/student/assignments", label: "Assignments", desc: "View & submit", icon: FiFileText },
  { to: "/student/attendance", label: "Attendance", desc: "Track & predict", icon: FiCheckSquare },
  { to: "/student/schedule", label: "My Schedule", desc: "Today's classes", icon: FiCalendar },
  { to: "/student/notes", label: "Notes", desc: "Study material", icon: FiBook },
  { to: "/student/marks", label: "Marks", desc: "Internal & practical", icon: FiEdit3 },
  { to: "/student/ai", label: "Ask AI", desc: "Study assistant", icon: FiCpu },
  { to: "/student/study-coach", label: "Study Coach", desc: "Upload & generate", icon: FiCpu },
];

export default function StudentDashboard() {
  const { user } = useAuth();
  const { unreadCount } = useNotifications();
  const { slots } = useSchedule();
  const now = useNow(1000);
  const [assignments, setAssignments] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get("/assignments/mine"), api.get("/attendance/me")])
      .then(([a, att]) => { setAssignments(a.data); setAttendance(att.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const pending = useMemo(
    () => assignments.filter((a) => !["submitted", "graded"].includes(a.submission_status)),
    [assignments]
  );
  const todayStr = localDateStr(now);
  const dueToday = pending.filter((a) => a.due_date === todayStr);
  const overdue = pending.filter((a) => a.due_date < todayStr);
  const upcoming = pending
    .filter((a) => a.due_date > todayStr)
    .sort((a, b) => a.due_date.localeCompare(b.due_date))
    .slice(0, 5);

  const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
  const secondsLeft = Math.max(0, Math.floor((endOfDay - now) / 1000));

  const avgAttendance = attendance.length ? Math.round(attendance.reduce((s, r) => s + r.percentage, 0) / attendance.length) : null;
  const { today } = analyseSchedule(slots, now);

  const chartData = {
    labels: attendance.map((a) => a.subject_name),
    datasets: [{
      label: "Attendance %",
      data: attendance.map((a) => a.percentage),
      backgroundColor: attendance.map((a) => (a.at_risk ? "#EF4444" : "#6D4AFF")),
      borderRadius: 8, maxBarThickness: 38,
    }],
  };
  const chartOptions = {
    responsive: true, plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, max: 100, ticks: { callback: (v) => `${v}%` } } },
  };

  const reminderStyle = (days) =>
    days <= 0 ? { cls: "bg-danger/10 text-danger", text: "Due today" }
    : days === 1 ? { cls: "bg-warning/10 text-warning", text: "Due tomorrow" }
    : { cls: "bg-primary/10 text-primary", text: `${days} days left` };

  return (
    <DashboardLayout>
      <div className="pt-2 space-y-6">
        <div>
          <h1 className="text-2xl font-display font-bold">Student Dashboard</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Everything for today, {user.full_name.split(" ")[0]} — live from your college data.</p>
        </div>

        <QuickActions items={QUICK} />

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Overall Attendance" value={avgAttendance !== null ? `${avgAttendance}%` : "—"} icon={FiCheckSquare} tone={avgAttendance !== null && avgAttendance < 75 ? "danger" : "success"} loading={loading} />
          <StatCard label="Pending Assignments" value={pending.length} icon={FiFileText} tone="warning" loading={loading} />
          <StatCard label="Classes Today" value={today.length} icon={FiClock} tone="primary" />
          <StatCard label="Unread Notifications" value={unreadCount} icon={FiBell} tone="secondary" />
        </div>

        <div className="grid lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            {/* Smart Deadline Reminder: today's deadline with live countdown */}
            {(dueToday.length > 0 || overdue.length > 0) && (
              <div className="glass-card p-5 border border-danger/20">
                <p className="font-display font-semibold flex items-center gap-2 text-danger mb-3"><FiAlertCircle /> Today's Deadline</p>
                <div className="space-y-2">
                  {dueToday.map((a) => (
                    <Link to="/student/assignments" key={a.id} className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl bg-danger/10 hover:bg-danger/15 transition-colors">
                      <div>
                        <p className="font-medium text-sm">{a.title}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{a.subject_name} · due today at 11:59 PM</p>
                      </div>
                      <span className="text-sm font-display font-bold text-danger tabular-nums">{formatSeconds(secondsLeft)} left</span>
                    </Link>
                  ))}
                  {overdue.map((a) => (
                    <Link to="/student/assignments" key={a.id} className="flex items-center justify-between gap-2 p-3 rounded-xl bg-slate-100 dark:bg-white/5">
                      <div>
                        <p className="font-medium text-sm">{a.title}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{a.subject_name} · was due {a.due_date}</p>
                      </div>
                      <span className="text-xs font-semibold text-danger">Overdue</span>
                    </Link>
                  ))}
                </div>
                <p className="text-xs text-slate-400 mt-3">Don't forget to submit before the deadline.</p>
              </div>
            )}

            <div className="glass-card p-5">
              <p className="font-display font-semibold mb-4">Attendance by subject</p>
              {attendance.length === 0 ? (
                <p className="text-sm text-slate-400 py-10 text-center">No attendance recorded yet.</p>
              ) : (
                <Bar data={chartData} options={chartOptions} height={150} />
              )}
            </div>
          </div>

          <div className="space-y-4">
            <NextClassCard slots={slots} role="student" scheduleLink="/student/schedule" />
            <SkillWalletWidget />

            <div className="glass-card p-5">
              <p className="font-display font-semibold mb-3">Upcoming reminders</p>
              {upcoming.length === 0 ? (
                <p className="text-sm text-slate-400 py-4 text-center">Nothing coming up — you're all caught up!</p>
              ) : (
                <div className="space-y-2">
                  {upcoming.map((a) => {
                    const st = reminderStyle(dayDiff(a.due_date, now));
                    return (
                      <div key={a.id} className="flex items-center justify-between gap-2 p-2.5 rounded-xl bg-slate-50 dark:bg-white/5">
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{a.title}</p>
                          <p className="text-xs text-slate-400 truncate">{a.subject_name}</p>
                        </div>
                        <span className={`text-[11px] px-2 py-1 rounded-full font-semibold whitespace-nowrap ${st.cls}`}>{st.text}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
