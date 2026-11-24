import { useEffect, useState } from "react";
import { FiZap, FiAward } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import api from "../../services/api";

const ACTIVITY_LABEL = {
  attendance: "Attendance marked present",
  early_submission: "Early assignment submission",
  on_time_submission: "On-time assignment submission",
  event: "Event participation",
  helping_others: "Helping others",
  perfect_attendance_week: "Perfect attendance week",
};

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 3600) return `${Math.max(1, Math.floor(diff / 60))}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function SkillWallet() {
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/skill-wallet/me").then(({ data }) => setWallet(data)).finally(() => setLoading(false));
  }, []);

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Skill Wallet</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Earn XP for attendance, on-time submissions, events, and helping others.</p>

        {loading ? (
          <p className="text-center py-16 text-slate-400">Loading...</p>
        ) : (
          <div className="grid lg:grid-cols-3 gap-4">
            <div className="glass-card p-6 lg:col-span-1 text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white text-2xl mx-auto mb-4"><FiZap /></div>
              <p className="text-4xl font-display font-bold">{wallet.total_xp}</p>
              <p className="text-sm text-slate-400 mb-4">Total XP</p>
              <span className="inline-block text-sm px-3 py-1 rounded-full bg-primary/10 text-primary font-semibold mb-3">Level {wallet.level}</span>
              <div className="w-full h-2.5 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-r from-primary to-secondary" style={{ width: `${wallet.xp_into_level}%` }} />
              </div>
              <p className="text-xs text-slate-400 mt-2">{wallet.xp_to_next_level} XP to Level {wallet.level + 1}</p>
            </div>

            <div className="glass-card p-6 lg:col-span-2">
              <p className="font-display font-semibold mb-4 flex items-center gap-2"><FiAward /> Badges earned</p>
              {wallet.badges.length === 0 ? (
                <p className="text-sm text-slate-400">No badges yet — keep attending classes and submitting on time!</p>
              ) : (
                <div className="grid sm:grid-cols-2 gap-3">
                  {wallet.badges.map((b) => (
                    <div key={b.id} className="p-3 rounded-xl bg-warning/10 flex items-start gap-3">
                      <FiAward className="text-warning mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-sm font-semibold">{b.name}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{b.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <p className="font-display font-semibold mt-6 mb-3">Recent activity</p>
              {wallet.recent.length === 0 ? (
                <p className="text-sm text-slate-400">Nothing yet.</p>
              ) : (
                <div className="space-y-1">
                  {wallet.recent.map((r, i) => (
                    <div key={i} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 dark:bg-white/5">
                      <div>
                        <p className="text-sm">{ACTIVITY_LABEL[r.activity] || r.activity}{r.note ? ` · ${r.note}` : ""}</p>
                        <p className="text-xs text-slate-400">{timeAgo(r.created_at)}</p>
                      </div>
                      <span className="text-sm font-semibold text-success">+{r.xp} XP</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
