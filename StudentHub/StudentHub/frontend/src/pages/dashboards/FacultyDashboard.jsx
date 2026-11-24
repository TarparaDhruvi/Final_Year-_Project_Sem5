import { useEffect, useMemo, useState } from "react";
import {
  FiBook, FiUsers, FiFileText, FiClock, FiAlertCircle, FiCheckCircle, FiBell, FiEdit3,
  FiCheckSquare, FiUpload, FiCalendar,
} from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import QuickActions from "../../components/QuickActions";
import StatCard from "../../components/StatCard";
import NextClassCard from "../../components/NextClassCard";
import ClassroomActivityHub from "../../components/ClassroomActivityHub";
import api from "../../services/api";
import useNow from "../../hooks/useNow";
import useSchedule from "../../hooks/useSchedule";
import { analyseSchedule } from "../../utils/schedule";
import { useAuth } from "../../context/AuthContext";
import { useNotifications } from "../../context/NotificationContext";

const pad = (n) => String(n).padStart(2, "0");
const localDateStr = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

const QUICK = [
  { to: "/faculty/attendance", label: "Attendance", desc: "Mark today's class", icon: FiCheckSquare },
  { to: "/faculty/assignments", label: "Assignments", desc: "Create & grade", icon: FiFileText },
  { to: "/faculty/notes", label: "Study Material", desc: "Upload notes", icon: FiUpload },
  { to: "/faculty/marks", label: "Marks", desc: "Enter & publish", icon: FiEdit3 },
  { to: "/faculty/schedule", label: "My Schedule", desc: "Today's classes", icon: FiCalendar },
  { to: "/faculty/students", label: "My Students", desc: "Profiles & progress", icon: FiUsers },
];

export default function FacultyDashboard() {
  const { user } = useAuth();
  const { notifications } = useNotifications();
  const { slots } = useSchedule();
  const now = useNow(30000);
  const [subjects, setSubjects] = useState([]);
  const [studentCount, setStudentCount] = useState(0);
  const [assignments, setAssignments] = useState([]);
  const [marks, setMarks] = useState({ published: 0, pending: 0, avgInternal: null, avgPractical: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const { data: mine } = await api.get("/faculty/me/subjects");
        setSubjects(mine);
        if (mine.length === 0) return;

        const [rosters, assignmentLists, marksLists] = await Promise.all([
          Promise.all(mine.map((s) => api.get("/students/roster", { params: { subject_id: s.id } }))),
          Promise.all(mine.map((s) => api.get(`/assignments/subject/${s.id}`))),
          Promise.all(mine.map((s) => api.get(`/marks/subject/${s.id}`))),
        ]);

        const unique = new Set();
        rosters.forEach(({ data }) => data.forEach((st) => unique.add(st.id)));
        setStudentCount(unique.size);

        setAssignments(assignmentLists.flatMap(({ data }, i) => data.map((a) => ({ ...a, subject_name: mine[i].name }))));

        const allMarks = marksLists.flatMap(({ data }) => data);
        const published = allMarks.filter((m) => m.published).length;
        const avg = (vals) => (vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : null);
        setMarks({
          published, pending: allMarks.length - published,
          avgInternal: avg(allMarks.filter((m) => m.internal != null).map((m) => m.internal)),
          avgPractical: avg(allMarks.filter((m) => m.practical != null).map((m) => m.practical)),
        });
      } catch {
        /* widgets degrade to empty states */
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const todayStr = localDateStr(now);
  const { activeCount, overdueCount } = useMemo(() => ({
    activeCount: assignments.filter((a) => a.due_date >= todayStr).length,
    overdueCount: assignments.filter((a) => a.due_date < todayStr).length,
  }), [assignments, todayStr]);
  const { today } = analyseSchedule(slots, now);

  return (
    <DashboardLayout>
      <div className="pt-2 space-y-6">
        <div>
          <h1 className="text-2xl font-display font-bold">Faculty Dashboard</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">{user.full_name.split(" ")[0]}'s teaching overview, live from your assigned subjects.</p>
        </div>

        <QuickActions items={QUICK} />

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Assigned Subjects" value={subjects.length} icon={FiBook} loading={loading} />
          <StatCard label="Students Taught" value={studentCount} icon={FiUsers} tone="secondary" loading={loading} />
          <StatCard label="Total Assignments" value={assignments.length} icon={FiFileText} tone="warning" loading={loading} />
          <StatCard label="Classes Today" value={today.length} icon={FiClock} tone="success" />
        </div>

        {!loading && subjects.length === 0 && (
          <div className="glass-card p-6 text-center text-slate-400">
            No subjects are assigned to you yet. Once your Admin assigns subjects, they'll appear here and in every dropdown automatically.
          </div>
        )}

        <ClassroomActivityHub />

        <div className="grid lg:grid-cols-2 gap-4">
          <NextClassCard slots={slots} role="faculty" scheduleLink="/faculty/schedule" />

          <div className="glass-card p-5">
            <p className="font-display font-semibold mb-3">Assignment status</p>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 rounded-xl bg-success/10">
                <span className="flex items-center gap-2 text-sm font-medium text-success"><FiCheckCircle /> Active</span>
                <span className="font-display font-bold text-success">{activeCount}</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-danger/10">
                <span className="flex items-center gap-2 text-sm font-medium text-danger"><FiAlertCircle /> Overdue</span>
                <span className="font-display font-bold text-danger">{overdueCount}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-4">
          <div className="glass-card p-5">
            <p className="font-display font-semibold mb-4 flex items-center gap-2"><FiEdit3 /> Marks summary</p>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[["Published", marks.published], ["Pending", marks.pending], ["Avg. internal", marks.avgInternal ?? "—"], ["Avg. practical", marks.avgPractical ?? "—"]].map(([k, v]) => (
                <div key={k} className="p-3 rounded-xl bg-slate-50 dark:bg-white/5">
                  <p className="text-xs text-slate-500 dark:text-slate-400">{k}</p>
                  <p className="text-xl font-display font-bold mt-0.5">{v}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-5">
            <p className="font-display font-semibold mb-4 flex items-center gap-2"><FiBell /> Recent notifications</p>
            {notifications.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-6">No notifications yet.</p>
            ) : (
              <div className="space-y-1">
                {notifications.slice(0, 5).map((n) => (
                  <div key={n.id} className={`px-3 py-2.5 rounded-xl ${n.is_read ? "" : "bg-primary/5"}`}>
                    <p className="text-sm font-medium">{n.title}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{n.message}</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">{timeAgo(n.created_at)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
