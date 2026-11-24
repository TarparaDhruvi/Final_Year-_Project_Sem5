import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiMessageSquare, FiArrowUp, FiSend, FiCornerDownRight } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

export default function DoubtWall() {
  const { user } = useAuth();
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState("");
  const [doubts, setDoubts] = useState([]);
  const [question, setQuestion] = useState("");
  const [replyDrafts, setReplyDrafts] = useState({});
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const endpoint = user.role === "faculty" ? "/faculty/me/subjects" : "/subjects";
    api.get(endpoint).then(({ data }) => setSubjects(data)).catch(() => toast.error("Failed to load subjects."));
  }, [user.role]);

  const load = async (sid) => {
    if (!sid) return;
    setLoading(true);
    try {
      const { data } = await api.get(`/doubts/subject/${sid}`);
      setDoubts(data);
    } catch {
      toast.error("Failed to load doubts.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(subjectId); }, [subjectId]);

  const ask = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;
    setSubmitting(true);
    try {
      await api.post("/doubts", { subject_id: subjectId, question });
      toast.success("Posted anonymously.");
      setQuestion("");
      load(subjectId);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Couldn't post your question.");
    } finally {
      setSubmitting(false);
    }
  };

  const upvote = async (id) => {
    setDoubts((prev) => prev.map((d) => d.id === id ? { ...d, upvotes: d.upvotes + (d.has_upvoted ? -1 : 1), has_upvoted: !d.has_upvoted } : d));
    try {
      await api.post(`/doubts/${id}/upvote`);
      load(subjectId);
    } catch {
      toast.error("Couldn't register your upvote.");
      load(subjectId);
    }
  };

  const reply = async (id) => {
    const text = replyDrafts[id];
    if (!text?.trim()) return;
    try {
      await api.put(`/doubts/${id}/reply`, { reply: text });
      toast.success("Reply posted.");
      setReplyDrafts({ ...replyDrafts, [id]: "" });
      load(subjectId);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Couldn't post your reply.");
    }
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Anonymous Doubt Wall</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          {user.role === "student" ? "Ask anything without your name attached — faculty reply publicly." : "Reply to student questions — the most upvoted ones rise to the top."}
        </p>

        <div className="glass-card p-4 mb-5">
          <select className="input-field !py-2 w-auto" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
            <option value="">Select a subject</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>

        {!subjectId ? (
          <p className="text-center py-16 text-slate-400">Choose a subject to see its Doubt Wall.</p>
        ) : (
          <>

            {user.role === "student" && (
              <form onSubmit={ask} className="glass-card p-4 mb-5 flex gap-2">
                <input className="input-field flex-1" placeholder="Ask your question anonymously..." value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={2000} />
                <button type="submit" disabled={submitting} className="btn-primary !py-2.5 !px-4 flex items-center gap-2 disabled:opacity-60"><FiSend /> Post</button>
              </form>
            )}

            {loading ? (
              <p className="text-center py-10 text-slate-400">Loading...</p>
            ) : doubts.length === 0 ? (
              <div className="glass-card p-10 text-center text-slate-400">No doubts posted yet for this subject.</div>
            ) : (
              <div className="space-y-3">
                {doubts.map((d) => (
                  <div key={d.id} className="glass-card p-4">
                    <div className="flex items-start gap-3">
                      <button
                        onClick={() => upvote(d.id)}
                        className={`flex flex-col items-center px-2.5 py-1.5 rounded-lg flex-shrink-0 transition-colors ${d.has_upvoted ? "bg-primary text-white" : "bg-slate-100 dark:bg-white/10 text-slate-500 hover:bg-primary/10"}`}
                      >
                        <FiArrowUp size={14} />
                        <span className="text-xs font-bold">{d.upvotes}</span>
                      </button>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm flex items-center gap-2">
                          {d.question}
                          {d.is_mine && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-medium flex-shrink-0">Your question</span>}
                        </p>
                        {d.reply ? (
                          <div className="mt-2 pl-3 border-l-2 border-success/40 flex items-start gap-1.5">
                            <FiCornerDownRight className="text-success mt-0.5 flex-shrink-0" size={13} />
                            <p className="text-sm text-slate-600 dark:text-slate-300">{d.reply}</p>
                          </div>
                        ) : user.role === "faculty" ? (
                          <div className="flex gap-2 mt-2">
                            <input
                              className="input-field !py-1.5 text-sm flex-1"
                              placeholder="Write a reply..."
                              value={replyDrafts[d.id] || ""}
                              onChange={(e) => setReplyDrafts({ ...replyDrafts, [d.id]: e.target.value })}
                            />
                            <button onClick={() => reply(d.id)} className="btn-primary !py-1.5 !px-3 text-sm">Reply</button>
                          </div>
                        ) : (
                          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1"><FiMessageSquare size={11} /> Waiting for a faculty reply</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
