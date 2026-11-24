import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams, Navigate } from "react-router-dom";
import toast from "react-hot-toast";
import { FiMail, FiLock, FiEye, FiEyeOff, FiHash, FiShield, FiBookOpen, FiUser, FiAlertCircle, FiInfo } from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import ThemeToggle from "../components/ThemeToggle";

const GMAIL_REGEX = /^[a-zA-Z0-9](\.?[a-zA-Z0-9_-]){0,63}@gmail\.com$/;
const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const ID_REGEX = /^[0-9]+$/;

const ROLE_CONFIG = {
  admin: {
    title: "Admin Portal",
    icon: FiShield,
    idLabel: "Admin ID",
    idKey: "admin_id",
    idPlaceholder: "ADMIN001",
    requiresNumericId: false,
  },
  faculty: {
    title: "Faculty Portal",
    icon: FiBookOpen,
    idLabel: "Faculty ID",
    idKey: "faculty_id",
    idPlaceholder: "1024",
    requiresNumericId: true,
  },
  student: {
    title: "Student Portal",
    icon: FiUser,
    idLabel: null,
    idKey: null,
    idPlaceholder: null,
    requiresNumericId: false,
  },
};

function loginErrorMessage(err) {
  if (!err.response) return "Can't reach the server. Check your internet connection and try again.";
  const { status, data } = err.response;
  const detail = data?.detail;
  if (status === 422) {
    const first = Array.isArray(detail) ? detail[0]?.msg : null;
    return first ? first.replace(/^Value error, /, "") : "Please check the details you entered.";
  }
  if (status >= 500) return "Something went wrong on our side. Please try again in a moment.";
  if (typeof detail === "string") return detail;   // 401 wrong credentials, 403 disabled / unverified, 429 too many attempts
  return "Login failed. Please check your details and try again.";
}

export default function Login() {
  const { role } = useParams();
  const config = ROLE_CONFIG[role];
  const { login } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ idValue: "", email: "", password: "", rememberMe: false });
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [searchParams] = useSearchParams();
  const notice = searchParams.get("expired")
    ? "Your session expired. Please log in again."
    : searchParams.get("disabled")
      ? "This account has been disabled. Please contact your administrator."
      : "";

  if (!config) {
    return <Navigate to="/login" replace />;
  }

  const validate = () => {
    const next = {};
    if (config.idKey) {
      if (!form.idValue.trim()) {
        next.idValue = `Please enter your ${config.idLabel}.`;
      } else if (config.requiresNumericId && !ID_REGEX.test(form.idValue.trim())) {
        next.idValue = `${config.idLabel} must contain numbers only.`;
      }
    }
    const email = form.email.trim().toLowerCase();
    if (!email) {
      next.email = "Please enter your email.";
    } else if (!EMAIL_SHAPE.test(email)) {
      next.email = "Please enter a valid email address.";
    } else if (!GMAIL_REGEX.test(email)) {
      next.email = "Only Gmail addresses (@gmail.com) are allowed.";
    }
    if (!form.password) {
      next.password = "Please enter your password.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!validate()) return;
    setSubmitting(true);
    try {
      const credentials = {
        email: form.email,
        password: form.password,
        remember_me: form.rememberMe,
      };
      if (config.idKey) {
        credentials[config.idKey] = form.idValue.trim();
      }
      const user = await login(role, credentials);
      // Reached ONLY after the backend verified the credentials and returned a session.
      toast.success(`Welcome back, ${user.full_name.split(" ")[0]}!`);
      navigate(`/${user.role}/dashboard`, { replace: true });
    } catch (err) {
      // Stay on this page and say what happened — never navigate on failure.
      setFormError(loginErrorMessage(err));
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
        <Link to="/login" className="flex items-center gap-2 mb-6 justify-center">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-display font-bold">
            S
          </div>
          <span className="font-display font-bold text-lg">StudentHub</span>
        </Link>

        <div className="flex items-center justify-center gap-2 mb-1">
          <config.icon className="text-primary" />
          <h1 className="text-2xl font-display font-bold text-center">{config.title}</h1>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center mb-8">
          Log in to continue to your dashboard
        </p>

        {notice && !formError && (
          <div role="status" className="mb-4 flex items-start gap-2 rounded-xl border border-primary/20 bg-primary/5 px-3 py-2 text-sm text-slate-700 dark:text-slate-200">
            <FiInfo className="mt-0.5 shrink-0 text-primary" /> <span>{notice}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {config.idKey && (
            <div>
              <label className="text-sm font-medium mb-1 block">{config.idLabel}</label>
              <div className="relative">
                <FiHash className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  className="input-field pl-11"
                  placeholder={config.idPlaceholder}
                  value={form.idValue}
                  onChange={(e) => { setForm({ ...form, idValue: e.target.value }); setFormError(""); }}
                />
              </div>
              {errors.idValue && <p className="input-error">{errors.idValue}</p>}
            </div>
          )}

          <div>
            <label className="text-sm font-medium mb-1 block">Gmail address</label>
            <div className="relative">
              <FiMail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="email"
                className="input-field pl-11"
                placeholder="you@gmail.com"
                value={form.email}
                onChange={(e) => { setForm({ ...form, email: e.target.value }); setFormError(""); }}
              />
            </div>
            {errors.email && <p className="input-error">{errors.email}</p>}
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">Password</label>
            <div className="relative">
              <FiLock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type={showPassword ? "text" : "password"}
                className="input-field pl-11 pr-11"
                placeholder="••••••••"
                value={form.password}
                onChange={(e) => { setForm({ ...form, password: e.target.value }); setFormError(""); }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
                aria-label="Toggle password visibility"
              >
                {showPassword ? <FiEyeOff /> : <FiEye />}
              </button>
            </div>
            {errors.password && <p className="input-error">{errors.password}</p>}
          </div>

          <div className="flex items-center justify-between text-sm">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={form.rememberMe}
                onChange={(e) => setForm({ ...form, rememberMe: e.target.checked })}
                className="rounded border-slate-300 text-primary focus:ring-primary"
              />
              Remember me
            </label>
            <Link to="/forgot-password" className="text-primary font-medium hover:underline">
              Forgot password?
            </Link>
          </div>

          {formError && (
            <div role="alert" aria-live="assertive" className="flex items-start gap-2 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
              <FiAlertCircle className="mt-0.5 shrink-0" /> <span>{formError}</span>
            </div>
          )}

          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
            {submitting ? "Logging in..." : "Log in"}
          </button>
        </form>

        {role === "student" ? (
          <p className="text-center text-sm text-slate-500 dark:text-slate-400 mt-6">
            New student?{" "}
            <Link to="/signup" className="text-primary font-medium hover:underline">
              Create an account
            </Link>
          </p>
        ) : (
          <p className="text-center text-xs text-slate-400 mt-6">
            {role === "faculty" ? "Faculty" : "Admin"} accounts are provisioned by the institution — there's no sign-up here.
          </p>
        )}

        <p className="text-center text-xs text-slate-400 mt-3">
          <Link to="/login" className="hover:underline">
            ← Choose a different portal
          </Link>
        </p>
      </div>
    </div>
  );
}
