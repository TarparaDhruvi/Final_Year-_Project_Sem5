import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiPlus, FiSearch, FiEdit2, FiTrash2, FiKey, FiUpload, FiDownload, FiCheckCircle, FiXCircle, FiEye, FiUserX, FiUserCheck } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import { downloadReport } from "../../utils/download";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
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

const errMsg = (err, fallback) => {
  const d = err.response?.data?.detail;
  if (Array.isArray(d)) return d[0]?.msg?.replace(/^Value error, /, "") || fallback;
  return d || fallback;
};

const EMPTY_FORM = { full_name: "", email: "", phone: "", password: "", student_id: "", department: DEPARTMENTS[0], semester: 1, batch: "" };

export default function StudentManagement() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("");
  const [semFilter, setSemFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [confirmStatus, setConfirmStatus] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [resetResult, setResetResult] = useState(null);
  const [importOpen, setImportOpen] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (deptFilter) params.department = deptFilter;
      if (semFilter) params.semester = semFilter;
      if (statusFilter) params.status = statusFilter;
      const { data } = await api.get("/students", { params });
      setStudents(data);
    } catch {
      toast.error("Failed to load students.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [deptFilter, semFilter, statusFilter]);
  useEffect(() => {
    const t = setTimeout(load, 400);
    return () => clearTimeout(t);
  }, [search]);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setErrors({});
    setModalOpen(true);
  };

  const openEdit = (s) => {
    setEditing(s);
    setForm({ full_name: s.full_name || "", email: s.email || "", phone: s.phone || "", password: "", student_id: s.student_id, department: s.department, semester: s.semester, batch: s.batch || "" });
    setErrors({});
    setModalOpen(true);
  };

  const validate = () => {
    const next = {};
    if (!NAME_REGEX.test(form.full_name.trim())) next.full_name = "Name must be 3–30 letters only.";
    if (!GMAIL_REGEX.test(form.email.trim().toLowerCase())) next.email = "Only Gmail addresses (@gmail.com) are allowed.";
    if (!ID_REGEX.test(form.student_id.trim())) next.student_id = "Student ID must contain numbers only.";
    if (!editing) {
      const pwErr = validatePassword(form.password);
      if (pwErr) next.password = pwErr;
    }
    if (form.batch.trim().length > 20) next.batch = "Batch is too long (max 20 characters).";
    if (!PHONE_REGEX.test(form.phone.trim())) next.phone = "Phone number must be exactly 10 digits.";
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
        await api.put(`/students/${editing.id}`, {
          full_name: form.full_name.trim(), phone: form.phone.trim(), email: form.email.trim().toLowerCase(), student_id: form.student_id.trim(),
          department: form.department, semester: Number(form.semester), batch: form.batch.trim(),
        });
        toast.success("Student updated.");
      } else {
        await api.post("/students", { ...form, semester: Number(form.semester) });
        toast.success("Student created.");
      }
      setModalOpen(false);
      load();
    } catch (err) {
      const msg = errMsg(err, "Something went wrong.");
      // surface duplicate errors next to the field they are about, and as a toast
      if (err.response?.status === 409) setErrors((prev) => ({ ...prev, ...(/email/i.test(msg) ? { email: msg } : { student_id: msg }) }));
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.delete(`/students/${confirmDelete.id}`);
      toast.success("Student deleted.");
      setConfirmDelete(null);
      load();
    } catch (err) {
      toast.error(errMsg(err, "Failed to delete student."));
    }
  };

  const openProfile = async (s) => {
    setProfileLoading(true);
    try {
      const { data } = await api.get(`/students/${s.id}`);
      setProfile(data);
    } catch (err) {
      toast.error(errMsg(err, "Couldn't load that student's profile."));
    } finally {
      setProfileLoading(false);
    }
  };

  const handleToggleStatus = async () => {
    const target = confirmStatus;
    try {
      await api.patch(`/students/${target.id}/status`, { is_active: !target.is_active });
      toast.success(target.is_active ? "Student deactivated." : "Student activated.");
      setConfirmStatus(null);
      load();
    } catch (err) {
      toast.error(errMsg(err, "Couldn't change the student's status."));
    }
  };

  const handleResetPassword = async (s) => {
    try {
      const { data } = await api.post(`/students/${s.id}/reset-password`);
      setResetResult({ name: s.full_name, password: data.temporary_password });
    } catch (err) {
      toast.error(errMsg(err, "Failed to reset password."));
    }
  };

  const handleImport = async () => {
    if (!importFile) { toast.error("Choose an .xlsx file first."); return; }
    setImporting(true);
    try {
      const fd = new FormData();
      fd.append("file", importFile);
      const { data } = await api.post("/students/bulk-import", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setImportResult(data);
      toast.success(data.message);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Import failed.");
    } finally {
      setImporting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-display font-bold">Student Management</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{students.length} student{students.length !== 1 ? "s" : ""}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => { setImportOpen(true); setImportResult(null); setImportFile(null); }} className="btn-secondary flex items-center gap-2 !py-2.5">
              <FiUpload /> Bulk Import
            </button>
            <button onClick={openCreate} className="btn-primary flex items-center gap-2 !py-2.5">
              <FiPlus /> Add Student
            </button>
          </div>
        </div>

        <div className="glass-card p-4 mb-4 flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input className="input-field pl-10 !py-2" placeholder="Search name, email, ID..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select className="input-field !py-2 w-auto" value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)}>
            <option value="">All Departments</option>
            {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <select className="input-field !py-2 w-auto" value={semFilter} onChange={(e) => setSemFilter(e.target.value)}>
            <option value="">All Semesters</option>
            {[1,2,3,4,5,6,7,8].map((s) => <option key={s} value={s}>Semester {s}</option>)}
          </select>
          <select className="input-field !py-2 w-auto" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="unverified">Email unverified</option>
          </select>
        </div>

        <div className="glass-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-slate-200 dark:border-white/10 text-slate-500 dark:text-slate-400">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Student ID</th>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Department</th>
                <th className="px-4 py-3 font-medium">Sem</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="text-center py-10 text-slate-400">Loading...</td></tr>
              ) : students.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-10 text-slate-400">No students found.</td></tr>
              ) : students.map((s) => (
                <tr key={s.id} className="border-b border-slate-100 dark:border-white/5 last:border-0">
                  <td className="px-4 py-3 font-medium">{s.full_name}</td>
                  <td className="px-4 py-3">{s.student_id}</td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{s.email}</td>
                  <td className="px-4 py-3">{s.department}</td>
                  <td className="px-4 py-3">{s.semester}</td>
                  <td className="px-4 py-3">
                    <span className={`text-[11px] px-2 py-1 rounded-full font-semibold ${!s.is_active ? "bg-danger/10 text-danger" : s.is_verified ? "bg-success/10 text-success" : "bg-warning/10 text-warning"}`}>
                      {!s.is_active ? "Inactive" : s.is_verified ? "Active" : "Unverified"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => openProfile(s)} title="View profile & records" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 text-secondary"><FiEye /></button>
                      <button onClick={() => setConfirmStatus(s)} title={s.is_active ? "Deactivate" : "Activate"} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 text-warning">{s.is_active ? <FiUserX /> : <FiUserCheck />}</button>
                      <button onClick={() => handleResetPassword(s)} title="Reset password" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 text-slate-500"><FiKey /></button>
                      <button onClick={() => openEdit(s)} title="Edit" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 text-primary"><FiEdit2 /></button>
                      <button onClick={() => setConfirmDelete(s)} title="Delete" className="p-2 rounded-lg hover:bg-danger/10 text-danger"><FiTrash2 /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit Student" : "Add Student"}>
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">Full name</label>
            <input className="input-field" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            {errors.full_name && <p className="input-error">{errors.full_name}</p>}
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Gmail address</label>
            <input type="email" className="input-field" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            {errors.email && <p className="input-error">{errors.email}</p>}
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Student ID</label>
            <input className="input-field" value={form.student_id} onChange={(e) => setForm({ ...form, student_id: e.target.value })} />
            {errors.student_id && <p className="input-error">{errors.student_id}</p>}
          </div>
          {!editing && (
            <>
              <div>
                <label className="text-sm font-medium mb-1 block">Password</label>
                <input type="password" className="input-field" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                {errors.password && <p className="input-error">{errors.password}</p>}
              </div>
            </>
          )}
          <div>
            <label className="text-sm font-medium mb-1 block">Phone</label>
            <input className="input-field" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            {errors.phone && <p className="input-error">{errors.phone}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1 block">Department</label>
              <select className="input-field" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })}>
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
          <div>
            <label className="text-sm font-medium mb-1 block">Batch (optional)</label>
            <input className="input-field" value={form.batch} onChange={(e) => setForm({ ...form, batch: e.target.value })} placeholder="2024-2028" />
            {errors.batch && <p className="input-error">{errors.batch}</p>}
          </div>
          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
            {submitting ? "Saving..." : editing ? "Save Changes" : "Create Student"}
          </button>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!confirmDelete}
        title="Delete student?"
        message={`This permanently deletes ${confirmDelete?.full_name}'s login and profile. Consider Deactivate instead if you may need the account again.`}
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(null)}
      />

      <ConfirmDialog
        open={!!confirmStatus}
        danger={!!confirmStatus?.is_active}
        title={confirmStatus?.is_active ? "Deactivate student?" : "Activate student?"}
        message={confirmStatus?.is_active ? `${confirmStatus?.full_name} will be signed out and unable to log in. All their records are kept.` : `${confirmStatus?.full_name} will be able to log in again.`}
        confirmLabel={confirmStatus?.is_active ? "Deactivate" : "Activate"}
        onConfirm={handleToggleStatus}
        onCancel={() => setConfirmStatus(null)}
      />

      <Modal open={profileLoading || !!profile} onClose={() => setProfile(null)} title={profile ? profile.full_name : "Loading..."} maxWidth="max-w-3xl">
        {profile && (
          <div className="space-y-5">
            <div className="grid sm:grid-cols-2 gap-x-6 gap-y-1 text-sm">
              <p><span className="text-slate-400">Student ID:</span> {profile.student_id}</p>
              <p><span className="text-slate-400">Email:</span> {profile.email}</p>
              <p><span className="text-slate-400">Phone:</span> {profile.phone || "—"}</p>
              <p><span className="text-slate-400">Batch:</span> {profile.batch || "—"}</p>
              <p><span className="text-slate-400">Department:</span> {profile.department}</p>
              <p><span className="text-slate-400">Semester:</span> {profile.semester}</p>
              <p><span className="text-slate-400">Status:</span> {profile.is_active ? (profile.is_verified ? "Active" : "Email unverified") : "Inactive"}</p>
              <p><span className="text-slate-400">Last login:</span> {profile.last_login_at ? new Date(profile.last_login_at).toLocaleString() : "Never"}</p>
            </div>

            <div>
              <p className="font-display font-semibold text-sm mb-2">Academic records</p>
              {profile.academics.length === 0 ? <p className="text-sm text-slate-400">No subjects are mapped to this department and semester yet.</p> : (
                <div className="overflow-x-auto rounded-xl border border-slate-100 dark:border-white/10">
                  <table className="w-full text-sm">
                    <thead><tr className="text-left text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-white/10">
                      <th className="px-3 py-2 font-medium">Subject</th><th className="px-3 py-2 font-medium">Faculty</th>
                      <th className="px-3 py-2 font-medium">Attendance</th><th className="px-3 py-2 font-medium">Internal</th>
                      <th className="px-3 py-2 font-medium">Practical</th><th className="px-3 py-2 font-medium">Assignments</th>
                    </tr></thead>
                    <tbody>
                      {profile.academics.map((a) => (
                        <tr key={a.subject_id} className="border-b border-slate-100 dark:border-white/5 last:border-0">
                          <td className="px-3 py-2 font-medium">{a.subject_name}</td>
                          <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{a.faculty_name || "Unassigned"}</td>
                          <td className="px-3 py-2">{a.attendance.percentage === null ? "—" : <span className={a.attendance.at_risk ? "text-danger font-semibold" : "text-success font-semibold"}>{a.attendance.percentage}% ({a.attendance.present}/{a.attendance.total})</span>}</td>
                          <td className="px-3 py-2">{a.marks?.internal ?? "—"}{a.marks && !a.marks.published && a.marks.internal != null && <span className="text-[10px] text-warning ml-1">draft</span>}</td>
                          <td className="px-3 py-2">{a.marks?.practical ?? "—"}</td>
                          <td className="px-3 py-2">{a.assignments.length === 0 ? "—" : `${a.assignments.filter((x) => x.status !== "not_submitted").length}/${a.assignments.length} submitted`}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div>
              <p className="font-display font-semibold text-sm mb-2">Recent leave requests</p>
              {profile.leave.length === 0 ? <p className="text-sm text-slate-400">None.</p> : profile.leave.map((l) => (
                <p key={l.id} className="text-xs text-slate-500 dark:text-slate-400">{l.from_date} → {l.to_date} · {l.status} · {l.reason}</p>
              ))}
            </div>
          </div>
        )}
      </Modal>

      <Modal open={!!resetResult} onClose={() => setResetResult(null)} title="Password Reset">
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">
          Share this temporary password with <strong>{resetResult?.name}</strong> securely:
        </p>
        <div className="glass-card p-4 flex items-center justify-between">
          <code className="font-mono text-sm">{resetResult?.password}</code>
          <button
            onClick={() => { navigator.clipboard.writeText(resetResult.password); toast.success("Copied!"); }}
            className="text-primary text-sm font-medium hover:underline"
          >
            Copy
          </button>
        </div>
      </Modal>

      <Modal open={importOpen} onClose={() => setImportOpen(false)} title="Bulk Import Students">
        {!importResult ? (
          <div className="space-y-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Upload an .xlsx file with columns: Full Name, Student ID, Email, Phone, Department, Semester.
            </p>
            <button
              onClick={() => downloadReport("/students/bulk-import/template", {}, "student_import_template.xlsx")}
              className="text-sm text-primary font-medium hover:underline flex items-center gap-1.5"
            >
              <FiDownload size={14} /> Download template
            </button>
            <input type="file" accept=".xlsx" className="input-field" onChange={(e) => setImportFile(e.target.files[0])} />
            <button onClick={handleImport} disabled={importing} className="btn-primary w-full disabled:opacity-60">
              {importing ? "Importing..." : "Import Students"}
            </button>
          </div>
        ) : (
          <div>
            <p className="text-sm font-medium mb-4">{importResult.message}</p>
            {importResult.created.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-semibold text-success uppercase tracking-wide mb-2 flex items-center gap-1.5"><FiCheckCircle /> Created ({importResult.created.length})</p>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {importResult.created.map((c, i) => <p key={i} className="text-xs text-slate-500 dark:text-slate-400">Row {c.row}: {c.full_name} ({c.student_id})</p>)}
                </div>
                {importResult.default_password && <p className="text-xs text-slate-400 mt-2">Default password for imported students: <code className="font-mono">{importResult.default_password}</code></p>}
              </div>
            )}
            {importResult.failed.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-semibold text-danger uppercase tracking-wide mb-2 flex items-center gap-1.5"><FiXCircle /> Failed ({importResult.failed.length})</p>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {importResult.failed.map((f, i) => <p key={i} className="text-xs text-danger">Row {f.row}: {f.error}</p>)}
                </div>
              </div>
            )}
            <button onClick={() => setImportOpen(false)} className="btn-primary w-full">Done</button>
          </div>
        )}
      </Modal>
    </DashboardLayout>
  );
}
