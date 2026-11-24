import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Line } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler } from "chart.js";
import { FiTrendingUp, FiUsers, FiCalendar } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import StatCard from "../../components/StatCard";
import api from "../../services/api";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

export default function CampusPulse() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/analytics/campus-pulse").then(({ data }) => setData(data)).catch(() => toast.error("Failed to load Campus Pulse."));
  }, []);

  if (!data) return <DashboardLayout><p className="text-center py-16 text-slate-400">Loading...</p></DashboardLayout>;

  const chartData = {
    labels: data.attendance_trend_14d.map((d) => d.date.slice(5)),
    datasets: [{
      label: "Attendance %", data: data.attendance_trend_14d.map((d) => d.attendance_pct),
      borderColor: "#6D4AFF", backgroundColor: "rgba(109,74,255,0.1)", fill: true, tension: 0.3, spanGaps: true,
    }],
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Campus Pulse</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Attendance trend, engagement, and event participation across campus.</p>

        <div className="grid sm:grid-cols-3 gap-4 mb-6">
          <StatCard label="Engagement Rate" value={`${data.engagement_rate_pct}%`} icon={FiTrendingUp} tone="success" />
          <StatCard label="Engaged Students" value={`${data.engaged_students} / ${data.total_students}`} icon={FiUsers} />
          <StatCard label="Event Participations" value={data.event_participation_count} icon={FiCalendar} tone="secondary" />
        </div>

        <div className="glass-card p-5">
          <p className="font-display font-semibold mb-4">Attendance trend — last 14 days</p>
          <Line data={chartData} options={{ responsive: true, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100, ticks: { callback: (v) => `${v}%` } } } }} height={90} />
        </div>
      </div>
    </DashboardLayout>
  );
}
