import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiVolume2, FiClock } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";

export default function AnnouncementsView() {
  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/announcements")
      .then(({ data }) => setAnnouncements(data))
      .catch(() => toast.error("Failed to load announcements."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Announcements</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Notices from your Admin and Faculty</p>

        <div className="space-y-3">
          {loading ? (
            <p className="text-center py-10 text-slate-400">Loading...</p>
          ) : announcements.length === 0 ? (
            <p className="text-center py-10 text-slate-400">No announcements yet.</p>
          ) : announcements.map((a) => (
            <div key={a.id} className="glass-card p-5">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white flex-shrink-0"><FiVolume2 size={16} /></div>
                <div className="min-w-0">
                  <p className="font-semibold">{a.title}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{a.message}</p>
                  <p className="text-xs text-slate-400 mt-2 flex items-center gap-1"><FiClock /> {new Date(a.created_at).toLocaleString()}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
