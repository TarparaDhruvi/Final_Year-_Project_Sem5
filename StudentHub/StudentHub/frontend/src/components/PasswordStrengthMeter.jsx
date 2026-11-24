function getStrength(password) {
  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[!@#$%^&*(),.?":{}|<>_\-+=[\]/\\;']/.test(password)) score++;
  return score;
}

const LABELS = ["Too weak", "Weak", "Fair", "Good", "Strong"];
const COLORS = ["bg-slate-300", "bg-danger", "bg-warning", "bg-secondary", "bg-success"];

export default function PasswordStrengthMeter({ password }) {
  const score = password ? getStrength(password) : 0;

  return (
    <div className="mt-2" aria-live="polite">
      <div className="flex gap-1.5">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${
              i < score ? COLORS[score] : "bg-slate-200 dark:bg-white/10"
            }`}
          />
        ))}
      </div>
      {password && (
        <p className="text-xs mt-1 text-slate-500 dark:text-slate-400">{LABELS[score]}</p>
      )}
    </div>
  );
}
