import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";

export default function StudentMarks() {
  const [marks, setMarks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/marks/mine")
      .then(({ data }) => setMarks(data))
      .catch(() => toast.error("Failed to load marks."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Marks</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Your published internal and practical marks</p>

        {loading ? (
          <p className="text-center py-16 text-slate-400">Loading...</p>
        ) : marks.length === 0 ? (
          <p className="text-center py-16 text-slate-400">No published marks yet.</p>
        ) : (
          <div className="glass-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-slate-200 dark:border-white/10 text-slate-500 dark:text-slate-400">
                  <th className="px-4 py-3 font-medium">Subject</th>
                  <th className="px-4 py-3 font-medium">Internal (/100)</th>
                  <th className="px-4 py-3 font-medium">Practical (/100)</th>
                </tr>
              </thead>
              <tbody>
                {marks.map((m) => (
                  <tr key={m.id} className="border-b border-slate-100 dark:border-white/5 last:border-0">
                    <td className="px-4 py-3 font-medium">{m.subject_name}</td>
                    <td className="px-4 py-3">{m.internal ?? "—"}</td>
                    <td className="px-4 py-3">{m.practical ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
