import { Link } from "react-router-dom";

/** Row of glass "quick action" cards. items: [{ to, label, desc, icon }] */
export default function QuickActions({ items }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
      {items.map((a) => (
        <Link
          key={a.to}
          to={a.to}
          className="glass-card p-4 group hover:-translate-y-1 hover:shadow-xl transition-all duration-200"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary text-white flex items-center justify-center mb-3 shadow-md shadow-primary/30 group-hover:scale-110 transition-transform">
            <a.icon />
          </div>
          <p className="text-sm font-semibold">{a.label}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{a.desc}</p>
        </Link>
      ))}
    </div>
  );
}
