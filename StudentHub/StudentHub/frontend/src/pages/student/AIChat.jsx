import { useEffect, useRef, useState } from "react";
import Markdown from "../../components/Markdown";
import toast from "react-hot-toast";
import { FiSend, FiPlus, FiCopy, FiRefreshCw, FiMic, FiTrash2, FiCpu, FiMessageSquare, FiPaperclip, FiX } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Avatar from "../../components/Avatar";
import AIStatusBanner from "../../components/AIStatusBanner";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

const SUGGESTIONS = [
  "Explain deadlock in operating systems",
  "Generate 5 MCQs on DBMS normalization with answers",
  "Give me viva questions on Java OOP",
  "Debug: why does my Python loop never end?",
];

/** Renders ```fenced``` blocks as code (with a copy button) and everything else as plain text. */
function MessageBody({ text, onCopy }) {
  const parts = String(text).split(/```/);
  return (
    <>
      {parts.map((part, i) => {
        if (i % 2 === 0) return part.trim() ? <Markdown key={i} text={part} /> : null;
        const nl = part.indexOf("\n");
        const lang = nl > -1 && nl < 20 ? part.slice(0, nl).trim() : "";
        const code = (nl > -1 && nl < 20 ? part.slice(nl + 1) : part).replace(/\n$/, "");
        return (
          <div key={i} className="my-2 rounded-xl overflow-hidden border border-slate-200 dark:border-white/10 bg-slate-900 text-slate-100 text-left">
            <div className="flex items-center justify-between px-3 py-1 text-[11px] bg-slate-800 text-slate-300">
              <span>{lang || "code"}</span>
              <button type="button" onClick={() => onCopy(code)} className="hover:text-white flex items-center gap-1"><FiCopy size={11} /> Copy</button>
            </div>
            <pre className="p-3 overflow-x-auto text-xs font-mono whitespace-pre">{code}</pre>
          </div>
        );
      })}
    </>
  );
}

export default function AIChat() {
  const { user } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [listening, setListening] = useState(false);
  const [attachment, setAttachment] = useState(null);
  const fileInputRef = useRef(null);
  const bottomRef = useRef(null);
  const recognitionRef = useRef(null);

  const [historyError, setHistoryError] = useState(false);
  const loadSessions = async () => {
    try {
      const { data } = await api.get("/ai/sessions");
      setSessions(data);
      setHistoryError(false);
    } catch {
      setHistoryError(true);
    }
  };
  useEffect(() => { loadSessions(); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, sending]);

  const openSession = async (id) => {
    try {
      const { data } = await api.get(`/ai/sessions/${id}`);
      setActiveId(id);
      setMessages(data.messages);
    } catch {
      toast.error("Couldn't open that chat.");
    }
  };

  const newChat = () => { setActiveId(null); setMessages([]); setInput(""); };

  const deleteSession = async (id, e) => {
    e.stopPropagation();
    try {
      await api.delete(`/ai/sessions/${id}`);
      if (id === activeId) newChat();
      loadSessions();
    } catch {
      toast.error("Couldn't delete that chat.");
    }
  };

  const send = async (text, regenerate = false) => {
    const body = { session_id: activeId, message: text || "", regenerate };
    if (!regenerate) {
      setMessages((m) => [...m, { role: "user", content: text }]);
      setInput("");
    } else {
      setMessages((m) => (m[m.length - 1]?.role === "assistant" ? m.slice(0, -1) : m));
    }
    setSending(true);
    try {
      const { data } = await api.post("/ai/chat", body);
      setActiveId(data.session_id);
      setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
      loadSessions();
    } catch (err) {
      toast.error(err.response?.data?.detail || "The AI didn't respond. Please try again.");
      if (!regenerate) setMessages((m) => m.slice(0, -1));
    } finally {
      setSending(false);
    }
  };

  const sendWithAttachment = async () => {
    const text = input.trim();
    setMessages((m) => [...m, { role: "user", content: `${text}${text ? "\n\n" : ""}📎 ${attachment.name}` }]);
    setInput("");
    const file = attachment;
    setAttachment(null);
    setSending(true);
    try {
      const fd = new FormData();
      if (activeId) fd.append("session_id", activeId);
      fd.append("message", text);
      fd.append("file", file);
      const { data } = await api.post("/ai/chat/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setActiveId(data.session_id);
      setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
      loadSessions();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Couldn't process that file.");
      setMessages((m) => m.slice(0, -1));
    } finally {
      setSending(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (sending) return;
    if (attachment) { sendWithAttachment(); return; }
    const text = input.trim();
    if (!text) return;
    send(text);
  };

  const copy = async (text) => {
    try { await navigator.clipboard.writeText(text); toast.success("Copied to clipboard."); }
    catch { toast.error("Couldn't copy."); }
  };

  const toggleVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { toast.error("Voice input isn't supported in this browser — try Chrome or Edge."); return; }
    if (listening) { recognitionRef.current?.stop(); return; }
    const rec = new SR();
    rec.lang = "en-IN";
    rec.interimResults = false;
    rec.onresult = (ev) => setInput((prev) => (prev ? prev + " " : "") + ev.results[0][0].transcript);
    rec.onerror = () => toast.error("Couldn't hear you — check your microphone permission.");
    rec.onend = () => setListening(false);
    recognitionRef.current = rec;
    setListening(true);
    rec.start();
  };

  const lastAssistantIndex = messages.map((m) => m.role).lastIndexOf("assistant");

  return (
    <DashboardLayout>
      <div className="pt-2 flex gap-4 h-[calc(100vh-9rem)] min-h-[480px]">
        {/* History */}
        <aside className="hidden lg:flex flex-col w-64 glass-card p-3 flex-shrink-0">
          <button onClick={newChat} className="btn-primary !py-2.5 flex items-center justify-center gap-2 mb-3"><FiPlus /> New chat</button>
          <p className="text-[11px] uppercase font-semibold text-slate-400 px-2 mb-1">History</p>
          <div className="flex-1 overflow-y-auto space-y-1">
            {historyError ? (
              <p className="text-xs text-danger px-2 py-4">Couldn't load your chats. <button onClick={loadSessions} className="underline">Retry</button></p>
            ) : sessions.length === 0 ? (
              <p className="text-xs text-slate-400 px-2 py-4">No chats yet.</p>
            ) : sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => openSession(s.id)}
                className={`group flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer text-sm transition-colors ${s.id === activeId ? "bg-primary/10 text-primary" : "hover:bg-slate-100 dark:hover:bg-white/5"}`}
              >
                <FiMessageSquare className="flex-shrink-0" size={14} />
                <span className="truncate flex-1">{s.title}</span>
                <button onClick={(e) => deleteSession(s.id, e)} aria-label="Delete chat" className="opacity-0 group-hover:opacity-100 text-danger"><FiTrash2 size={13} /></button>
              </div>
            ))}
          </div>
        </aside>

        {/* Conversation */}
        <section className="flex-1 glass-card flex flex-col min-w-0">
          <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 dark:border-white/10">
            <p className="font-display font-semibold flex items-center gap-2"><FiCpu className="text-primary" /> StudentHub AI</p>
            <button onClick={newChat} className="lg:hidden text-sm text-primary font-medium flex items-center gap-1"><FiPlus /> New</button>
          </div>

          <div className="px-5 pt-4 empty:hidden"><AIStatusBanner /></div>

          <div className="flex-1 overflow-y-auto p-5 space-y-5">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white text-2xl mb-4"><FiCpu /></div>
                <p className="font-display font-semibold text-lg">How can I help, {user.full_name.split(" ")[0]}?</p>
                <div className="grid sm:grid-cols-2 gap-2 mt-6 max-w-xl w-full">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} onClick={() => send(s)} className="text-left text-sm p-3 rounded-xl border border-slate-200 dark:border-white/10 hover:bg-primary/5 hover:border-primary/30 transition-colors">{s}</button>
                  ))}
                </div>
              </div>
            ) : messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
                {m.role === "user" ? <Avatar user={user} size={32} /> : (
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white flex-shrink-0"><FiCpu size={15} /></div>
                )}
                <div className={`max-w-[85%] ${m.role === "user" ? "items-end" : ""}`}>
                  <div className={`px-4 py-3 rounded-2xl text-sm break-words ${m.role === "user" ? "bg-primary text-white rounded-tr-sm whitespace-pre-wrap" : "bg-slate-100 dark:bg-white/10 rounded-tl-sm"}`}>
                    {m.role === "user" ? m.content : <MessageBody text={m.content} onCopy={copy} />}
                  </div>
                  {m.role === "assistant" && (
                    <div className="flex gap-3 mt-1.5 ml-1 text-xs text-slate-400">
                      <button onClick={() => copy(m.content)} className="flex items-center gap-1 hover:text-primary"><FiCopy size={12} /> Copy</button>
                      {i === lastAssistantIndex && !sending && (
                        <button onClick={() => send("", true)} className="flex items-center gap-1 hover:text-primary"><FiRefreshCw size={12} /> Regenerate</button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white flex-shrink-0"><FiCpu size={15} /></div>
                <div className="px-4 py-3 rounded-2xl bg-slate-100 dark:bg-white/10 flex gap-1.5 items-center">
                  {[0, 1, 2].map((d) => <span key={d} className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: `${d * 0.15}s` }} />)}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSubmit} className="p-4 border-t border-slate-200 dark:border-white/10">
            {attachment && (
              <div className="flex items-center gap-2 mb-2 px-3 py-1.5 rounded-lg bg-primary/5 w-fit">
                <FiPaperclip size={12} className="text-primary" />
                <span className="text-xs text-primary font-medium">{attachment.name}</span>
                <button type="button" onClick={() => setAttachment(null)} aria-label="Remove attachment" className="text-primary hover:text-danger"><FiX size={12} /></button>
              </div>
            )}
            <div className="flex items-end gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.pptx,.jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={(e) => { if (e.target.files[0]) setAttachment(e.target.files[0]); e.target.value = ""; }}
              />
              <button type="button" onClick={() => fileInputRef.current?.click()} aria-label="Attach file" className="w-11 h-11 flex-shrink-0 rounded-xl glass-card flex items-center justify-center"><FiPaperclip /></button>
              <textarea
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(e); } }}
                placeholder={attachment ? "Add a note about this file (optional)…" : "Ask anything…  (Enter to send, Shift+Enter for a new line)"}
                className="input-field resize-none max-h-32"
                maxLength={8000}
              />
              <button type="button" onClick={toggleVoice} aria-label="Voice input" className={`w-11 h-11 flex-shrink-0 rounded-xl flex items-center justify-center transition-colors ${listening ? "bg-danger text-white animate-pulse" : "glass-card"}`}><FiMic /></button>
              <button type="submit" disabled={sending || (!input.trim() && !attachment)} aria-label="Send" className="btn-primary !p-0 w-11 h-11 flex-shrink-0 flex items-center justify-center disabled:opacity-50"><FiSend /></button>
            </div>
          </form>
        </section>
      </div>
    </DashboardLayout>
  );
}
