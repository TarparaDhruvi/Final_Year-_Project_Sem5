/** Glass stat tile used across all three dashboards. */
export default function StatCard({ label, value, icon: Icon, tone = "primary", loading }) {
  const tones = {
    primary: "bg-primary/10 text-primary",
    success: "bg-success/10 text-success",
    warning: "bg-warning/10 text-warning",
    danger: "bg-danger/10 text-danger",
    secondary: "bg-secondary/10 text-secondary",
  };
  return (
    <div className="glass-card p-5">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${tones[tone]}`}><Icon /></div>
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      {loading ? (
        <div className="h-8 w-16 mt-1 rounded-lg bg-slate-200 dark:bg-white/10 animate-pulse" />
      ) : (
        <p className="text-2xl font-display font-bold mt-1">{value}</p>
      )}
    </div>
  );
}
