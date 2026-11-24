import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiSearch, FiEye, FiSave, FiCheckCircle, FiAlertTriangle } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Modal from "../../components/Modal";
import api from "../../services/api";

const pad = (n) => String(n).padStart(2, "0");
const todayStr = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
const errText = (err, fallback) => {
  const d = err.response?.data?.detail;
  if (Array.isArray(d)) return d[0]?.msg?.replace(/^Value error, /, "") || fallback;
  return d || fallback;
};

/** One subject's panel inside the student modal: attendance, marks, assignments (all for MY subject only). */
function SubjectPanel({ studentId, row, onChanged }) {
  const [date, setDate] = useState(todayStr());
  const [internal, setInternal] = useState(row.marks?.internal ?? "");
  const [practical, setPractical] = useState(row.marks?.practical ?? "");
  const [busy, setBusy] = useState(false);
  const [grades, setGrades] = useState({});

  const run = async (fn, okMsg) => {
    setBusy(true);
    try { await fn(); toast.success(okMsg); onChanged(); }
    catch (err) { toast.error(errText(err, "That didn't work.")); }
    finally { setBusy(false); }
  };

  const markAttendance = (status) =>
    run(() => api.post("/attendance/mark", { subject_id: row.subject_id, date, entries: [{ student_id: studentId, status }] }), `Marked ${status}.`);

  const saveMarks = () => {
    const toNum = (v) => (v === "" ? null : Number(v));
    const i = toNum(internal), p = toNum(practical);
    if (i === null && p === null) { toast.error("Enter internal and/or practical marks."); return; }
    if ([i, p].some((v) => v !== null && (Number.isNaN(v) || v < 0 || v > 100))) { toast.error("Marks must be between 0 and 100."); return; }
    run(() => api.put("/marks", { student_id: studentId, subject_id: row.subject_id, internal: i, practical: p }), "Marks saved.");
  };

  const att = row.attendance;
  return (
    <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 space-y-4">
      <div className="flex items-center justify-between">
        <p className="font-display font-semibold text-sm">{row.subject_name} <span className="text-xs text-slate-400 font-normal">{row.subject_code}</span></p>
        <span className={`text-xs px-2 py-1 rounded-full font-semibold ${att.percentage === null ? "bg-slate-200 dark:bg-white/10 text-slate-500" : att.at_risk ? "bg-danger/10 text-danger" : "bg-success/10 text-success"}`}>
          {att.percentage === null ? "No attendance yet" : `${att.percentage}% (${att.present}/${att.total})`}
        </span>
      </div>

      <div>
        <p className="text-xs font-medium mb-1.5">Mark attendance</p>
        <div className="flex flex-wrap items-center gap-2">
          <input type="date" max={todayStr()} value={date} onChange={(e) => setDate(e.target.value)} className="input-field !py-1.5 w-auto" />
          <button disabled={busy} onClick={() => markAttendance("present")} className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-success/10 text-success disabled:opacity-50">Present</button>
          <button disabled={busy} onClick={() => markAttendance("absent")} className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-danger/10 text-danger disabled:opacity-50">Absent</button>
        </div>
      </div>

      <div>
        <p className="text-xs font-medium mb-1.5">Marks {row.marks?.published && <span className="text-success ml-1 inline-flex items-center gap-1"><FiCheckCircle size={11} /> published</span>}</p>
        <div className="flex flex-wrap items-center gap-2">
          <input type="number" min="0" max="100" placeholder="Internal" value={internal} onChange={(e) => setInternal(e.target.value)} className="input-field !py-1.5 !px-2 w-24" />
          <input type="number" min="0" max="100" placeholder="Practical" value={practical} onChange={(e) => setPractical(e.target.value)} className="input-field !py-1.5 !px-2 w-24" />
          <button disabled={busy} onClick={saveMarks} className="btn-secondary !py-1.5 text-xs flex items-center gap-1 disabled:opacity-50"><FiSave size={12} /> Save</button>
          {row.marks && !row.marks.published && (
            <button disabled={busy} onClick={() => run(() => api.put(`/marks/${row.marks.id}/publish`), "Published to student.")} className="text-xs text-secondary font-medium hover:underline">Publish</button>
          )}
        </div>
      </div>

      <div>
        <p className="text-xs font-medium mb-1.5">Assignments</p>
        {row.assignments.length === 0 ? <p className="text-xs text-slate-400">No assignments for this subject.</p> : (
          <div className="space-y-2">
            {row.assignments.map((a) => (
              <div key={a.id} className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="min-w-0">
                  <p className="font-medium truncate">{a.title}</p>
                  <p className="text-slate-400">Due {a.due_date} · {a.status.replace("_", " ")}{a.grade ? ` · Grade ${a.grade}` : ""}</p>
                </div>
                {a.submission_id ? (
                  <div className="flex items-center gap-1.5">
                    <input placeholder="Grade" maxLength={20} value={grades[a.id] ?? a.grade ?? ""} onChange={(e) => setGrades({ ...grades, [a.id]: e.target.value })} className="input-field !py-1 !px-2 w-20 text-xs" />
                    <button disabled={busy || !(grades[a.id] ?? "").trim()} onClick={() => run(() => api.put(`/assignments/submissions/${a.submission_id}/grade`, { grade: grades[a.id].trim() }), "Graded.")} className="text-primary font-medium hover:underline disabled:opacity-40">Grade</button>
                  </div>
                ) : <span className="text-slate-400">Not submitted</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function FacultyStudents() {
  const [students, setStudents] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [search, setSearch] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [semester, setSemester] = useState("");
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [phone, setPhone] = useState("");
  const [batch, setBatch] = useState("");
  const [saving, setSaving] = useState(false);
  const [formErr, setFormErr] = useState("");

  useEffect(() => { api.get("/faculty/me/subjects").then(({ data }) => setSubjects(data)).catch(() => {}); }, []);

  const load = async () => {
    setLoading(true); setLoadError(false);
    try {
      const params = {};
      if (search.trim()) params.search = search.trim();
      if (subjectId) params.subject_id = subjectId;
      if (semester) params.semester = semester;
      const { data } = await api.get("/faculty/me/students", { params });
      setStudents(data);
    } catch { setLoadError(true); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [subjectId, semester]);
  useEffect(() => { const t = setTimeout(load, 400); return () => clearTimeout(t); }, [search]);

  const openDetail = async (id, keepOpen = false) => {
    if (!keepOpen) setDetailLoading(true);
    try {
      const { data } = await api.get(`/faculty/me/students/${id}`);
      setDetail(data); setPhone(data.phone || ""); setBatch(data.batch || ""); setFormErr("");
    } catch (err) { toast.error(errText(err, "Couldn't open that student.")); setDetail(null); }
    finally { setDetailLoading(false); }
  };

  const saveProfile = async (e) => {
    e.preventDefault();
    if (!/^[0-9]{10}$/.test(phone.trim())) { setFormErr("Phone number must be exactly 10 digits."); return; }
    setSaving(true); setFormErr("");
    try {
      await api.put(`/faculty/me/students/${detail.id}`, { phone: phone.trim(), batch: batch.trim() });
      toast.success("Student updated.");
      openDetail(detail.id, true); load();
    } catch (err) { setFormErr(errText(err, "Couldn't save changes.")); }
    finally { setSaving(false); }
  };

  const semesters = [...new Set(students.map((s) => s.semester))].sort((a, b) => a - b);

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">My Students</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Students enrolled in the subjects assigned to you — {students.length} shown</p>

        <div className="glass-card p-4 mb-4 flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input className="input-field pl-10 !py-2" placeholder="Search name, email, ID, phone..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select className="input-field !py-2 w-auto" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
            <option value="">All my subjects</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <select className="input-field !py-2 w-auto" value={semester} onChange={(e) => setSemester(e.target.value)}>
            <option value="">All semesters</option>
            {(semester && !semesters.includes(Number(semester)) ? [...semesters, Number(semester)] : semesters).map((s) => <option key={s} value={s}>Semester {s}</option>)}
          </select>
        </div>

        {loadError && <div className="mb-4 p-3 rounded-xl bg-danger/10 border border-danger/30 text-sm text-danger">Couldn't load your students. <button onClick={load} className="underline font-medium">Retry</button></div>}

        <div className="glass-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-slate-200 dark:border-white/10 text-slate-500 dark:text-slate-400">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Student ID</th>
                <th className="px-4 py-3 font-medium">Class</th>
                <th className="px-4 py-3 font-medium">My subjects</th>
                <th className="px-4 py-3 font-medium">Attendance</th>
                <th className="px-4 py-3 font-medium text-right">View</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-center py-10 text-slate-400">Loading...</td></tr>
              ) : students.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-10 text-slate-400">{subjects.length === 0 ? "No subjects are assigned to you yet — ask the Admin to assign subjects." : "No students found."}</td></tr>
              ) : students.map((s) => (
                <tr key={s.id} className="border-b border-slate-100 dark:border-white/5 last:border-0">
                  <td className="px-4 py-3 font-medium">{s.full_name} {!s.is_active && <span className="ml-1 text-[10px] px-1.5 py-0.5 rounded bg-warning/10 text-warning">inactive</span>}</td>
                  <td className="px-4 py-3">{s.student_id}</td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{s.department} · Sem {s.semester}</td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{s.subjects.map((x) => x.name).join(", ")}</td>
                  <td className="px-4 py-3">
                    {s.attendance_percentage === null ? <span className="text-slate-400">—</span> :
                      <span className={s.attendance_percentage < 75 ? "text-danger font-semibold" : "text-success font-semibold"}>{s.attendance_percentage}%</span>}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => openDetail(s.id)} title="View & manage" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 text-primary"><FiEye /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={detailLoading || !!detail} onClose={() => setDetail(null)} title={detail ? detail.full_name : "Loading..."} maxWidth="max-w-2xl">
        {detail && (
          <div className="space-y-5">
            <div className="grid sm:grid-cols-2 gap-x-6 gap-y-1 text-sm">
              <p><span className="text-slate-400">Student ID:</span> {detail.student_id}</p>
              <p><span className="text-slate-400">Email:</span> {detail.email}</p>
              <p><span className="text-slate-400">Department:</span> {detail.department}</p>
              <p><span className="text-slate-400">Semester:</span> {detail.semester}</p>
            </div>

            <form onSubmit={saveProfile} noValidate className="p-4 rounded-xl bg-primary/5 border border-primary/10 space-y-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">You can update a student's contact phone and batch. Other profile fields are managed by the Admin.</p>
              <div className="grid sm:grid-cols-2 gap-3">
                <div><label className="text-xs font-medium mb-1 block">Phone</label><input className="input-field !py-2" value={phone} onChange={(e) => setPhone(e.target.value)} /></div>
                <div><label className="text-xs font-medium mb-1 block">Batch</label><input className="input-field !py-2" value={batch} onChange={(e) => setBatch(e.target.value)} placeholder="2024-2028" maxLength={20} /></div>
              </div>
              {formErr && <p className="input-error flex items-center gap-1"><FiAlertTriangle size={12} /> {formErr}</p>}
              <button type="submit" disabled={saving} className="btn-primary !py-2 text-sm disabled:opacity-60">{saving ? "Saving..." : "Save profile"}</button>
            </form>

            <div className="space-y-3">
              {detail.academics.map((row) => (
                <SubjectPanel key={row.subject_id} studentId={detail.id} row={row} onChanged={() => { openDetail(detail.id, true); load(); }} />
              ))}
            </div>
          </div>
        )}
      </Modal>
    </DashboardLayout>
  );
}
