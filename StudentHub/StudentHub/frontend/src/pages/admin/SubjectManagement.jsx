import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiPlus, FiEdit2, FiTrash2 } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import api from "../../services/api";

const DEPARTMENTS = ["Computer Science", "Information Technology", "Electronics & Communication", "Electrical Engineering", "Mechanical Engineering", "Civil Engineering", "Commerce", "Science", "Law", "Other"];
const EMPTY_FORM = { name: "", code: "", department: DEPARTMENTS[0], semester: 1, credits: 3, faculty_ids: [] };

export default function SubjectManagement() {
  const [subjects, setSubjects] = useState([]);
  const [facultyList, setFacultyList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [{ data: s }, { data: f }] = await Promise.all([api.get("/subjects"), api.get("/faculty")]);
      setSubjects(s);
      setFacultyList(f);
    } catch {
      toast.error("Failed to load subjects.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const openCreate = () => { setEditing(null); setForm(EMPTY_FORM); setErrors({}); setModalOpen(true); };
  const openEdit = (s) => {
    setEditing(s);
    setForm({ name: s.name, code: s.code, department: s.department, semester: s.semester, credits: s.credits, faculty_ids: s.faculty_ids || [] });
    setErrors({});
    setModalOpen(true);
  };

  const validate = () => {
    const next = {};
    if (!form.name.trim()) next.name = "Subject name is required.";
    if (!editing && !form.code.trim()) next.code = "Subject code is required.";
    const sem = Number(form.semester);
    if (!sem || sem < 1 || sem > 8) next.semester = "Semester must be between 1 and 8.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      if (editing) {
        await api.put(`/subjects/${editing.id}`, { name: form.name, faculty_ids: form.faculty_ids, semester: Number(form.semester), credits: Number(form.credits) });
        toast.success("Subject updated.");
      } else {
        await api.post("/subjects", { ...form, semester: Number(form.semester), credits: Number(form.credits), faculty_ids: form.faculty_ids });
        toast.success("Subject created.");
      }
      setModalOpen(false);
      load();
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(Array.isArray(detail) ? detail[0]?.msg : detail || "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.delete(`/subjects/${confirmDelete.id}`);
      toast.success("Subject deleted.");
      setConfirmDelete(null);
      load();
    } catch {
      toast.error("Failed to delete subject.");
    }
  };

  const toggleFaculty = (fid) => setForm((f) => ({ ...f, faculty_ids: f.faculty_ids.includes(fid) ? f.faculty_ids.filter((x) => x !== fid) : [...f.faculty_ids, fid] }));

  return (
    <DashboardLayout>
      <div className="pt-2">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-display font-bold">Subject Management</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{subjects.length} subject{subjects.length !== 1 ? "s" : ""}</p>
          </div>
          <button onClick={openCreate} className="btn-primary flex items-center gap-2 !py-2.5"><FiPlus /> Add Subject</button>
        </div>

        <div className="glass-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-slate-200 dark:border-white/10 text-slate-500 dark:text-slate-400">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Code</th>
                <th className="px-4 py-3 font-medium">Department</th>
                <th className="px-4 py-3 font-medium">Sem</th>
                <th className="px-4 py-3 font-medium">Faculty (can be several)</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-center py-10 text-slate-400">Loading...</td></tr>
              ) : subjects.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-10 text-slate-400">No subjects yet.</td></tr>
              ) : subjects.map((s) => (
                <tr key={s.id} className="border-b border-slate-100 dark:border-white/5 last:border-0">
                  <td className="px-4 py-3 font-medium">{s.name}</td>
                  <td className="px-4 py-3">{s.code}</td>
                  <td className="px-4 py-3">{s.department}</td>
                  <td className="px-4 py-3">{s.semester}</td>
                  <td className="px-4 py-3">
                    {(s.faculty || []).length === 0 ? <span className="text-slate-400">Unassigned</span> : (
                      <div className="flex flex-wrap gap-1">
                        {s.faculty.map((f) => <span key={f.faculty_id} className="text-[11px] px-2 py-0.5 rounded-full bg-secondary/10 text-secondary font-medium">{f.full_name}</span>)}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => openEdit(s)} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 text-primary"><FiEdit2 /></button>
                      <button onClick={() => setConfirmDelete(s)} className="p-2 rounded-lg hover:bg-danger/10 text-danger"><FiTrash2 /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit Subject" : "Add Subject"}>
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">Subject name</label>
            <input className="input-field" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            {errors.name && <p className="input-error">{errors.name}</p>}
          </div>
          {!editing && (
            <div>
              <label className="text-sm font-medium mb-1 block">Subject code</label>
              <input className="input-field" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="CS301" />
              {errors.code && <p className="input-error">{errors.code}</p>}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1 block">Department</label>
              <select className="input-field" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} disabled={!!editing}>
                {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Semester</label>
              <select className="input-field" value={form.semester} onChange={(e) => setForm({ ...form, semester: e.target.value })}>
                {[1,2,3,4,5,6,7,8].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              {errors.semester && <p className="input-error">{errors.semester}</p>}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1 block">Credits</label>
              <input type="number" min="1" max="10" className="input-field" value={form.credits} onChange={(e) => setForm({ ...form, credits: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Faculty teaching this subject (optional — pick as many as needed)</label>
            <div className="max-h-36 overflow-y-auto rounded-xl border border-slate-200 dark:border-white/10 divide-y divide-slate-100 dark:divide-white/5">
              {facultyList.length === 0 ? <p className="p-3 text-sm text-slate-400">No faculty yet.</p> : facultyList.map((f) => (
                <label key={f.id} className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5">
                  <input type="checkbox" checked={form.faculty_ids.includes(f.faculty_id)} onChange={() => toggleFaculty(f.faculty_id)} className="rounded border-slate-300 text-primary focus:ring-primary" />
                  <span className="text-sm">{f.full_name} <span className="text-slate-400 text-xs">· ID {f.faculty_id}</span></span>
                </label>
              ))}
            </div>
          </div>
          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
            {submitting ? "Saving..." : editing ? "Save Changes" : "Create Subject"}
          </button>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!confirmDelete}
        title="Delete subject?"
        message={`This will permanently delete "${confirmDelete?.name}".`}
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(null)}
      />
    </DashboardLayout>
  );
}
