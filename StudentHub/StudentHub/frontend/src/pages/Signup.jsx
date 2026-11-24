import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { FiUser, FiMail, FiLock, FiPhone, FiEye, FiEyeOff, FiHash, FiBookOpen, FiLayers } from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import PasswordStrengthMeter from "../components/PasswordStrengthMeter";
import ThemeToggle from "../components/ThemeToggle";

const NAME_REGEX = /^[A-Za-z ]{3,30}$/;
const GMAIL_REGEX = /^[a-zA-Z0-9](\.?[a-zA-Z0-9_-]){0,63}@gmail\.com$/;
const PHONE_REGEX = /^[0-9]{10}$/;
const ID_REGEX = /^[0-9]+$/;

const DEPARTMENTS = [
  "Computer Science", "Information Technology", "Electronics & Communication",
  "Electrical Engineering", "Mechanical Engineering", "Civil Engineering",
  "Commerce", "Science", "Law", "Other",
];

function validatePassword(password) {
  if (password.length < 8) return "Password must be at least 8 characters long.";
  if (!/[A-Z]/.test(password)) return "Password must include at least one uppercase letter.";
  if (!/[a-z]/.test(password)) return "Password must include at least one lowercase letter.";
  if (!/[0-9]/.test(password)) return "Password must include at least one number.";
  if (!/[!@#$%^&*(),.?":{}|<>_\-+=[\]/\\;']/.test(password))
    return "Password must include at least one special character.";
  return null;
}

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    student_id: "",
    department: DEPARTMENTS[0],
    semester: "1",
    password: "",
    confirm_password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const validate = () => {
    const next = {};
    if (!NAME_REGEX.test(form.full_name.trim())) {
      next.full_name = "Name must be 3–30 letters only (no numbers or special characters).";
    }
    if (!GMAIL_REGEX.test(form.email.trim().toLowerCase())) {
      next.email = "Only Gmail addresses (@gmail.com) are allowed.";
    }
    if (!PHONE_REGEX.test(form.phone.trim())) {
      next.phone = "Phone number must be exactly 10 digits.";
    }
    if (!ID_REGEX.test(form.student_id.trim())) {
      next.student_id = "Student ID must contain numbers only.";
    }
    if (!form.department) {
      next.department = "Please select a department.";
    }
    const sem = Number(form.semester);
    if (!sem || sem < 1 || sem > 8) {
      next.semester = "Semester must be between 1 and 8.";
    }
    const passwordError = validatePassword(form.password);
    if (passwordError) next.password = passwordError;
    if (form.confirm_password !== form.password) {
      next.confirm_password = "Passwords do not match.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      await signup({ ...form, semester: Number(form.semester) });
      toast.success("Account created! Check your Gmail inbox to verify your email.");
      navigate("/login/student");
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        toast.error(detail[0]?.msg || "Please check your details and try again.");
      } else {
        toast.error(detail || "Signup failed. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const field = (name, label, icon, type = "text", placeholder = "") => (
    <div>
      <label className="text-sm font-medium mb-1 block">{label}</label>
      <div className="relative">
        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">{icon}</span>
        <input
          type={type}
          className="input-field pl-11"
          placeholder={placeholder}
          value={form[name]}
          onChange={(e) => setForm({ ...form, [name]: e.target.value })}
        />
      </div>
      {errors[name] && <p className="input-error">{errors[name]}</p>}
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-16 bg-gradient-to-br from-surface via-white to-secondary/10 dark:from-dark dark:via-dark dark:to-primary/10">
      <div className="absolute top-6 right-6">
        <ThemeToggle />
      </div>

      <div className="glass-card w-full max-w-md p-8">
        <Link to="/" className="flex items-center gap-2 mb-6 justify-center">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-display font-bold">
            S
          </div>
          <span className="font-display font-bold text-lg">StudentHub</span>
        </Link>

        <h1 className="text-2xl font-display font-bold text-center mb-1">Create your student account</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center mb-8">
          Only students can sign up — a Gmail address is required
        </p>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {field("full_name", "Full name", <FiUser />, "text", "Priya Sharma")}
          {field("email", "Gmail address", <FiMail />, "email", "you@gmail.com")}
          {field("phone", "Phone number", <FiPhone />, "tel", "9876543210")}
          {field("student_id", "Student ID", <FiHash />, "text", "2024001")}

          <div>
            <label className="text-sm font-medium mb-1 block">Department</label>
            <div className="relative">
              <FiBookOpen className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 z-10" />
              <select
                className="input-field pl-11 appearance-none"
                value={form.department}
                onChange={(e) => setForm({ ...form, department: e.target.value })}
              >
                {DEPARTMENTS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
            {errors.department && <p className="input-error">{errors.department}</p>}
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">Semester</label>
            <div className="relative">
              <FiLayers className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 z-10" />
              <select
                className="input-field pl-11 appearance-none"
                value={form.semester}
                onChange={(e) => setForm({ ...form, semester: e.target.value })}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                  <option key={s} value={s}>Semester {s}</option>
                ))}
              </select>
            </div>
            {errors.semester && <p className="input-error">{errors.semester}</p>}
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
                onChange={(e) => setForm({ ...form, password: e.target.value })}
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
            <PasswordStrengthMeter password={form.password} />
            {errors.password && <p className="input-error">{errors.password}</p>}
          </div>

          {field("confirm_password", "Confirm password", <FiLock />, "password", "••••••••")}

          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
            {submitting ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500 dark:text-slate-400 mt-6">
          Already have an account?{" "}
          <Link to="/login/student" className="text-primary font-medium hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
