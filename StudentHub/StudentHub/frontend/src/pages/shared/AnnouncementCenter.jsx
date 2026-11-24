import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiPlus, FiVolume2, FiClock } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Modal from "../../components/Modal";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

const DEPARTMENTS = ["Computer Science", "Information Technology", "Electronics & Communication", "Electrical Engineering", "Mechanical Engineering", "Civil Engineering", "Commerce", "Science", "Law", "Other"];
const today = () => new Date().toISOString().slice(0, 10);

export default function AnnouncementCenter() {
  const { user } = useAuth();
  const [announcements, setAnnouncements] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ title: "", message: "", target_type: "all", department: DEPARTMENTS[0], semester: 1, scheduled_for: "" });
  const [errors, setErrors] = useState({});

  const load = async () => {
    try {
      const { data } = await api.get("/announcements");
      setAnnouncements(data);
    } catch {
      toast.error("Failed to load announcements.");
    }
  };
  useEffect(() => { load(); }, []);

  const validate = () => {
    const next = {};
    if (!form.title.trim()) next.title = "Title is required.";
    if (!form.message.trim()) next.message = "Message is required.";
    if (form.scheduled_for && form.scheduled_for < today()) next.scheduled_for = "Scheduled date cannot be in the past.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      const payload = {
        title: form.title,
        message: form.message,
        target_type: user.role === "faculty" ? "all" : form.target_type,
        department: form.target_type !== "all" ? form.department : null,
        semester: form.target_type === "semester" ? Number(form.semester) : null,
        scheduled_for: form.scheduled_for || null,
      };
      const { data } = await api.post("/announcements", payload);
      toast.success(data.message);
      setModalOpen(false);
      setForm({ title: "", message: "", target_type: "all", department: DEPARTMENTS[0], semester: 1, scheduled_for: "" });
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
            <h1 className="text-2xl font-display font-bold">Announcement Center</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {user.role === "faculty" ? "Notify your assigned classes" : "Broadcast to everyone, a department, or a semester"}
            </p>
          </div>
          <button onClick={() => setModalOpen(true)} className="btn-primary flex items-center gap-2 !py-2.5"><FiPlus /> New Announcement</button>
        </div>

        <div className="space-y-3">
          {announcements.length === 0 ? (
            <p className="text-center py-10 text-slate-400">No announcements yet.</p>
          ) : announcements.map((a) => (
            <div key={a.id} className="glass-card p-5">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white flex-shrink-0"><FiVolume2 size={16} /></div>
                <div className="min-w-0">
                  <p className="font-semibold">{a.title}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{a.message}</p>
                  <p className="text-xs text-slate-400 mt-2 flex items-center gap-1"><FiClock /> {new Date(a.created_at).toLocaleString()} · {a.target_type}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New Announcement">
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">Title</label>
            <input className="input-field" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            {errors.title && <p className="input-error">{errors.title}</p>}
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Message</label>
            <textarea rows={4} className="input-field" value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
            {errors.message && <p className="input-error">{errors.message}</p>}
          </div>

          {user.role === "admin" && (
            <>
              <div>
                <label className="text-sm font-medium mb-1 block">Target</label>
                <select className="input-field" value={form.target_type} onChange={(e) => setForm({ ...form, target_type: e.target.value })}>
                  <option value="all">Everyone</option>
                  <option value="department">Specific Department</option>
                  <option value="semester">Specific Semester</option>
                </select>
              </div>
              {form.target_type !== "all" && (
                <div>
                  <label className="text-sm font-medium mb-1 block">Department</label>
                  <select className="input-field" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })}>
                    {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
              )}
              {form.target_type === "semester" && (
                <div>
                  <label className="text-sm font-medium mb-1 block">Semester</label>
                  <select className="input-field" value={form.semester} onChange={(e) => setForm({ ...form, semester: e.target.value })}>
                    {[1,2,3,4,5,6,7,8].map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              )}
            </>
          )}

          <div>
            <label className="text-sm font-medium mb-1 block">Schedule for later (optional)</label>
            <input type="date" min={today()} className="input-field" value={form.scheduled_for} onChange={(e) => setForm({ ...form, scheduled_for: e.target.value })} />
            {errors.scheduled_for && <p className="input-error">{errors.scheduled_for}</p>}
          </div>

          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
            {submitting ? "Publishing..." : "Publish Announcement"}
          </button>
        </form>
      </Modal>
    </DashboardLayout>
  );
}
