import { FiAlertTriangle } from "react-icons/fi";

export default function ConfirmDialog({ open, title, message, confirmLabel = "Confirm", onConfirm, onCancel, danger = true }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-dark/40 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative glass-card w-full max-w-sm p-6 text-center">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-xl mx-auto mb-4 ${danger ? "bg-danger/10 text-danger" : "bg-primary/10 text-primary"}`}>
          <FiAlertTriangle />
        </div>
        <h3 className="font-display font-semibold mb-2">{title}</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">{message}</p>
        <div className="flex gap-3">
          <button onClick={onCancel} className="btn-secondary flex-1 !py-2.5">Cancel</button>
          <button
            onClick={onConfirm}
            className={`flex-1 !py-2.5 rounded-xl font-semibold text-white transition-colors ${danger ? "bg-danger hover:bg-danger/90" : "bg-primary hover:bg-primary/90"}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
