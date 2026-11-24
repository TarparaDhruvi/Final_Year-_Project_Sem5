import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiPlus, FiClock } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Modal from "../../components/Modal";
import api from "../../services/api";

const STATUS_STYLE = {
  pending: "bg-warning/10 text-warning",
  approved: "bg-success/10 text-success",
  rejected: "bg-danger/10 text-danger",
};
const today = () => new Date().toISOString().slice(0, 10);

export default function LeaveApply() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ reason: "", from_date: today(), to_date: today() });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/leave/mine");
      setHistory(data);
    } catch {
      toast.error("Failed to load leave history.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const validate = () => {
    const next = {};
    if (!form.reason.trim()) next.reason = "Please provide a reason.";
    if (form.from_date < today()) next.from_date = "Leave start date cannot be in the past.";
    if (form.to_date < form.from_date) next.to_date = "End date cannot be before the start date.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      await api.post("/leave", form);
      toast.success("Leave request submitted.");
      setModalOpen(false);
      setForm({ reason: "", from_date: today(), to_date: today() });
      load();
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(Array.isArray(detail) ? detail[0]?.msg : detail || "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-display font-bold">Leave</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Apply for leave and track your requests</p>
          </div>
          <button onClick={() => setModalOpen(true)} className="btn-primary flex items-center gap-2 !py-2.5"><FiPlus /> Apply for Leave</button>
        </div>

        <div className="space-y-3">
          {loading ? (
            <p className="text-center py-10 text-slate-400">Loading...</p>
          ) : history.length === 0 ? (
            <p className="text-center py-10 text-slate-400">No leave requests yet.</p>
          ) : history.map((r) => (
            <div key={r.id} className="glass-card p-5">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs px-2 py-0.5 rounded-full capitalize font-medium ${STATUS_STYLE[r.status]}`}>{r.status}</span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-300">{r.reason}</p>
              <p className="text-xs text-slate-400 flex items-center gap-1 mt-1"><FiClock /> {r.from_date} → {r.to_date}</p>
            </div>
          ))}
        </div>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Apply for Leave">
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">Reason</label>
            <textarea rows={3} className="input-field" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
            {errors.reason && <p className="input-error">{errors.reason}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1 block">From</label>
              <input type="date" min={today()} className="input-field" value={form.from_date} onChange={(e) => setForm({ ...form, from_date: e.target.value })} />
              {errors.from_date && <p className="input-error">{errors.from_date}</p>}
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">To</label>
              <input type="date" min={form.from_date} className="input-field" value={form.to_date} onChange={(e) => setForm({ ...form, to_date: e.target.value })} />
              {errors.to_date && <p className="input-error">{errors.to_date}</p>}
            </div>
          </div>
          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
            {submitting ? "Submitting..." : "Submit Request"}
          </button>
        </form>
      </Modal>
    </DashboardLayout>
  );
}
