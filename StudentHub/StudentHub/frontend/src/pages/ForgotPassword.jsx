import { useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { FiMail } from "react-icons/fi";
import api from "../services/api";
import ThemeToggle from "../components/ThemeToggle";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const value = email.trim().toLowerCase();
    if (!value) { setError("Please enter your email."); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) { setError("Please enter a valid email address."); return; }
    if (!/^[a-zA-Z0-9](\.?[a-zA-Z0-9_-]){0,63}@gmail\.com$/.test(value)) {
      setError("Only Gmail addresses (@gmail.com) are allowed.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email });
      toast.success(data.message);
      setError("");
      setSent(true);
    } catch (err) {
      // 503 = the server has no email set up (a real setup message), 429 = too many requests. Never show "sent" for these.
      setError(
        !err.response
          ? "Can't reach the server. Check your internet connection and try again."
          : typeof err.response.data?.detail === "string"
            ? err.response.data.detail
            : "Please enter a valid email address."
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
        <h1 className="text-2xl font-display font-bold text-center mb-1">Forgot password</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center mb-8">
          We'll email you a secure reset link — it expires in 15 minutes.
        </p>

        {sent ? (
          <div className="text-center">
            <p className="text-sm text-slate-600 dark:text-slate-300 mb-6">
              If <strong>{email}</strong> is registered, a reset link is on its way to your Gmail inbox.
            </p>
            <Link to="/login" className="text-primary font-medium hover:underline text-sm">
              Back to login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-1 block">Gmail address</label>
              <div className="relative">
                <FiMail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="email"
                  className="input-field pl-11"
                  placeholder="you@gmail.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              {error && <p className="input-error">{error}</p>}
            </div>

            <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
              {submitting ? "Sending..." : "Send reset link"}
            </button>

            <p className="text-center text-sm text-slate-500 dark:text-slate-400">
              <Link to="/login" className="text-primary font-medium hover:underline">
                Back to login
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
