import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiCheck, FiX, FiClock } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";

const STATUS_STYLE = {
  pending: "bg-warning/10 text-warning",
  approved: "bg-success/10 text-success",
  rejected: "bg-danger/10 text-danger",
};

export default function LeaveManagement() {
  const [requests, setRequests] = useState([]);
  const [filter, setFilter] = useState("pending");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/leave", { params: filter ? { status: filter } : {} });
      setRequests(data);
    } catch {
      toast.error("Failed to load leave requests.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [filter]);

  const review = async (id, status) => {
    try {
      await api.put(`/leave/${id}/review`, { status });
      toast.success(`Leave request ${status}.`);
      load();
    } catch {
      toast.error("Failed to update leave request.");
    }
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-display font-bold">Leave Management</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Review and respond to leave requests</p>
          </div>
          <div className="flex gap-2">
            {["pending", "approved", "rejected", ""].map((s) => (
              <button
                key={s || "all"}
                onClick={() => setFilter(s)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors ${filter === s ? "bg-primary text-white" : "glass-card text-slate-500"}`}
              >
                {s || "All"}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          {loading ? (
            <p className="text-center py-10 text-slate-400">Loading...</p>
          ) : requests.length === 0 ? (
            <p className="text-center py-10 text-slate-400">No leave requests found.</p>
          ) : requests.map((r) => (
            <div key={r.id} className="glass-card p-5 flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <p className="font-semibold">{r.full_name}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full capitalize font-medium ${STATUS_STYLE[r.status]}`}>{r.status}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-white/10 capitalize">{r.role}</span>
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400">{r.reason}</p>
                <p className="text-xs text-slate-400 flex items-center gap-1 mt-1"><FiClock /> {r.from_date} → {r.to_date}</p>
              </div>
              {r.status === "pending" && (
                <div className="flex gap-2">
                  <button onClick={() => review(r.id, "approved")} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-success/10 text-success text-sm font-medium hover:bg-success/20"><FiCheck /> Approve</button>
                  <button onClick={() => review(r.id, "rejected")} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-danger/10 text-danger text-sm font-medium hover:bg-danger/20"><FiX /> Reject</button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
