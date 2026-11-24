import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FiZap, FiAward } from "react-icons/fi";
import api from "../services/api";

/** Compact XP + level + badges widget for the student dashboard. */
export default function SkillWalletWidget() {
  const [wallet, setWallet] = useState(null);

  useEffect(() => {
    api.get("/skill-wallet/me").then(({ data }) => setWallet(data)).catch(() => {});
  }, []);

  if (!wallet) return null;

  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="font-display font-semibold flex items-center gap-2"><FiZap className="text-warning" /> Skill Wallet</p>
        <Link to="/student/skill-wallet" className="text-xs text-primary font-medium hover:underline">View all →</Link>
      </div>

      <div className="flex items-end justify-between mb-2">
        <div>
          <p className="text-3xl font-display font-bold text-primary">{wallet.total_xp}</p>
          <p className="text-xs text-slate-400">Total XP · Level {wallet.level}</p>
        </div>
        <p className="text-xs text-slate-400">{wallet.xp_to_next_level} XP to level {wallet.level + 1}</p>
      </div>
      <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden mb-4">
        <div className="h-full rounded-full bg-gradient-to-r from-primary to-secondary transition-all duration-500" style={{ width: `${wallet.xp_into_level}%` }} />
      </div>

      {wallet.badges.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {wallet.badges.map((b) => (
            <span key={b.id} title={b.description} className="text-[11px] px-2.5 py-1 rounded-full bg-warning/10 text-warning font-medium flex items-center gap-1">
              <FiAward size={11} /> {b.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
