import { useEffect, useState } from "react";
import Markdown from "../../components/Markdown";
import toast from "react-hot-toast";
import {
  FiUpload, FiFile, FiImage, FiCpu, FiCalendar, FiClock, FiChevronLeft, FiChevronRight,
  FiCheck, FiX, FiRotateCw, FiBookOpen, FiList, FiMoon, FiTrash2, FiPlus,
} from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";
import AIStatusBanner from "../../components/AIStatusBanner";

const pad = (n) => String(n).padStart(2, "0");
const today = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
const errText = (err, fallback) => {
  const d = err.response?.data?.detail;
  if (Array.isArray(d)) return d[0]?.msg?.replace(/^Value error, /, "") || fallback;
  return d || fallback;
};
const TABS = [
  { key: "notes", label: "Short Notes", icon: FiBookOpen },
  { key: "topics", label: "Important Topics", icon: FiList },
  { key: "explain", label: "Topic Explanations", icon: FiBookOpen },
  { key: "flashcards", label: "Flashcards", icon: FiFile },
  { key: "mcqs", label: "MCQs", icon: FiCheck },
  { key: "viva", label: "Viva Questions", icon: FiCpu },
  { key: "formula", label: "Formula Sheet", icon: FiList },
  { key: "planner", label: "Study Planner", icon: FiCalendar },
  { key: "lastnight", label: "Last Night Mode", icon: FiMoon },
];

function FlashcardDeck({ cards }) {
  const [i, setI] = useState(0);
  const [flipped, setFlipped] = useState(false);
  if (cards.length === 0) return <p className="text-sm text-slate-400">No flashcards generated.</p>;
  const card = cards[i];
  const go = (dir) => { setFlipped(false); setI((prev) => (prev + dir + cards.length) % cards.length); };
  return (
    <div className="flex flex-col items-center">
      <button
        onClick={() => setFlipped(!flipped)}
        className="w-full max-w-lg h-56 glass-card flex items-center justify-center p-6 text-center cursor-pointer select-none"
      >
        <p className="text-lg font-medium">{flipped ? card.back : card.front}</p>
      </button>
      <p className="text-xs text-slate-400 mt-2">{flipped ? "Answer — tap to flip back" : "Question — tap to reveal answer"}</p>
      <div className="flex items-center gap-4 mt-4">
        <button onClick={() => go(-1)} className="w-9 h-9 rounded-full glass-card flex items-center justify-center"><FiChevronLeft /></button>
        <span className="text-sm text-slate-500">{i + 1} / {cards.length}</span>
        <button onClick={() => go(1)} className="w-9 h-9 rounded-full glass-card flex items-center justify-center"><FiChevronRight /></button>
      </div>
    </div>
  );
}

function MCQQuiz({ mcqs }) {
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [showKey, setShowKey] = useState(false);
  if (mcqs.length === 0) return <p className="text-sm text-slate-400">No MCQs generated.</p>;
  const score = mcqs.filter((q) => answers[q.id] === q.correct_index).length;

  return (
    <div className="space-y-5">
      {mcqs.map((q, qi) => (
        <div key={q.id} className="glass-card p-4">
          <p className="text-sm font-medium mb-3">{qi + 1}. {q.question}</p>
          <div className="space-y-2">
            {q.options.map((opt, oi) => {
              const chosen = answers[q.id] === oi;
              const reveal = submitted || showKey;
              const isCorrect = reveal && oi === q.correct_index;
              const isWrongChoice = submitted && chosen && oi !== q.correct_index;
              return (
                <button
                  key={oi}
                  disabled={submitted}
                  onClick={() => setAnswers({ ...answers, [q.id]: oi })}
                  className={`w-full text-left text-sm px-3 py-2 rounded-lg border transition-colors ${
                    isCorrect ? "bg-success/10 border-success text-success" :
                    isWrongChoice ? "bg-danger/10 border-danger text-danger" :
                    chosen ? "bg-primary/10 border-primary" : "border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5"
                  }`}
                >
                  {opt}
                </button>
              );
            })}
          </div>
          {(submitted || showKey) && (
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
              <span className="font-semibold text-success">Answer: {String.fromCharCode(65 + q.correct_index)}.</span> {q.explanation}
            </p>
          )}
        </div>
      ))}
      {!submitted ? (
        <div className="flex gap-3">
          <button onClick={() => setSubmitted(true)} className="btn-primary">Submit Quiz</button>
          <button onClick={() => setShowKey(!showKey)} className="btn-secondary !py-2 text-sm">{showKey ? "Hide answers" : "Show answers"}</button>
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <p className="font-display font-bold">Score: {score}/{mcqs.length}</p>
          <button onClick={() => { setSubmitted(false); setShowKey(false); setAnswers({}); }} className="btn-secondary !py-2 text-sm flex items-center gap-1.5"><FiRotateCw size={13} /> Retry</button>
        </div>
      )}
    </div>
  );
}

export default function StudyCoach() {
  const [materials, setMaterials] = useState([]);
  const [plans, setPlans] = useState([]);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(null);
  const [examDate, setExamDate] = useState(today());
  const [dailyHours, setDailyHours] = useState(1);
  const [generating, setGenerating] = useState(false);
  const [activePlan, setActivePlan] = useState(null);
  const [tab, setTab] = useState("notes");
  const [aiConfigured, setAiConfigured] = useState(true);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => { api.get("/ai/status").then(({ data }) => setAiConfigured(data.configured)).catch(() => {}); }, []);

  const load = () => {
    setLoadError(false);
    api.get("/study-coach/materials").then(({ data }) => setMaterials(data)).catch(() => setLoadError(true));
    api.get("/study-coach/plans").then(({ data }) => setPlans(data)).catch(() => setLoadError(true));
  };
  useEffect(() => { load(); }, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) { toast.error("Choose a file first."); return; }
    if (file.size > 15 * 1024 * 1024) { toast.error("File is too large. Maximum size is 15 MB."); return; }
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/study-coach/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setUploaded(data);
      toast.success(`Detected subject: ${data.subject}`);
      load();
    } catch (err) {
      toast.error(errText(err, "Upload failed."));
    } finally {
      setUploading(false);
    }
  };

  const pickMaterial = (m) => { setUploaded({ id: m.id, filename: m.filename, subject: m.subject, preview: m.preview }); setFile(null); window.scrollTo({ top: 0, behavior: "smooth" }); };

  const deleteMaterial = async (id, e) => {
    e.stopPropagation();
    try {
      await api.delete(`/study-coach/materials/${id}`);
      if (uploaded?.id === id) setUploaded(null);
      load();
    } catch {
      toast.error("Couldn't delete that upload.");
    }
  };

  const handleGenerate = async () => {
    if (!uploaded) return;
    setGenerating(true);
    try {
      const { data } = await api.post("/study-coach/generate", { material_id: uploaded.id, exam_date: examDate, daily_hours: Number(dailyHours) });
      setActivePlan(data);
      setTab("notes");
      load();
    } catch (err) {
      toast.error(errText(err, "Couldn't generate your study plan."));
    } finally {
      setGenerating(false);
    }
  };

  const openPlan = async (id) => {
    try {
      const { data } = await api.get(`/study-coach/plans/${id}`);
      setActivePlan(data);
      setUploaded(null);
      setTab("notes");
    } catch {
      toast.error("Couldn't open that plan.");
    }
  };

  const deletePlan = async (id, e) => {
    e.stopPropagation();
    try {
      await api.delete(`/study-coach/plans/${id}`);
      if (activePlan?.id === id) setActivePlan(null);
      load();
    } catch {
      toast.error("Couldn't delete that plan.");
    }
  };

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">AI Study Coach</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          Upload your notes — the subject is detected automatically — then get short notes, flashcards, MCQs, viva questions, and a day-by-day plan until your exam.
        </p>

        <AIStatusBanner />

        {loadError && !activePlan && (
          <div className="mb-4 p-3 rounded-xl bg-danger/10 border border-danger/30 text-sm text-danger flex items-center justify-between">
            Couldn't load your saved study material. <button onClick={load} className="underline font-medium">Retry</button>
          </div>
        )}

        {!activePlan && (
          <div className="grid lg:grid-cols-3 gap-4 mb-6">
            <form onSubmit={handleUpload} className="glass-card p-5 lg:col-span-2 space-y-4">
              <p className="font-display font-semibold flex items-center gap-2"><FiUpload /> Upload your notes</p>
              <input
                type="file"
                accept=".pdf,.docx,.pptx,.jpg,.jpeg,.png,.webp"
                className="input-field"
                onChange={(e) => { setFile(e.target.files[0]); setUploaded(null); }}
              />
              <p className="text-xs text-slate-400">PDF, DOCX, PPTX, or an image (including handwritten notes) — max 15 MB.</p>
              <button type="submit" disabled={uploading} className="btn-primary !py-2.5 disabled:opacity-60">
                {uploading ? "Analysing..." : "Upload & Detect Subject"}
              </button>

              {uploaded && (
                <div className="p-4 rounded-xl bg-primary/5 border border-primary/20">
                  <p className="text-xs text-slate-400 mb-1">Detected subject{uploaded.filename ? ` · ${uploaded.filename}` : ""}</p>
                  <p className="font-display font-bold text-lg text-primary">{uploaded.subject}</p>
                  {uploaded.preview && <p className="text-xs text-slate-400 mt-2 line-clamp-3">{uploaded.preview}</p>}

                  <div className="grid sm:grid-cols-2 gap-3 mt-4">
                    <div>
                      <label className="text-xs font-medium mb-1 block">Exam date</label>
                      <input type="date" min={today()} className="input-field !py-2" value={examDate} onChange={(e) => setExamDate(e.target.value)} />
                    </div>
                    <div>
                      <label className="text-xs font-medium mb-1 block">Daily study hours</label>
                      <input type="number" min="0.25" max="16" step="0.25" className="input-field !py-2" value={dailyHours} onChange={(e) => setDailyHours(e.target.value)} />
                    </div>
                  </div>
                  <button onClick={handleGenerate} disabled={generating || !aiConfigured} className="btn-primary w-full !py-2.5 mt-4 disabled:opacity-60 flex items-center justify-center gap-2">
                    <FiCpu /> {generating ? "Generating — this can take up to a minute..." : !aiConfigured ? "AI not configured" : "Generate My Study Plan"}
                  </button>
                </div>
              )}
            </form>

            <div className="glass-card p-5">
              <p className="font-display font-semibold mb-3">My study plans</p>
              {plans.length === 0 ? (
                <p className="text-sm text-slate-400">No plans yet — upload notes to create your first one.</p>
              ) : (
                <div className="space-y-2">
                  {plans.map((p) => (
                    <div key={p.id} onClick={() => openPlan(p.id)} className="p-3 rounded-xl bg-slate-50 dark:bg-white/5 hover:bg-primary/5 cursor-pointer flex items-center justify-between group">
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{p.subject}</p>
                        <p className="text-xs text-slate-400 flex items-center gap-1"><FiClock size={11} /> Exam {p.exam_date}</p>
                      </div>
                      <button onClick={(e) => deletePlan(p.id, e)} className="opacity-0 group-hover:opacity-100 text-danger p-1"><FiTrash2 size={14} /></button>
                    </div>
                  ))}
                </div>
              )}

              {materials.length > 0 && (
                <>
                  <p className="font-display font-semibold mt-5 mb-2 text-sm">My uploads</p>
                  <div className="space-y-2 max-h-56 overflow-y-auto">
                    {materials.map((m) => (
                      <div key={m.id} onClick={() => pickMaterial(m)} title="Generate a new plan from this upload" className={`p-3 rounded-xl hover:bg-primary/5 cursor-pointer flex items-center justify-between group ${uploaded?.id === m.id ? "bg-primary/10" : "bg-slate-50 dark:bg-white/5"}`}>
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate flex items-center gap-1.5">{m.kind === "image" ? <FiImage size={12} /> : <FiFile size={12} />} {m.filename}</p>
                          <p className="text-xs text-slate-400 truncate">{m.subject}</p>
                        </div>
                        <button onClick={(e) => deleteMaterial(m.id, e)} aria-label="Delete upload" className="opacity-0 group-hover:opacity-100 text-danger p-1"><FiTrash2 size={14} /></button>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {activePlan && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-xs text-slate-400">Study plan for</p>
                <p className="font-display font-bold text-lg">{activePlan.subject}</p>
              </div>
              <button onClick={() => setActivePlan(null)} className="btn-secondary !py-2 text-sm flex items-center gap-1.5"><FiPlus size={14} /> New / Back to list</button>
            </div>

            <div className="flex flex-wrap gap-2 mb-5">
              {TABS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t.key ? "bg-primary text-white" : "glass-card text-slate-500"}`}
                >
                  <t.icon size={14} /> {t.label}
                </button>
              ))}
            </div>

            <div className="glass-card p-5">
              {tab === "notes" && <Markdown text={activePlan.short_notes || "No notes generated."} />}

              {tab === "topics" && (
                <ol className="space-y-2 list-decimal list-inside">
                  {(activePlan.important_topics || []).map((t, i) => <li key={i} className="text-sm">{t}</li>)}
                </ol>
              )}

              {tab === "explain" && (
                (activePlan.topic_explanations || []).length === 0 ? (
                  <p className="text-sm text-slate-400">No topic explanations were generated for this plan — generate a new plan to get them.</p>
                ) : (
                  <div className="space-y-3">
                    {activePlan.topic_explanations.map((t, i) => (
                      <div key={i} className="p-4 rounded-xl bg-slate-50 dark:bg-white/5">
                        <p className="font-display font-semibold text-sm mb-1">{t.topic}</p>
                        <Markdown text={t.explanation} className="text-slate-600 dark:text-slate-300" />
                      </div>
                    ))}
                  </div>
                )
              )}

              {tab === "flashcards" && <FlashcardDeck cards={activePlan.flashcards || []} />}
              {tab === "mcqs" && <MCQQuiz mcqs={activePlan.mcqs || []} />}

              {tab === "viva" && (
                <ul className="space-y-2">
                  {(activePlan.viva_questions || []).map((q, i) => (
                    <li key={i} className="text-sm p-3 rounded-lg bg-slate-50 dark:bg-white/5">{q}</li>
                  ))}
                </ul>
              )}

              {tab === "formula" && (
                <ul className="space-y-2">
                  {(activePlan.formula_sheet || []).map((f, i) => (
                    <li key={i} className="text-sm font-mono p-2.5 rounded-lg bg-slate-50 dark:bg-white/5">{f}</li>
                  ))}
                </ul>
              )}

              {tab === "planner" && (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {(activePlan.planner || []).map((d, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-white/5">
                      <div className="min-w-0 pr-3">
                        <p className="text-sm font-medium">{d.date}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-300">{d.focus_topic}</p>
                        {(d.tasks || []).length > 0 && <ul className="mt-1 list-disc list-inside text-xs text-slate-400">{d.tasks.map((t, k) => <li key={k}>{t}</li>)}</ul>}
                      </div>
                      <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary font-medium">{d.target_hours}h</span>
                    </div>
                  ))}
                </div>
              )}

              {tab === "lastnight" && (
                <div className="p-4 rounded-xl bg-warning/10 border border-warning/20">
                  <p className="text-xs font-semibold text-warning uppercase tracking-wide mb-2 flex items-center gap-1.5"><FiMoon /> Crash Revision</p>
                  <Markdown text={activePlan.last_night_mode || "No crash revision generated."} />
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
