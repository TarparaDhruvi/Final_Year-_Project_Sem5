import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { FiLock } from "react-icons/fi";
import api from "../services/api";
import PasswordStrengthMeter from "../components/PasswordStrengthMeter";
import ThemeToggle from "../components/ThemeToggle";

function validatePassword(password) {
  if (password.length < 8) return "Password must be at least 8 characters long.";
  if (!/[A-Z]/.test(password)) return "Password must include at least one uppercase letter.";
  if (!/[a-z]/.test(password)) return "Password must include at least one lowercase letter.";
  if (!/[0-9]/.test(password)) return "Password must include at least one number.";
  if (!/[!@#$%^&*(),.?":{}|<>_\-+=[\]/\\;']/.test(password))
    return "Password must include at least one special character.";
  return null;
}

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const navigate = useNavigate();

  const [form, setForm] = useState({ new_password: "", confirm_password: "" });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const validate = () => {
    const next = {};
    const passwordError = validatePassword(form.new_password);
    if (passwordError) next.new_password = passwordError;
    if (form.confirm_password !== form.new_password) {
      next.confirm_password = "Passwords do not match.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!token) {
      toast.error("This reset link is missing its token. Please request a new one.");
      return;
    }
    if (!validate()) return;
    setSubmitting(true);
    try {
      const { data } = await api.post("/auth/reset-password", { token, ...form });
      toast.success(data.message);
      navigate("/login");
    } catch (err) {
      toast.error(
        !err.response
          ? "Can't reach the server. Check your internet connection and try again."
          : typeof err.response.data?.detail === "string"
            ? err.response.data.detail
            : err.response.data?.detail?.[0]?.msg?.replace(/^Value error, /, "") || "This reset link is invalid or has expired."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 bg-gradient-to-br from-surface via-white to-secondary/10 dark:from-dark dark:via-dark dark:to-primary/10">
      <div className="absolute top-6 right-6">
        <ThemeToggle />
      </div>

      <div className="glass-card w-full max-w-md p-8">
        <h1 className="text-2xl font-display font-bold text-center mb-1">Set a new password</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center mb-8">
          Choose a strong password you haven't used before.
        </p>

        {!token && (
          <p className="text-sm text-danger text-center mb-4">
            No reset token found in this link. Please request a new one from{" "}
            <Link to="/forgot-password" className="underline">Forgot password</Link>.
          </p>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">New password</label>
            <div className="relative">
              <FiLock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="password"
                className="input-field pl-11"
                placeholder="••••••••"
                value={form.new_password}
                onChange={(e) => setForm({ ...form, new_password: e.target.value })}
              />
            </div>
            <PasswordStrengthMeter password={form.new_password} />
            {errors.new_password && <p className="input-error">{errors.new_password}</p>}
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">Confirm new password</label>
            <div className="relative">
              <FiLock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="password"
                className="input-field pl-11"
                placeholder="••••••••"
                value={form.confirm_password}
                onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
              />
            </div>
            {errors.confirm_password && <p className="input-error">{errors.confirm_password}</p>}
          </div>

          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
            {submitting ? "Resetting..." : "Reset password"}
          </button>
        </form>
      </div>
    </div>
  );
}
