import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiPlus, FiTrash2, FiAlertTriangle } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Modal from "../../components/Modal";
import api from "../../services/api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const DEPARTMENTS = ["Computer Science", "Information Technology", "Electronics & Communication", "Electrical Engineering", "Mechanical Engineering", "Civil Engineering", "Commerce", "Science", "Law", "Other"];
const EMPTY_FORM = { day_of_week: "Monday", start_time: "09:00", end_time: "10:00", subject_id: "", faculty_id: "", classroom: "", department: DEPARTMENTS[0], semester: 1 };

export default function TimetableManagement() {
  const [slots, setSlots] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [facultyList, setFacultyList] = useState([]);
  const [deptFilter, setDeptFilter] = useState(DEPARTMENTS[0]);
  const [semFilter, setSemFilter] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [clashWarning, setClashWarning] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    try {
      const [{ data: t }, { data: s }, { data: f }] = await Promise.all([
        api.get("/timetable", { params: { department: deptFilter, semester: semFilter } }),
        api.get("/subjects", { params: { department: deptFilter, semester: semFilter } }),
        api.get("/faculty"),
      ]);
      setSlots(t);
      setSubjects(s);
      setFacultyList(f);
    } catch {
      toast.error("Failed to load timetable.");
    }
  };
  useEffect(() => { load(); }, [deptFilter, semFilter]);

  const openCreate = () => {
    setForm({ ...EMPTY_FORM, department: deptFilter, semester: semFilter });
    setClashWarning(null);
    setModalOpen(true);
  };

  const checkClash = async (nextForm) => {
    if (!nextForm.subject_id || !nextForm.faculty_id || !nextForm.classroom) return;
    try {
      const { data } = await api.post("/timetable/check-clash", { ...nextForm, semester: Number(nextForm.semester) });
      setClashWarning(data.has_clash ? data.clashes : null);
    } catch {
      // ignore live-check failures silently
    }
  };

  // Only faculty who currently teach the chosen subject can be timetabled for it.
  const teachersOf = (subjectId) => {
    const ids = subjects.find((s) => s.id === subjectId)?.faculty_ids || [];
    return facultyList.filter((f) => ids.includes(f.faculty_id));
  };

  const updateForm = (fields) => {
    const next = { ...form, ...fields };
    if ("subject_id" in fields) {
      const teachers = teachersOf(next.subject_id);
      next.faculty_id = teachers.length === 1 ? teachers[0].faculty_id : (teachers.some((t) => t.faculty_id === next.faculty_id) ? next.faculty_id : "");
    }
    setForm(next);
    checkClash(next);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/timetable", { ...form, semester: Number(form.semester) });
      toast.success("Timetable slot created.");
      setModalOpen(false);
      load();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.clashes) {
        toast.error(detail.message);
        setClashWarning(detail.clashes);
      } else {
        toast.error(typeof detail === "string" ? detail : "Something went wrong.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/timetable/${id}`);
      toast.success("Slot removed.");
      load();
    } catch {
      toast.error("Failed to remove slot.");
    }
  };

  const subjectName = (id) => subjects.find((s) => s.id === id)?.name || slots.find(sl => sl.subject_id === id) ? "—" : "—";
  const slotsByDay = (day) => slots.filter((s) => s.day_of_week === day).sort((a, b) => a.start_time.localeCompare(b.start_time));

  return (
    <DashboardLayout>
      <div className="pt-2">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-display font-bold">Timetable</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Weekly view with live clash detection</p>
          </div>
          <button onClick={openCreate} className="btn-primary flex items-center gap-2 !py-2.5"><FiPlus /> Add Slot</button>
        </div>

        <div className="glass-card p-4 mb-4 flex flex-wrap gap-3">
          <select className="input-field !py-2 w-auto" value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)}>
            {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <select className="input-field !py-2 w-auto" value={semFilter} onChange={(e) => setSemFilter(Number(e.target.value))}>
            {[1,2,3,4,5,6,7,8].map((s) => <option key={s} value={s}>Semester {s}</option>)}
          </select>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {DAYS.map((day) => (
            <div key={day} className="glass-card p-4">
              <h3 className="font-display font-semibold mb-3">{day}</h3>
              {slotsByDay(day).length === 0 ? (
                <p className="text-xs text-slate-400">No classes scheduled.</p>
              ) : (
                <div className="space-y-2">
                  {slotsByDay(day).map((s) => (
                    <div key={s.id} className="flex items-center justify-between p-2.5 rounded-lg bg-primary/5">
                      <div>
                        <p className="text-sm font-medium">{s.start_time}–{s.end_time}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{subjects.find((sub) => sub.id === s.subject_id)?.name || "Subject"} · Room {s.classroom}</p>
                      </div>
                      <button onClick={() => handleDelete(s.id)} className="p-1.5 rounded-lg hover:bg-danger/10 text-danger"><FiTrash2 size={14} /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add Timetable Slot">
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1 block">Day</label>
              <select className="input-field" value={form.day_of_week} onChange={(e) => updateForm({ day_of_week: e.target.value })}>
                {DAYS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Classroom</label>
              <input className="input-field" value={form.classroom} onChange={(e) => updateForm({ classroom: e.target.value })} placeholder="Room 204" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1 block">Start time</label>
              <input type="time" className="input-field" value={form.start_time} onChange={(e) => updateForm({ start_time: e.target.value })} />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">End time</label>
              <input type="time" className="input-field" value={form.end_time} onChange={(e) => updateForm({ end_time: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Subject</label>
            <select className="input-field" value={form.subject_id} onChange={(e) => updateForm({ subject_id: e.target.value })}>
              <option value="">Select subject</option>
              {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Faculty</label>
            <select className="input-field" value={form.faculty_id} onChange={(e) => updateForm({ faculty_id: e.target.value })}>
              <option value="">Select faculty</option>
              {teachersOf(form.subject_id).map((f) => <option key={f.id} value={f.faculty_id}>{f.full_name}</option>)}
            </select>
            {form.subject_id && teachersOf(form.subject_id).length === 0 && (
              <p className="input-error">No faculty is assigned to this subject yet. Assign one under Faculty or Subjects first.</p>
            )}
          </div>

          {clashWarning && (
            <div className="bg-danger/10 border border-danger/20 rounded-xl p-3 space-y-1">
              {clashWarning.map((c, i) => (
                <p key={i} className="text-xs text-danger flex items-start gap-1.5"><FiAlertTriangle className="mt-0.5 flex-shrink-0" /> {c.message}</p>
              ))}
            </div>
          )}

          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
            {submitting ? "Saving..." : "Create Slot"}
          </button>
        </form>
      </Modal>
    </DashboardLayout>
  );
}
