import { useEffect, useMemo, useState } from "react";
import { Bar, Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend } from "chart.js";
import { FiUsers, FiUserCheck, FiBook, FiClipboard, FiCalendar, FiVolume2, FiBarChart2 } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import QuickActions from "../../components/QuickActions";
import StatCard from "../../components/StatCard";
import StudentPerformance from "../../components/StudentPerformance";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend);

const QUICK = [
  { to: "/admin/students", label: "Students", desc: "Add & manage", icon: FiUsers },
  { to: "/admin/faculty", label: "Faculty", desc: "Accounts & subjects", icon: FiUserCheck },
  { to: "/admin/subjects", label: "Subjects", desc: "Create & map", icon: FiBook },
  { to: "/admin/timetable", label: "Timetable", desc: "Weekly schedule", icon: FiCalendar },
  { to: "/admin/announcements", label: "Announce", desc: "Broadcast notices", icon: FiVolume2 },
  { to: "/admin/reports", label: "Reports", desc: "Attendance & marks", icon: FiBarChart2 },
];

const PALETTE = ["#6D4AFF", "#B51DC9", "#22C55E", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#EC4899"];

export default function AdminDashboard() {
  const { user } = useAuth();
  const [students, setStudents] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [leave, setLeave] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get("/students"), api.get("/faculty"), api.get("/subjects"), api.get("/leave")])
      .then(([s, f, sub, l]) => { setStudents(s.data); setFaculty(f.data); setSubjects(sub.data); setLeave(l.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const pendingLeave = leave.filter((l) => l.status === "pending").length;

  const byDept = useMemo(() => {
    const map = {};
    students.forEach((s) => { map[s.department] = (map[s.department] || 0) + 1; });
    return map;
  }, [students]);

  const leaveCounts = ["pending", "approved", "rejected"].map((k) => leave.filter((l) => l.status === k).length);

  const deptChart = {
    labels: Object.keys(byDept),
    datasets: [{ label: "Students", data: Object.values(byDept), backgroundColor: PALETTE, borderRadius: 8, maxBarThickness: 44 }],
  };
  const leaveChart = {
    labels: ["Pending", "Approved", "Rejected"],
    datasets: [{ data: leaveCounts, backgroundColor: ["#F59E0B", "#22C55E", "#EF4444"], borderWidth: 0 }],
  };
  const barOptions = { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } };

  return (
    <DashboardLayout>
      <div className="pt-2 space-y-6">
        <div>
          <h1 className="text-2xl font-display font-bold">Admin Dashboard</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Welcome back, {user.full_name.split(" ")[0]} — campus overview at a glance.</p>
        </div>

        <QuickActions items={QUICK} />

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Students" value={students.length} icon={FiUsers} loading={loading} />
          <StatCard label="Total Faculty" value={faculty.length} icon={FiUserCheck} tone="secondary" loading={loading} />
          <StatCard label="Total Subjects" value={subjects.length} icon={FiBook} tone="success" loading={loading} />
          <StatCard label="Pending Leave Requests" value={pendingLeave} icon={FiClipboard} tone="warning" loading={loading} />
        </div>

        <div className="grid lg:grid-cols-3 gap-4">
          <div className="glass-card p-5 lg:col-span-2">
            <p className="font-display font-semibold mb-4">Students by department</p>
            {students.length === 0 ? <p className="text-sm text-slate-400 py-10 text-center">No students yet.</p> : <Bar data={deptChart} options={barOptions} height={140} />}
          </div>
          <div className="glass-card p-5">
            <p className="font-display font-semibold mb-4">Leave requests</p>
            {leave.length === 0 ? <p className="text-sm text-slate-400 py-10 text-center">No leave requests yet.</p> : (
              <div className="max-w-[220px] mx-auto"><Doughnut data={leaveChart} options={{ plugins: { legend: { position: "bottom" } }, cutout: "65%" }} /></div>
            )}
          </div>
        </div>

        <StudentPerformance subjects={subjects} />
      </div>
    </DashboardLayout>
  );
}
