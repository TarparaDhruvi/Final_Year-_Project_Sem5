import { useEffect, useState } from "react";
import { FiAlertTriangle } from "react-icons/fi";
import api from "../services/api";

/** Shown on AI pages when OPENAI_API_KEY isn't set — so the user learns that up front, not after a failed request. */
export default function AIStatusBanner() {
  const [configured, setConfigured] = useState(true);

  useEffect(() => {
    api.get("/ai/status").then(({ data }) => setConfigured(data.configured)).catch(() => {});
  }, []);

  if (configured) return null;
  return (
    <div className="mb-5 p-4 rounded-xl bg-warning/10 border border-warning/30 flex items-start gap-3">
      <FiAlertTriangle className="text-warning mt-0.5 flex-shrink-0" />
      <div>
        <p className="text-sm font-semibold">AI isn't set up yet</p>
        <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5">
          The server has no OpenAI API key. Ask your Admin to add <code className="font-mono">OPENAI_API_KEY</code> to
          <code className="font-mono"> backend/.env</code> and restart. Everything else on this page still works.
        </p>
      </div>
    </div>
  );
}
