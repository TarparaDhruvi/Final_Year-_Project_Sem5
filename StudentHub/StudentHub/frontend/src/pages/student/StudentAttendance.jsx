import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiAlertTriangle } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";

export default function StudentAttendance() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/attendance/me")
      .then(({ data }) => setRows(data))
      .catch(() => toast.error("Failed to load attendance."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Attendance</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Subject-wise attendance with a simple risk prediction</p>

        {loading ? (
          <p className="text-center py-16 text-slate-400">Loading...</p>
        ) : rows.length === 0 ? (
          <p className="text-center py-16 text-slate-400">No attendance records yet.</p>
        ) : (
          <div className="grid sm:grid-cols-2 gap-4">
            {rows.map((r) => (
              <div key={r.subject_id} className="glass-card p-5">
                <div className="flex items-center justify-between mb-3">
                  <p className="font-semibold">{r.subject_name}</p>
                  {r.at_risk && <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-danger/10 text-danger font-medium"><FiAlertTriangle size={12} /> At risk</span>}
                </div>
                <div className="flex items-end gap-2 mb-2">
                  <p className={`text-3xl font-display font-bold ${r.at_risk ? "text-danger" : "text-primary"}`}>{r.percentage}%</p>
                  <p className="text-sm text-slate-400 mb-1">{r.present}/{r.total} classes</p>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden mb-3">
                  <div className={`h-full rounded-full ${r.at_risk ? "bg-danger" : "bg-gradient-to-r from-primary to-secondary"}`} style={{ width: `${Math.min(r.percentage, 100)}%` }} />
                </div>
                <p className="text-xs text-slate-400">
                  Skip 2 more classes and attendance becomes <strong className={r.prediction_after_2_more_absences < 75 ? "text-danger" : ""}>{r.prediction_after_2_more_absences}%</strong>.
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
