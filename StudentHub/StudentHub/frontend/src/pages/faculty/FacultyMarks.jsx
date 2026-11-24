import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { FiSave, FiCheckCircle } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

export default function FacultyMarks() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState("");
  const [students, setStudents] = useState([]);
  const [marksMap, setMarksMap] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/faculty/me/subjects")
      .then(({ data }) => {
        setSubjects(data);
        const wanted = searchParams.get("subject");   // deep link from the Classroom Activity Hub
        if (wanted && data.some((s) => s.id === wanted)) { setSubjectId(wanted); loadRoster(wanted); }
      })
      .catch(() => toast.error("Failed to load your subjects."));
  }, [user.id]);

  const loadRoster = async (sid) => {
    if (!sid) return;
    setLoading(true);
    try {
      const [{ data: roster }, { data: marks }] = await Promise.all([
        api.get("/students/roster", { params: { subject_id: sid } }),
        api.get(`/marks/subject/${sid}`),
      ]);
      setStudents(roster);
      const map = {};
      roster.forEach((s) => { map[s.id] = { internal: "", practical: "", published: false, marksId: null }; });
      marks.forEach((m) => { map[m.student_id] = { internal: m.internal ?? "", practical: m.practical ?? "", published: m.published, marksId: m.id }; });
      setMarksMap(map);
    } catch {
      toast.error("Failed to load roster.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { if (subjectId) loadRoster(subjectId); }, [subjectId]);

  const update = (studentId, field, value) => {
    setMarksMap((prev) => ({ ...prev, [studentId]: { ...prev[studentId], [field]: value } }));
  };

  const save = async (studentId) => {
    const entry = marksMap[studentId];
    try {
      await api.put("/marks", {
        student_id: studentId,
        subject_id: subjectId,
        internal: entry.internal === "" ? null : Number(entry.internal),
        practical: entry.practical === "" ? null : Number(entry.practical),
      });
      toast.success("Marks saved.");
      loadRoster(subjectId);
    } catch {
      toast.error("Failed to save marks.");
    }
  };

  const publish = async (studentId) => {
    const entry = marksMap[studentId];
    if (!entry.marksId) {
      toast.error("Save marks before publishing.");
      return;
    }
    try {
      await api.put(`/marks/${entry.marksId}/publish`);
      toast.success("Published to student.");
      loadRoster(subjectId);
    } catch {
      toast.error("Failed to publish.");
    }
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Marks</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Enter internal/practical marks and publish results</p>

        <div className="glass-card p-4 mb-4">
          <select className="input-field !py-2 w-auto" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
            <option value="">Select a subject</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>

        {!subjectId ? (
          <p className="text-center py-16 text-slate-400">Select a subject to enter marks.</p>
        ) : loading ? (
          <p className="text-center py-16 text-slate-400">Loading...</p>
        ) : (
          <div className="glass-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-slate-200 dark:border-white/10 text-slate-500 dark:text-slate-400">
                  <th className="px-4 py-3 font-medium">Student</th>
                  <th className="px-4 py-3 font-medium">Internal (/100)</th>
                  <th className="px-4 py-3 font-medium">Practical (/100)</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.id} className="border-b border-slate-100 dark:border-white/5 last:border-0">
                    <td className="px-4 py-3 font-medium">{s.full_name}</td>
                    <td className="px-4 py-3">
                      <input type="number" min="0" max="100" className="input-field !py-1.5 !px-2 w-20" value={marksMap[s.id]?.internal ?? ""} onChange={(e) => update(s.id, "internal", e.target.value)} />
                    </td>
                    <td className="px-4 py-3">
                      <input type="number" min="0" max="100" className="input-field !py-1.5 !px-2 w-20" value={marksMap[s.id]?.practical ?? ""} onChange={(e) => update(s.id, "practical", e.target.value)} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button onClick={() => save(s.id)} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 text-primary" title="Save"><FiSave /></button>
                        {marksMap[s.id]?.published ? (
                          <span className="text-xs text-success flex items-center gap-1"><FiCheckCircle /> Published</span>
                        ) : (
                          <button onClick={() => publish(s.id)} className="text-xs text-secondary font-medium hover:underline">Publish</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
