import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiPlus, FiEdit2, FiTrash2, FiLink, FiEye, FiEyeOff, FiX } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import PasswordStrengthMeter from "../../components/PasswordStrengthMeter";
import api from "../../services/api";

const DEPARTMENTS = ["Computer Science", "Information Technology", "Electronics & Communication", "Electrical Engineering", "Mechanical Engineering", "Civil Engineering", "Commerce", "Science", "Law", "Other"];
const NAME_REGEX = /^[A-Za-z ]{3,30}$/;
const GMAIL_REGEX = /^[a-zA-Z0-9](\.?[a-zA-Z0-9_-]){0,63}@gmail\.com$/;
const PHONE_REGEX = /^[0-9]{10}$/;
const ID_REGEX = /^[0-9]+$/;

function validatePassword(password) {
  if (password.length < 8) return "Password must be at least 8 characters long.";
  if (!/[A-Z]/.test(password)) return "Include at least one uppercase letter.";
  if (!/[a-z]/.test(password)) return "Include at least one lowercase letter.";
  if (!/[0-9]/.test(password)) return "Include at least one number.";
  if (!/[!@#$%^&*(),.?":{}|<>_\-+=[\]/\\;']/.test(password)) return "Include at least one special character.";
  return null;
}

const EMPTY_FORM = { full_name: "", email: "", phone: "", faculty_id: "", department: DEPARTMENTS[0], designation: "", password: "", confirm_password: "" };

export default function FacultyManagement() {
  const [facultyList, setFacultyList] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [assignModal, setAssignModal] = useState(null);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [selectedSubjects, setSelectedSubjects] = useState([]);
  const [confirmRemove, setConfirmRemove] = useState(null);   // { faculty, subject } — remove ONE assignment
  const [assignBusy, setAssignBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [{ data: f }, { data: s }] = await Promise.all([api.get("/faculty"), api.get("/subjects")]);
      setFacultyList(f);
      setSubjects(s);
    } catch {
      toast.error("Failed to load faculty.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => { setEditing(null); setForm(EMPTY_FORM); setErrors({}); setShowPassword(false); setShowConfirmPassword(false); setModalOpen(true); };
  const openEdit = (f) => {
    setEditing(f);
    setForm({ ...EMPTY_FORM, full_name: f.full_name || "", email: f.email || "", phone: f.phone || "", faculty_id: f.faculty_id, department: f.department, designation: f.designation || "" });
    setErrors({});
    setModalOpen(true);
  };

  const validate = () => {
    const next = {};
    if (!NAME_REGEX.test(form.full_name.trim())) next.full_name = "Name must be 3–30 letters only.";
    if (!PHONE_REGEX.test(form.phone.trim())) next.phone = "Phone number must be exactly 10 digits.";
    if (!editing) {
      if (!GMAIL_REGEX.test(form.email.trim().toLowerCase())) next.email = "Only Gmail addresses (@gmail.com) are allowed.";
      if (!ID_REGEX.test(form.faculty_id.trim())) next.faculty_id = "Faculty ID must contain numbers only.";
      const pwErr = validatePassword(form.password);
      if (pwErr) next.password = pwErr;
      if (form.confirm_password !== form.password) next.confirm_password = "Passwords do not match.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      if (editing) {
        await api.put(`/faculty/${editing.id}`, { full_name: form.full_name, phone: form.phone, department: form.department, designation: form.designation || null });
        toast.success("Faculty member updated.");
      } else {
        await api.post("/faculty", form);
        toast.success("Faculty member created. Share the Faculty ID and password with them directly.");
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
      await api.delete(`/faculty/${confirmDelete.id}`);
      toast.success("Faculty member deleted.");
      setConfirmDelete(null);
      load();
    } catch {
      toast.error("Failed to delete faculty member.");
    }
  };

  const openAssign = (f) => {
    setAssignModal(f);
    setSelectedSubjects(f.subject_ids || []);
  };

  const toggleSubject = (id) => {
    setSelectedSubjects((prev) => prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]);
  };

  const apiMessage = (err, fallback) => {
    const d = err.response?.data?.detail;
    return Array.isArray(d) ? d[0]?.msg : typeof d === "string" ? d : fallback;
  };

  // Saves THIS faculty member's list only. A subject keeps every other teacher it already has.
  const saveAssign = async () => {
    setAssignBusy(true);
    try {
      await api.put(`/faculty/${assignModal.id}/assign-subjects`, { subject_ids: selectedSubjects });
      toast.success("Assignments saved. Other faculty teaching the same subjects are unaffected.");
      setAssignModal(null);
      load();
    } catch (err) {
      toast.error(apiMessage(err, "Failed to assign subjects."));
    } finally {
      setAssignBusy(false);
    }
  };

  const removeOne = async () => {
    const { faculty: f, subject: s } = confirmRemove;
    try {
      await api.delete(`/faculty/${f.id}/subjects/${s.id}`);
      toast.success(`${s.name} removed from ${f.full_name}.`);
      setConfirmRemove(null);
      load();
    } catch (err) {
      toast.error(apiMessage(err, "Couldn't remove that assignment."));
      setConfirmRemove(null);
      load();
    }
  };

  // Move one subject from the faculty member in the modal to another faculty member.
  const reassign = async (subject, toFacultyId) => {
    if (!toFacultyId) return;
    setAssignBusy(true);
    try {
      await api.post(`/faculty/${assignModal.id}/subjects/${subject.id}/reassign`, { to_faculty_id: toFacultyId });
      toast.success(`${subject.name} reassigned.`);
      setAssignModal(null);
      load();
    } catch (err) {
      toast.error(apiMessage(err, "Couldn't reassign that subject."));
    } finally {
      setAssignBusy(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-display font-bold">Faculty Management</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{facultyList.length} faculty member{facultyList.length !== 1 ? "s" : ""}</p>
          </div>
          <button onClick={openCreate} className="btn-primary flex items-center gap-2 !py-2.5">
            <FiPlus /> Add Faculty
          </button>
        </div>

        <div className="glass-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-slate-200 dark:border-white/10 text-slate-500 dark:text-slate-400">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Faculty ID</th>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Department</th>
                <th className="px-4 py-3 font-medium">Subjects</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-center py-10 text-slate-400">Loading...</td></tr>
              ) : facultyList.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-10 text-slate-400">No faculty members yet.</td></tr>
              ) : facultyList.map((f) => (
                <tr key={f.id} className="border-b border-slate-100 dark:border-white/5 last:border-0">
                  <td className="px-4 py-3 font-medium">{f.full_name}</td>
                  <td className="px-4 py-3">{f.faculty_id}</td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{f.email}</td>
                  <td className="px-4 py-3">{f.department}</td>
                  <td className="px-4 py-3">
                    {(f.subject_ids || []).length === 0 ? (
                      <span className="text-slate-400">None</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {(f.subject_ids || []).map((id) => {
                          const subj = subjects.find((s) => s.id === id);
                          return (
                            <span key={id} className="inline-flex items-center gap-1 text-[11px] pl-2 pr-1 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                              {subj?.name || "Subject"}
                              {subj && (
                                <button type="button" onClick={() => setConfirmRemove({ faculty: f, subject: subj })} aria-label={`Remove ${subj.name} from ${f.full_name}`} title="Remove this subject from this faculty member" className="rounded-full hover:bg-primary/20 p-0.5"><FiX size={10} /></button>
                              )}
                            </span>
                          );
                        })}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => openAssign(f)} title="Assign subjects" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 text-secondary"><FiLink /></button>
                      <button onClick={() => openEdit(f)} title="Edit" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 text-primary"><FiEdit2 /></button>
                      <button onClick={() => setConfirmDelete(f)} title="Delete" className="p-2 rounded-lg hover:bg-danger/10 text-danger"><FiTrash2 /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit Faculty" : "Add Faculty"}>
        {!editing && (
          <p className="text-xs text-slate-400 mb-4 -mt-2">
            Set the Faculty ID and password directly — share both with the faculty member yourself.
          </p>
        )}
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">Full name</label>
            <input className="input-field" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            {errors.full_name && <p className="input-error">{errors.full_name}</p>}
          </div>
          {!editing && (
            <>
              <div>
                <label className="text-sm font-medium mb-1 block">Gmail address</label>
                <input type="email" className="input-field" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                {errors.email && <p className="input-error">{errors.email}</p>}
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Faculty ID</label>
                <input className="input-field" value={form.faculty_id} onChange={(e) => setForm({ ...form, faculty_id: e.target.value })} />
                {errors.faculty_id && <p className="input-error">{errors.faculty_id}</p>}
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    className="input-field pr-11"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    placeholder="Set a password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
                    aria-label="Toggle password visibility"
                  >
                    {showPassword ? <FiEyeOff /> : <FiEye />}
                  </button>
                </div>
                <PasswordStrengthMeter password={form.password} />
                {errors.password && <p className="input-error">{errors.password}</p>}
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Confirm password</label>
                <div className="relative">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    className="input-field pr-11"
                    value={form.confirm_password}
                    onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
                    placeholder="Re-enter the password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
                    aria-label="Toggle password visibility"
                  >
                    {showConfirmPassword ? <FiEyeOff /> : <FiEye />}
                  </button>
                </div>
                {errors.confirm_password && <p className="input-error">{errors.confirm_password}</p>}
              </div>
            </>
          )}
          <div>
            <label className="text-sm font-medium mb-1 block">Phone</label>
            <input className="input-field" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            {errors.phone && <p className="input-error">{errors.phone}</p>}
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Department</label>
            <select className="input-field" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })}>
              {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Designation (optional)</label>
            <input className="input-field" value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} placeholder="Assistant Professor" />
          </div>
          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
            {submitting ? "Saving..." : editing ? "Save Changes" : "Create Faculty"}
          </button>
        </form>
      </Modal>

      <Modal open={!!assignModal} onClose={() => setAssignModal(null)} title={`Assign Subjects — ${assignModal?.full_name}`}>
        <p className="text-xs text-slate-400 mb-3 -mt-2">
          A subject can be taught by several faculty. Ticking a subject adds it for {assignModal?.full_name} only; it never removes it from anyone else.
        </p>
        <div className="space-y-2 max-h-80 overflow-y-auto mb-4">
          {subjects.length === 0 ? (
            <p className="text-sm text-slate-400">No subjects created yet.</p>
          ) : subjects.map((s) => {
            const others = (s.faculty || []).filter((x) => x.faculty_id !== assignModal?.faculty_id);
            const saved = (assignModal?.subject_ids || []).includes(s.id);
            return (
              <div key={s.id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 dark:hover:bg-white/5">
                <input id={`as-${s.id}`} type="checkbox" checked={selectedSubjects.includes(s.id)} onChange={() => toggleSubject(s.id)} className="rounded border-slate-300 text-primary focus:ring-primary" />
                <label htmlFor={`as-${s.id}`} className="flex-1 min-w-0 cursor-pointer">
                  <p className="text-sm font-medium">{s.name} <span className="text-slate-400 font-normal">({s.code})</span></p>
                  <p className="text-xs text-slate-400">{s.department} · Semester {s.semester}</p>
                  {others.length > 0 && <p className="text-[11px] text-secondary mt-0.5">Also taught by: {others.map((x) => x.full_name).join(", ")}</p>}
                </label>
                {saved && (
                  <select aria-label={`Reassign ${s.name}`} disabled={assignBusy} value="" onChange={(e) => reassign(s, e.target.value)} className="input-field !py-1 !px-2 !text-xs w-auto max-w-[130px]">
                    <option value="">Reassign…</option>
                    {facultyList.filter((x) => x.faculty_id !== assignModal?.faculty_id).map((x) => <option key={x.id} value={x.faculty_id}>{x.full_name}</option>)}
                  </select>
                )}
              </div>
            );
          })}
        </div>
        <button onClick={saveAssign} disabled={assignBusy} className="btn-primary w-full disabled:opacity-60">{assignBusy ? "Saving..." : "Save Assignment"}</button>
      </Modal>

      <ConfirmDialog
        open={!!confirmRemove}
        title="Remove this subject?"
        message={`${confirmRemove?.subject?.name} will be removed from ${confirmRemove?.faculty?.full_name} only. Other faculty teaching it keep it, and all marks, attendance and notes are kept.`}
        confirmLabel="Remove"
        onConfirm={removeOne}
        onCancel={() => setConfirmRemove(null)}
      />

      <ConfirmDialog
        open={!!confirmDelete}
        title="Delete faculty member?"
        message={`This permanently deletes ${confirmDelete?.full_name}'s account and removes their subject assignments. The subjects themselves, and any co-teachers, are not affected.`}
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(null)}
      />
    </DashboardLayout>
  );
}
