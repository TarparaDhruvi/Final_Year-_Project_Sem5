import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { FiPlus, FiUsers, FiClock, FiActivity } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Modal from "../../components/Modal";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

const pad2 = (n) => String(n).padStart(2, "0");
const today = () => { const d = new Date(); return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`; };

export default function FacultyAssignments() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const [subjects, setSubjects] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [submissionsModal, setSubmissionsModal] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [form, setForm] = useState({ title: "", description: "", subject_id: "", due_date: today() });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [gradeInputs, setGradeInputs] = useState({});

  const loadSubjects = async () => {
    const { data: mine } = await api.get("/faculty/me/subjects");
    setSubjects(mine);
    const wanted = searchParams.get("subject");
    if (searchParams.get("new") && mine.length) {          // "Manage Assignments → New" from the Classroom Activity Hub
      setForm((f) => ({ ...f, subject_id: mine.some((s) => s.id === wanted) ? wanted : f.subject_id }));
      setModalOpen(true);
    }
    if (mine.length) {
      const all = [];
      for (const s of mine) {
        const { data } = await api.get(`/assignments/subject/${s.id}`);
        all.push(...data.map((a) => ({ ...a, subject_name: s.name })));
      }
      setAssignments(all);
    }
  };
  useEffect(() => { loadSubjects(); }, [user.id]);

  const validate = () => {
    const next = {};
    if (!form.title.trim()) next.title = "Title is required.";
    if (!form.description.trim()) next.description = "Description is required.";
    if (!form.subject_id) next.subject_id = "Please select a subject.";
    if (form.due_date < today()) next.due_date = "Due date cannot be in the past.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      await api.post("/assignments", form);
      toast.success("Assignment created.");
      setModalOpen(false);
      setForm({ title: "", description: "", subject_id: "", due_date: today() });
      loadSubjects();
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(Array.isArray(detail) ? detail[0]?.msg : detail || "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  };

  const openSubmissions = async (a) => {
    setSubmissionsModal(a);
    try {
      const { data } = await api.get(`/assignments/${a.id}/submissions`);
      setSubmissions(data);
    } catch {
      toast.error("Failed to load submissions.");
    }
  };

  const grade = async (submissionId) => {
    const g = gradeInputs[submissionId];
    if (!g) return;
    try {
      await api.put(`/assignments/submissions/${submissionId}/grade`, { grade: g });
      toast.success("Graded.");
      openSubmissions(submissionsModal);
    } catch {
      toast.error("Failed to grade submission.");
    }
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-display font-bold">Assignments</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Create assignments and grade submissions</p>
          </div>
          <button onClick={() => setModalOpen(true)} className="btn-primary flex items-center gap-2 !py-2.5"><FiPlus /> New Assignment</button>
        </div>

        <div className="space-y-3">
          {assignments.length === 0 ? (
            <p className="text-center py-10 text-slate-400">No assignments yet — assign yourself subjects first via Admin, or create one above.</p>
          ) : assignments.map((a) => (
            <div key={a.id} className="glass-card p-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-semibold">{a.title}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400">{a.subject_name}</p>
                <p className="text-xs text-slate-400 flex items-center gap-1 mt-1"><FiClock /> Due {a.due_date}</p>
              </div>
              <button onClick={() => openSubmissions(a)} className="btn-secondary !py-2 flex items-center gap-2 text-sm"><FiUsers /> View Submissions</button>
            </div>
          ))}
        </div>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New Assignment">
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">Subject</label>
            <select className="input-field" value={form.subject_id} onChange={(e) => setForm({ ...form, subject_id: e.target.value })}>
              <option value="">Select subject</option>
              {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            {errors.subject_id && <p className="input-error">{errors.subject_id}</p>}
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Title</label>
            <input className="input-field" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            {errors.title && <p className="input-error">{errors.title}</p>}
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Instructions</label>
            <textarea rows={4} className="input-field" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            {errors.description && <p className="input-error">{errors.description}</p>}
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Due date</label>
            <input type="date" min={today()} className="input-field" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
            {errors.due_date && <p className="input-error">{errors.due_date}</p>}
          </div>
          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
            {submitting ? "Creating..." : "Create Assignment"}
          </button>
        </form>
      </Modal>

      <Modal open={!!submissionsModal} onClose={() => setSubmissionsModal(null)} title={`Submissions — ${submissionsModal?.title}`} maxWidth="max-w-2xl">
        {submissions.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-8">No submissions yet.</p>
        ) : (
          <div className="space-y-3">
            {submissions.map((s) => (
              <div key={s.id} className="glass-card p-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="font-medium text-sm">{s.student_name}</p>
                    <p className="text-xs text-slate-400">{s.student_roll} · {s.status}</p>
                  </div>
                  {s.file_url && <a href={s.file_url} target="_blank" rel="noreferrer" className="text-primary text-xs font-medium hover:underline">View file</a>}
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
                  <FiActivity /> {(s.timeline || []).map((t) => t.event).join(" → ")}
                </div>
                {s.grade ? (
                  <p className="text-sm"><span className="font-semibold text-success">Grade: {s.grade}</span></p>
                ) : (
                  <div className="flex gap-2">
                    <input
                      className="input-field !py-1.5 text-sm flex-1"
                      placeholder="Grade (e.g. A, 85)"
                      value={gradeInputs[s.id] || ""}
                      onChange={(e) => setGradeInputs({ ...gradeInputs, [s.id]: e.target.value })}
                    />
                    <button onClick={() => grade(s.id)} className="btn-primary !py-1.5 !px-4 text-sm">Grade</button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Modal>
    </DashboardLayout>
  );
}
