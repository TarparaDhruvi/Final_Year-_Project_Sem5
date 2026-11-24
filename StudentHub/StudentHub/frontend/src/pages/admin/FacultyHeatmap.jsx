import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiTrendingDown, FiEye, FiAlertTriangle } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";

export default function FacultyHeatmap() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/analytics/faculty-heatmap").then(({ data }) => setData(data)).catch(() => toast.error("Failed to load heatmap."));
  }, []);

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Faculty Heatmap</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Hardest subjects, most-viewed notes, and assignment delay patterns — all computed from live data.</p>

        {!data ? (
          <p className="text-center py-16 text-slate-400">Loading...</p>
        ) : (
          <div className="grid lg:grid-cols-3 gap-4">
            <div className="glass-card p-5">
              <p className="font-display font-semibold mb-4 flex items-center gap-2"><FiTrendingDown className="text-danger" /> Hardest Subjects</p>
              {data.hardest_subjects.length === 0 ? <p className="text-sm text-slate-400">No marks data yet.</p> : (
                <div className="space-y-2">
                  {data.hardest_subjects.map((s) => (
                    <div key={s.subject_id} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 dark:bg-white/5">
                      <div><p className="text-sm font-medium">{s.subject_name}</p><p className="text-xs text-slate-400">{s.sample_size} students</p></div>
                      <span className="text-sm font-display font-bold text-danger">{s.avg_internal_marks}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="glass-card p-5">
              <p className="font-display font-semibold mb-4 flex items-center gap-2"><FiEye className="text-primary" /> Most-Viewed Notes</p>
              {data.most_viewed_notes.length === 0 ? <p className="text-sm text-slate-400">No notes viewed yet.</p> : (
                <div className="space-y-2">
                  {data.most_viewed_notes.map((n) => (
                    <div key={n.id} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 dark:bg-white/5">
                      <p className="text-sm font-medium truncate">{n.title}</p>
                      <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary font-medium flex-shrink-0">{n.views} views</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="glass-card p-5">
              <p className="font-display font-semibold mb-4 flex items-center gap-2"><FiAlertTriangle className="text-warning" /> Assignment Delay Patterns</p>
              {data.assignment_delay_patterns.length === 0 ? <p className="text-sm text-slate-400">No assignment data yet.</p> : (
                <div className="space-y-2">
                  {data.assignment_delay_patterns.map((s) => (
                    <div key={s.subject_id} className="p-2.5 rounded-lg bg-slate-50 dark:bg-white/5">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium">{s.subject_name}</p>
                        <span className="text-xs font-bold text-warning">{s.delay_rate_pct}%</span>
                      </div>
                      <div className="w-full h-1.5 rounded-full bg-slate-200 dark:bg-white/10 mt-1.5 overflow-hidden">
                        <div className="h-full bg-warning rounded-full" style={{ width: `${s.delay_rate_pct}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
