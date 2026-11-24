import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiAlertCircle, FiUser } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";

export default function SilentStudentFinder() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/analytics/silent-students").then(({ data }) => setData(data)).catch(() => toast.error("Failed to load analysis."));
  }, []);

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Silent Student Finder</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Students flagged for low attendance, missed deadlines, or no recorded engagement.</p>

        {!data ? (
          <p className="text-center py-16 text-slate-400">Analysing...</p>
        ) : data.students.length === 0 ? (
          <div className="glass-card p-10 text-center text-slate-400">No students flagged right now — everyone looks engaged!</div>
        ) : (
          <>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">{data.flagged_count} student{data.flagged_count !== 1 ? "s" : ""} flagged</p>
            <div className="space-y-3">
              {data.students.map((s) => (
                <div key={s.student_id} className="glass-card p-4 flex flex-wrap items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-xl bg-danger/10 text-danger flex items-center justify-center flex-shrink-0"><FiUser /></div>
                    <div>
                      <p className="font-medium">{s.full_name} <span className="text-xs text-slate-400 font-normal">· {s.roll_no}</span></p>
                      <p className="text-xs text-slate-400">{s.department} · Semester {s.semester}</p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {s.flags.map((f, i) => (
                          <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-danger/10 text-danger font-medium flex items-center gap-1"><FiAlertCircle size={10} /> {f}</span>
                        ))}
                      </div>
                      <p className="text-xs text-slate-400 mt-1.5 italic">{s.suggestion}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
