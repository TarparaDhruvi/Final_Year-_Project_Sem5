import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { FiUpload, FiFile, FiTrash2 } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Modal from "../../components/Modal";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

export default function FacultyNotes() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const [subjects, setSubjects] = useState([]);
  const [notes, setNotes] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ title: "", subject_id: "", unit: "" });
  const [file, setFile] = useState(null);
  const [errors, setErrors] = useState({});
  const [uploading, setUploading] = useState(false);

  const loadAll = async () => {
    const { data: mine } = await api.get("/faculty/me/subjects");
    setSubjects(mine);
    if (searchParams.get("upload") && mine.length) {       // "Upload Study Material" from the Classroom Activity Hub
      const wanted = searchParams.get("subject");
      setForm((f) => ({ ...f, subject_id: mine.some((s) => s.id === wanted) ? wanted : f.subject_id }));
      setModalOpen(true);
    }
    if (mine.length) {
      const all = [];
      for (const s of mine) {
        const { data } = await api.get("/notes", { params: { subject_id: s.id } });
        all.push(...data.map((n) => ({ ...n, subject_name: s.name })));
      }
      setNotes(all);
    }
  };
  useEffect(() => { loadAll(); }, [user.id]);

  const validate = () => {
    const next = {};
    if (!form.title.trim()) next.title = "Title is required.";
    if (!form.subject_id) next.subject_id = "Please select a subject.";
    if (!form.unit.trim()) next.unit = "Unit is required.";
    if (!file) next.file = "Please choose a file (PDF, PPT, DOCX, or image).";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("title", form.title);
      fd.append("subject_id", form.subject_id);
      fd.append("unit", form.unit);
      fd.append("file", file);
      await api.post("/notes/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Notes uploaded.");
      setModalOpen(false);
      setForm({ title: "", subject_id: "", unit: "" });
      setFile(null);
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/notes/${id}`);
      toast.success("Note deleted.");
      loadAll();
    } catch {
      toast.error("Failed to delete note.");
    }
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-display font-bold">Notes</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Upload study material for your subjects</p>
          </div>
          <button onClick={() => setModalOpen(true)} className="btn-primary flex items-center gap-2 !py-2.5"><FiUpload /> Upload Notes</button>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {notes.length === 0 ? (
            <p className="text-slate-400 col-span-full text-center py-10">No notes uploaded yet.</p>
          ) : notes.map((n) => (
            <div key={n.id} className="glass-card p-4">
              <div className="flex items-start justify-between">
                <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><FiFile /></div>
                <button onClick={() => handleDelete(n.id)} className="p-1.5 rounded-lg hover:bg-danger/10 text-danger"><FiTrash2 size={14} /></button>
              </div>
              <p className="font-medium text-sm mt-2">{n.title}</p>
              <p className="text-xs text-slate-400">{n.subject_name} · Unit {n.unit} · {n.file_type.toUpperCase()}</p>
              <a href={n.file_url} target="_blank" rel="noreferrer" className="text-primary text-xs font-medium hover:underline mt-2 inline-block">Open file</a>
            </div>
          ))}
        </div>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Upload Notes">
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
            <input className="input-field" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Unit 3 — Sorting Algorithms" />
            {errors.title && <p className="input-error">{errors.title}</p>}
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Unit</label>
            <input className="input-field" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} placeholder="Unit 3" />
            {errors.unit && <p className="input-error">{errors.unit}</p>}
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">File (PDF, PPT, DOCX, JPG, PNG)</label>
            <input type="file" accept=".pdf,.ppt,.pptx,.doc,.docx,.jpg,.jpeg,.png" className="input-field" onChange={(e) => setFile(e.target.files[0])} />
            {errors.file && <p className="input-error">{errors.file}</p>}
          </div>
          <button type="submit" disabled={uploading} className="btn-primary w-full disabled:opacity-60">
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </form>
      </Modal>
    </DashboardLayout>
  );
}
