import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FiSearch, FiUser, FiUserCheck, FiBook, FiFileText, FiCalendar, FiCommand } from "react-icons/fi";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";

const TYPE_ICON = { student: FiUser, faculty: FiUserCheck, subject: FiBook, assignment: FiFileText, note: FiFileText, timetable: FiCalendar };

/** Ctrl+K / Cmd+K command palette — searches students, faculty, subjects, assignments, notes, timetable (role-scoped). */
export default function GlobalSearch() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
    else { setQuery(""); setResults([]); }
  }, [open]);

  useEffect(() => {
    if (query.trim().length < 2) { setResults([]); return; }
    setLoading(true);
    const t = setTimeout(() => {
      api.get("/search", { params: { q: query } })
        .then(({ data }) => setResults(data.results))
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  if (!user) return null;

  const go = (r) => {
    setOpen(false);
    if (r.link) navigate(r.link);
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="hidden md:flex items-center gap-2 px-3 py-2 rounded-xl glass-card text-sm text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
        aria-label="Open global search"
      >
        <FiSearch size={14} />
        <span>Search...</span>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-white/10 flex items-center gap-0.5"><FiCommand size={9} />K</span>
      </button>

      {open && (
        <div className="fixed inset-0 z-[200] flex items-start justify-center pt-24 px-4">
          <div className="absolute inset-0 bg-dark/50 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="relative glass-card w-full max-w-xl max-h-[70vh] overflow-hidden flex flex-col">
            <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 dark:border-white/10">
              <FiSearch className="text-slate-400 flex-shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search students, faculty, subjects, assignments, notes..."
                className="flex-1 bg-transparent outline-none text-sm"
              />
              <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-white/10 text-slate-400 flex-shrink-0">ESC</kbd>
            </div>

            <div className="overflow-y-auto">
              {query.trim().length < 2 ? (
                <p className="text-sm text-slate-400 text-center py-10">Type at least 2 characters to search.</p>
              ) : loading ? (
                <p className="text-sm text-slate-400 text-center py-10">Searching...</p>
              ) : results.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-10">No results for "{query}".</p>
              ) : (
                <div className="p-2">
                  {results.map((r, i) => {
                    const Icon = TYPE_ICON[r.type] || FiSearch;
                    return (
                      <button
                        key={i}
                        onClick={() => go(r)}
                        disabled={!r.link}
                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-primary/5 text-left disabled:opacity-60 disabled:hover:bg-transparent"
                      >
                        <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><Icon size={14} /></div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate">{r.label}</p>
                          <p className="text-xs text-slate-400 truncate">{r.sublabel}</p>
                        </div>
                        <span className="text-[10px] text-slate-400 uppercase flex-shrink-0">{r.type}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
