import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { FiCamera, FiTrash2, FiMail, FiPhone, FiEye, FiEyeOff, FiSave, FiLock } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import Avatar from "../../components/Avatar";
import PasswordStrengthMeter from "../../components/PasswordStrengthMeter";
import { useAuth } from "../../context/AuthContext";
import api from "../../services/api";

const NAME_REGEX = /^[A-Za-z ]{3,30}$/;
const PHONE_REGEX = /^[0-9]{10}$/;
const MAX_PHOTO_BYTES = 2 * 1024 * 1024;

function validatePassword(p) {
  if (p.length < 8) return "Password must be at least 8 characters long.";
  if (!/[A-Z]/.test(p)) return "Include at least one uppercase letter.";
  if (!/[a-z]/.test(p)) return "Include at least one lowercase letter.";
  if (!/[0-9]/.test(p)) return "Include at least one number.";
  if (!/[!@#$%^&*(),.?":{}|<>_\-+=[\]/\\;']/.test(p)) return "Include at least one special character.";
  return null;
}

const ROLE_LABEL = { admin: "Administrator", faculty: "Faculty", student: "Student" };

function PasswordInput({ value, onChange, placeholder, error, showMeter }) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <div className="relative">
        <input type={show ? "text" : "password"} className="input-field pr-11" value={value} onChange={onChange} placeholder={placeholder} />
        <button type="button" onClick={() => setShow(!show)} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400" aria-label="Toggle password visibility">
          {show ? <FiEyeOff /> : <FiEye />}
        </button>
      </div>
      {showMeter && <PasswordStrengthMeter password={value} />}
      {error && <p className="input-error">{error}</p>}
    </div>
  );
}

export default function Profile() {
  const { user, setUser } = useAuth();
  const fileRef = useRef(null);
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({ full_name: "", phone: "", designation: "", batch: "" });
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [pw, setPw] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [pwErrors, setPwErrors] = useState({});
  const [pwSaving, setPwSaving] = useState(false);

  const applyProfile = (data) => {
    setProfile(data);
    setForm({ full_name: data.full_name || "", phone: data.phone || "", designation: data.details?.designation || "", batch: data.details?.batch || "" });
    const { details, ...userOnly } = data;
    setUser(userOnly);
    localStorage.setItem("studenthub_user", JSON.stringify(userOnly));
  };

  useEffect(() => {
    api.get("/profile").then(({ data }) => applyProfile(data)).catch(() => toast.error("Failed to load your profile."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handlePhoto = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast.error("Please choose a JPG, PNG, or WEBP image.");
      return;
    }
    if (file.size > MAX_PHOTO_BYTES) {
      toast.error("Image is too large — the maximum is 2 MB.");
      return;
    }
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/profile/photo", fd, { headers: { "Content-Type": "multipart/form-data" } });
      applyProfile(data);
      toast.success("Profile photo updated.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Photo upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const removePhoto = async () => {
    try {
      const { data } = await api.delete("/profile/photo");
      applyProfile(data);
      toast.success("Profile photo removed.");
    } catch {
      toast.error("Couldn't remove the photo.");
    }
  };

  const saveProfile = async (e) => {
    e.preventDefault();
    const next = {};
    if (!NAME_REGEX.test(form.full_name.trim())) next.full_name = "Name must be 3–30 letters only (no numbers or special characters).";
    if (form.phone.trim() && !PHONE_REGEX.test(form.phone.trim())) next.phone = "Phone number must be exactly 10 digits.";
    setErrors(next);
    if (Object.keys(next).length) return;

    setSaving(true);
    try {
      const body = { full_name: form.full_name, phone: form.phone.trim() };
      if (user.role === "faculty") body.designation = form.designation;
      if (user.role === "student") body.batch = form.batch;
      const { data } = await api.put("/profile", body);
      applyProfile(data);
      toast.success("Profile updated.");
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(Array.isArray(detail) ? detail[0]?.msg : detail || "Couldn't save your profile.");
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async (e) => {
    e.preventDefault();
    const next = {};
    if (!pw.current_password) next.current_password = "Enter your current password.";
    const err = validatePassword(pw.new_password);
    if (err) next.new_password = err;
    else if (pw.new_password === pw.current_password) next.new_password = "New password must be different from the current one.";
    if (pw.confirm_password !== pw.new_password) next.confirm_password = "Passwords do not match.";
    setPwErrors(next);
    if (Object.keys(next).length) return;

    setPwSaving(true);
    try {
      await api.post("/profile/change-password", pw);
      toast.success("Password changed successfully.");
      setPw({ current_password: "", new_password: "", confirm_password: "" });
    } catch (e2) {
      const detail = e2.response?.data?.detail;
      toast.error(Array.isArray(detail) ? detail[0]?.msg : detail || "Couldn't change your password.");
    } finally {
      setPwSaving(false);
    }
  };

  const d = profile?.details || {};
  const readOnly = [
    user.role === "student" && ["Student ID", d.student_id],
    user.role === "faculty" && ["Faculty ID", d.faculty_id],
    user.role === "admin" && ["Admin ID", d.admin_id],
    d.department && ["Department", d.department],
    user.role === "student" && d.semester && ["Semester", d.semester],
  ].filter(Boolean);

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">My Profile</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Manage your photo, personal details, and password.</p>

        <div className="grid lg:grid-cols-3 gap-4">
          {/* Identity card */}
          <div className="glass-card p-6 text-center h-fit">
            <div className="relative inline-block">
              <Avatar user={user} size={112} />
              <button
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                aria-label="Upload profile photo"
                className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center shadow-lg hover:scale-110 transition disabled:opacity-60"
              >
                <FiCamera size={16} />
              </button>
              <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handlePhoto} />
            </div>
            <p className="font-display font-bold text-lg mt-4">{user.full_name}</p>
            <span className="inline-block mt-1 text-xs px-2.5 py-1 rounded-full bg-primary/10 text-primary font-medium">{ROLE_LABEL[user.role]}</span>
            <p className="text-xs text-slate-400 mt-3">{uploading ? "Uploading..." : "JPG, PNG or WEBP · max 2 MB"}</p>
            {user.avatar_url && (
              <button onClick={removePhoto} className="mt-3 text-xs text-danger hover:underline inline-flex items-center gap-1"><FiTrash2 size={12} /> Remove photo</button>
            )}

            <div className="mt-6 pt-5 border-t border-slate-200 dark:border-white/10 space-y-3 text-left text-sm">
              <p className="flex items-center gap-2 text-slate-500 dark:text-slate-400 break-all"><FiMail className="flex-shrink-0" /> {user.email}</p>
              {profile?.phone && <p className="flex items-center gap-2 text-slate-500 dark:text-slate-400"><FiPhone className="flex-shrink-0" /> {profile.phone}</p>}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-4">
            {/* Edit profile */}
            <form onSubmit={saveProfile} noValidate className="glass-card p-6 space-y-4">
              <h2 className="font-display font-semibold">Edit profile</h2>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium mb-1 block">Full name</label>
                  <input className="input-field" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
                  {errors.full_name && <p className="input-error">{errors.full_name}</p>}
                </div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Phone</label>
                  <input className="input-field" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="10-digit number" />
                  {errors.phone && <p className="input-error">{errors.phone}</p>}
                </div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Gmail (cannot be changed)</label>
                  <input className="input-field opacity-60" value={user.email} disabled />
                </div>
                {readOnly.map(([label, value]) => (
                  <div key={label}>
                    <label className="text-sm font-medium mb-1 block">{label}</label>
                    <input className="input-field opacity-60" value={value ?? ""} readOnly disabled />
                  </div>
                ))}
                {user.role === "faculty" && (
                  <div>
                    <label className="text-sm font-medium mb-1 block">Designation</label>
                    <input className="input-field" value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} placeholder="Assistant Professor" />
                  </div>
                )}
                {user.role === "student" && (
                  <div>
                    <label className="text-sm font-medium mb-1 block">Batch</label>
                    <input className="input-field" value={form.batch} onChange={(e) => setForm({ ...form, batch: e.target.value })} placeholder="2024-2028" />
                  </div>
                )}
              </div>
              <button type="submit" disabled={saving} className="btn-primary !py-2.5 inline-flex items-center gap-2 disabled:opacity-60">
                <FiSave /> {saving ? "Saving..." : "Save changes"}
              </button>
            </form>

            {/* Change password */}
            <form onSubmit={changePassword} noValidate className="glass-card p-6 space-y-4">
              <h2 className="font-display font-semibold flex items-center gap-2"><FiLock /> Change password</h2>
              <div>
                <label className="text-sm font-medium mb-1 block">Current password</label>
                <PasswordInput value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} error={pwErrors.current_password} />
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium mb-1 block">New password</label>
                  <PasswordInput value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} error={pwErrors.new_password} showMeter />
                </div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Confirm new password</label>
                  <PasswordInput value={pw.confirm_password} onChange={(e) => setPw({ ...pw, confirm_password: e.target.value })} error={pwErrors.confirm_password} />
                </div>
              </div>
              <button type="submit" disabled={pwSaving} className="btn-primary !py-2.5 disabled:opacity-60">
                {pwSaving ? "Updating..." : "Update password"}
              </button>
            </form>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
