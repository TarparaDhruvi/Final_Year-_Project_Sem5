import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { FiCheck, FiSave, FiZap } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Modal from "../../components/Modal";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

const pad2 = (n) => String(n).padStart(2, "0");
const today = () => { const d = new Date(); return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`; };

export default function FacultyAttendance() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState("");
  const [date, setDate] = useState(today());
  const [students, setStudents] = useState([]);
  const [statusMap, setStatusMap] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [xpTarget, setXpTarget] = useState(null);
  const [xpActivity, setXpActivity] = useState("event");
  const [xpNote, setXpNote] = useState("");
  const [xpSubmitting, setXpSubmitting] = useState(false);

  useEffect(() => {
    api.get("/faculty/me/subjects")
      .then(({ data }) => {
        setSubjects(data);
        // Deep link from the Classroom Activity Hub (?subject=ID): open straight onto that subject — but only if it is one of MY subjects.
        const wanted = searchParams.get("subject");
        if (wanted && data.some((s) => s.id === wanted)) { setSubjectId(wanted); loadRoster(wanted); }
      })
      .catch(() => toast.error("Failed to load your subjects."));
  }, [user.id]);

  const loadRoster = async (sid) => {
    if (!sid) return;
    setLoading(true);
    try {
      const { data } = await api.get("/students/roster", { params: { subject_id: sid } });
      setStudents(data);
      const { data: existing } = await api.get(`/attendance/subject/${sid}`, { params: { date } });
      const map = {};
      data.forEach((s) => { map[s.id] = "present"; });
      existing.forEach((e) => { map[e.student_id] = e.status; });
      setStatusMap(map);
    } catch {
      toast.error("Failed to load roster.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (subjectId) loadRoster(subjectId); }, [subjectId, date]);

  const toggle = (studentId) => {
    setStatusMap((prev) => ({ ...prev, [studentId]: prev[studentId] === "present" ? "absent" : "present" }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const entries = students.map((s) => ({ student_id: s.id, status: statusMap[s.id] || "absent" }));
      await api.post("/attendance/mark", { subject_id: subjectId, date, entries });
      toast.success("Attendance saved.");
    } catch {
      toast.error("Failed to save attendance.");
    } finally {
      setSaving(false);
    }
  };

  const awardXp = async (e) => {
    e.preventDefault();
    setXpSubmitting(true);
    try {
      await api.post("/skill-wallet/award", { student_id: xpTarget.id, activity: xpActivity, note: xpNote || null });
      toast.success(`XP awarded to ${xpTarget.full_name}.`);
      setXpTarget(null);
      setXpNote("");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Couldn't award XP.");
    } finally {
      setXpSubmitting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Attendance</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Mark or edit attendance for your subjects</p>

        <div className="glass-card p-4 mb-4 flex flex-wrap gap-3 items-center">
          <select className="input-field !py-2 w-auto" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
            <option value="">Select a subject</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <input type="date" max={today()} className="input-field !py-2 w-auto" value={date} onChange={(e) => setDate(e.target.value)} />
          {subjectId && (
            <button onClick={handleSave} disabled={saving} className="btn-primary !py-2 flex items-center gap-2 ml-auto disabled:opacity-60">
              <FiSave /> {saving ? "Saving..." : "Save Attendance"}
            </button>
          )}
        </div>

        {!subjectId ? (
          <p className="text-center py-16 text-slate-400">Select a subject to mark attendance.</p>
        ) : loading ? (
          <p className="text-center py-16 text-slate-400">Loading roster...</p>
        ) : students.length === 0 ? (
          <p className="text-center py-16 text-slate-400">No students found for this subject.</p>
        ) : (
          <div className="glass-card overflow-hidden">
            {students.map((s, i) => (
              <div key={s.id} className={`flex items-center justify-between px-4 py-3 ${i !== students.length - 1 ? "border-b border-slate-100 dark:border-white/5" : ""}`}>
                <div>
                  <p className="text-sm font-medium">{s.full_name}</p>
                  <p className="text-xs text-slate-400">{s.student_id}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setXpTarget(s)}
                    title="Award XP (Skill Wallet)"
                    className="p-2 rounded-lg hover:bg-warning/10 text-warning"
                  >
                    <FiZap size={15} />
                  </button>
                  <button
                    onClick={() => toggle(s.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                      statusMap[s.id] === "present" ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
                    }`}
                  >
                    <FiCheck /> {statusMap[s.id] === "present" ? "Present" : "Absent"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <Modal open={!!xpTarget} onClose={() => setXpTarget(null)} title={`Award XP — ${xpTarget?.full_name}`}>
        <form onSubmit={awardXp} className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">Reason</label>
            <select className="input-field" value={xpActivity} onChange={(e) => setXpActivity(e.target.value)}>
              <option value="event">Event participation (+50 XP)</option>
              <option value="helping_others">Helping others (+10 XP)</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Note (optional)</label>
            <input className="input-field" value={xpNote} onChange={(e) => setXpNote(e.target.value)} placeholder="e.g. Won the hackathon" />
          </div>
          <button type="submit" disabled={xpSubmitting} className="btn-primary w-full disabled:opacity-60">
            {xpSubmitting ? "Awarding..." : "Award XP"}
          </button>
        </form>
      </Modal>
    </DashboardLayout>
  );
}
