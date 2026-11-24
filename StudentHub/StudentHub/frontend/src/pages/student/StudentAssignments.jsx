import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiClock, FiUpload, FiCheckCircle, FiAlertCircle } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Modal from "../../components/Modal";
import api from "../../services/api";

const STATUS_BADGE = {
  not_submitted: "bg-slate-100 dark:bg-white/10 text-slate-500",
  draft: "bg-warning/10 text-warning",
  submitted: "bg-secondary/10 text-secondary",
  graded: "bg-success/10 text-success",
};

export default function StudentAssignments() {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitModal, setSubmitModal] = useState(null);
  const [fileUrl, setFileUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/assignments/mine");
      setAssignments(data);
    } catch {
      toast.error("Failed to load assignments.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const handleSubmit = async () => {
    if (!fileUrl.trim()) {
      toast.error("Please provide a link or note for your submission.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/assignments/${submitModal.id}/submit`, { file_url: fileUrl });
      toast.success("Assignment submitted.");
      setSubmitModal(null);
      setFileUrl("");
      load();
    } catch {
      toast.error("Failed to submit assignment.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Assignments</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">View, submit, and track your assignments</p>

        {loading ? (
          <p className="text-center py-16 text-slate-400">Loading...</p>
        ) : assignments.length === 0 ? (
          <p className="text-center py-16 text-slate-400">No assignments yet.</p>
        ) : (
          <div className="space-y-3">
            {assignments.map((a) => (
              <div key={a.id} className="glass-card p-5 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-semibold">{a.title}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_BADGE[a.submission_status]}`}>{a.submission_status.replace("_", " ")}</span>
                  </div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{a.subject_name}</p>
                  <p className={`text-xs flex items-center gap-1 mt-1 ${a.is_overdue ? "text-danger" : a.is_due_today ? "text-warning font-semibold" : "text-slate-400"}`}>
                    {a.is_overdue ? <FiAlertCircle /> : <FiClock />}
                    {a.is_due_today ? "Due today" : a.is_overdue ? `Was due ${a.due_date}` : `Due ${a.due_date}`}
                  </p>
                  {a.grade && <p className="text-sm text-success font-semibold mt-1 flex items-center gap-1"><FiCheckCircle /> Grade: {a.grade}</p>}
                </div>
                {a.submission_status !== "graded" && (
                  <button onClick={() => setSubmitModal(a)} className="btn-secondary !py-2 flex items-center gap-2 text-sm">
                    <FiUpload /> {a.submission_status === "not_submitted" ? "Submit" : "Update Submission"}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <Modal open={!!submitModal} onClose={() => setSubmitModal(null)} title={`Submit — ${submitModal?.title}`}>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">{submitModal?.description}</p>
        <label className="text-sm font-medium mb-1 block">Submission link or note</label>
        <input className="input-field mb-4" placeholder="https://drive.google.com/..." value={fileUrl} onChange={(e) => setFileUrl(e.target.value)} />
        <button onClick={handleSubmit} disabled={submitting} className="btn-primary w-full disabled:opacity-60">
          {submitting ? "Submitting..." : "Submit Assignment"}
        </button>
      </Modal>
    </DashboardLayout>
  );
}
