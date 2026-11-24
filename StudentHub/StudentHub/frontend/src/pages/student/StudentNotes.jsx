import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiFile, FiDownload } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";

export default function StudentNotes() {
  const [subjects, setSubjects] = useState([]);
  const [subjectFilter, setSubjectFilter] = useState("");
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSubjectsAndNotes = async () => {
      setLoading(true);
      try {
        const { data: allSubjects } = await api.get("/subjects");
        setSubjects(allSubjects);
        const params = subjectFilter ? { subject_id: subjectFilter } : {};
        const { data } = await api.get("/notes", { params });
        setNotes(data);
      } catch {
        toast.error("Failed to load notes.");
      } finally {
        setLoading(false);
      }
    };
    loadSubjectsAndNotes();
  }, [subjectFilter]);

  const subjectName = (id) => subjects.find((s) => s.id === id)?.name || "Subject";

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Notes</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Download study material uploaded by your faculty</p>

        <div className="glass-card p-4 mb-4">
          <select className="input-field !py-2 w-auto" value={subjectFilter} onChange={(e) => setSubjectFilter(e.target.value)}>
            <option value="">All Subjects</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>

        {loading ? (
          <p className="text-center py-16 text-slate-400">Loading...</p>
        ) : notes.length === 0 ? (
          <p className="text-center py-16 text-slate-400">No notes available yet.</p>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {notes.map((n) => (
              <div key={n.id} className="glass-card p-4">
                <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-2"><FiFile /></div>
                <p className="font-medium text-sm">{n.title}</p>
                <p className="text-xs text-slate-400 mb-2">{subjectName(n.subject_id)} · Unit {n.unit} · {n.file_type.toUpperCase()}</p>
                <a href={n.file_url} target="_blank" rel="noreferrer" className="text-primary text-xs font-medium hover:underline flex items-center gap-1"><FiDownload /> Download</a>
              </div>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
