import { NavLink, Link, useLocation } from "react-router-dom";
import { useState } from "react";
import {
  FiLogOut, FiGrid, FiUsers, FiUserCheck, FiBook, FiCalendar, FiClipboard, FiVolume2,
  FiFileText, FiEdit3, FiCheckSquare, FiMenu, FiX, FiBell, FiCpu, FiClock, FiUser,
  FiBarChart2, FiZap, FiTarget,
  FiMessageSquare, FiTrendingDown, FiAlertTriangle, FiActivity, } from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import ThemeToggle from "../components/ThemeToggle";
import NotificationBell from "../components/NotificationBell";
import GlobalSearch from "../components/GlobalSearch";
import Avatar from "../components/Avatar";

const ROLE_LABEL = { admin: "Administrator", faculty: "Faculty", student: "Student" };

const NAV = {
  admin: [
    { to: "/admin/dashboard", label: "Dashboard", icon: FiGrid, end: true },
    { to: "/admin/students", label: "Students", icon: FiUsers },
    { to: "/admin/faculty", label: "Faculty", icon: FiUserCheck },
    { to: "/admin/subjects", label: "Subjects", icon: FiBook },
    { to: "/admin/timetable", label: "Timetable", icon: FiCalendar },
    { to: "/admin/leave", label: "Leave Requests", icon: FiClipboard },
    { to: "/admin/announcements", label: "Announcements", icon: FiVolume2 },
    { to: "/notifications", label: "Notifications", icon: FiBell },
    { to: "/admin/reports", label: "Reports", icon: FiBarChart2 },
    { to: "/admin/faculty-heatmap", label: "Faculty Heatmap", icon: FiTrendingDown },
    { to: "/admin/silent-students", label: "Silent Students", icon: FiAlertTriangle },
    { to: "/admin/campus-pulse", label: "Campus Pulse", icon: FiActivity },
    { to: "/admin/calendar", label: "Calendar", icon: FiCalendar },
    { to: "/profile", label: "My Profile", icon: FiUser },
  ],
  faculty: [
    { to: "/faculty/dashboard", label: "Dashboard", icon: FiGrid, end: true },
    { to: "/faculty/schedule", label: "My Schedule", icon: FiClock },
    { to: "/faculty/students", label: "My Students", icon: FiUsers },
    { to: "/faculty/attendance", label: "Attendance", icon: FiCheckSquare },
    { to: "/faculty/assignments", label: "Assignments", icon: FiFileText },
    { to: "/faculty/notes", label: "Study Material", icon: FiBook },
    { to: "/faculty/marks", label: "Marks", icon: FiEdit3 },
    { to: "/faculty/leave", label: "My Leave", icon: FiClipboard },
    { to: "/faculty/announcements", label: "Announcements", icon: FiVolume2 },
    { to: "/notifications", label: "Notifications", icon: FiBell },
    { to: "/faculty/reports", label: "Reports", icon: FiBarChart2 },
    { to: "/faculty/doubt-wall", label: "Doubt Wall", icon: FiMessageSquare },
    { to: "/faculty/calendar", label: "Calendar", icon: FiCalendar },
    { to: "/profile", label: "My Profile", icon: FiUser },
  ],
  student: [
    { to: "/student/dashboard", label: "Dashboard", icon: FiGrid, end: true },
    { to: "/student/schedule", label: "My Schedule", icon: FiClock },
    { to: "/student/attendance", label: "Attendance", icon: FiCheckSquare },
    { to: "/student/assignments", label: "Assignments", icon: FiFileText },
    { to: "/student/notes", label: "Notes", icon: FiBook },
    { to: "/student/marks", label: "Marks", icon: FiEdit3 },
    { to: "/student/leave", label: "Leave", icon: FiClipboard },
    { to: "/student/announcements", label: "Announcements", icon: FiVolume2 },
    { to: "/notifications", label: "Notifications", icon: FiBell },
    { to: "/student/ai", label: "StudentHub AI", icon: FiCpu },
    { to: "/student/study-coach", label: "AI Study Coach", icon: FiTarget },
    { to: "/student/skill-wallet", label: "Skill Wallet", icon: FiZap },
    { to: "/student/reports", label: "Reports", icon: FiBarChart2 },
    { to: "/student/doubt-wall", label: "Doubt Wall", icon: FiMessageSquare },
    { to: "/student/calendar", label: "Calendar", icon: FiCalendar },
    { to: "/profile", label: "My Profile", icon: FiUser },
  ],
};

function SidebarContent({ user, logout, onNavigate }) {
  const items = NAV[user?.role] || [];
  return (
    <>
      <div className="flex items-center gap-2.5 mb-6">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-display font-bold shadow-lg shadow-primary/30">
          S
        </div>
        <p className="font-display font-bold text-lg leading-tight">StudentHub</p>
      </div>

      <Link
        to="/profile"
        onClick={onNavigate}
        className="flex items-center gap-3 p-3 mb-5 rounded-2xl bg-primary/5 dark:bg-white/5 border border-primary/10 hover:bg-primary/10 transition-colors"
      >
        <Avatar user={user} size={40} />
        <div className="min-w-0">
          <p className="text-sm font-semibold truncate">{user?.full_name}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">{ROLE_LABEL[user?.role]}</p>
        </div>
      </Link>

      <nav className="flex-1 space-y-1 overflow-y-auto pr-1 -mr-1">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-gradient-to-r from-primary to-secondary text-white shadow-lg shadow-primary/30"
                  : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 hover:translate-x-0.5"
              }`
            }
          >
            <item.icon className="text-base transition-transform group-hover:scale-110" /> {item.label}
          </NavLink>
        ))}
      </nav>

      <button
        onClick={logout}
        className="mt-3 flex items-center gap-3 px-3 py-2.5 rounded-xl text-danger hover:bg-danger/10 text-sm font-medium transition-colors"
      >
        <FiLogOut /> Log out
      </button>
    </>
  );
}

export default function DashboardLayout({ children }) {
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const onAIPage = location.pathname.endsWith("/ai");

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="min-h-screen bg-gradient-to-br from-surface via-white to-secondary/5 dark:from-dark dark:via-dark dark:to-primary/5 flex">
      {/* Desktop floating sidebar */}
      <aside className="hidden md:flex flex-col w-64 m-4 p-5 glass-card sticky top-4 h-[calc(100vh-2rem)] flex-shrink-0">
        <SidebarContent user={user} logout={logout} />
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-[90] md:hidden">
          <div className="absolute inset-0 bg-dark/50 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-72 p-5 bg-white dark:bg-dark flex flex-col shadow-2xl">
            <button
              onClick={() => setMobileOpen(false)}
              className="self-end mb-2 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 dark:hover:bg-white/10"
              aria-label="Close menu"
            >
              <FiX />
            </button>
            <SidebarContent user={user} logout={logout} onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center justify-between p-4 md:pl-0">
          <div className="glass-card flex-1 flex items-center justify-between px-5 py-3">
            <div className="flex items-center gap-3 min-w-0">
              <button
                onClick={() => setMobileOpen(true)}
                className="md:hidden w-9 h-9 flex items-center justify-center rounded-lg hover:bg-slate-100 dark:hover:bg-white/10"
                aria-label="Open menu"
              >
                <FiMenu />
              </button>
              <div className="min-w-0">
                <p className="text-xs text-slate-500 dark:text-slate-400">{greeting} 👋</p>
                <p className="font-display font-semibold truncate">{user?.full_name}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <GlobalSearch />
              <NotificationBell />
              <ThemeToggle />
              <Link to="/profile" aria-label="My profile" className="rounded-full ring-2 ring-transparent hover:ring-primary/40 transition">
                <Avatar user={user} size={40} />
              </Link>
            </div>
          </div>
        </header>

        <main className="flex-1 px-4 pb-24 md:pr-4">{children}</main>
      </div>

      {/* Floating AI button — students only (StudentHub AI is not available to Admin or Faculty) */}
      {!onAIPage && user?.role === "student" && (
        <Link
          to="/student/ai"
          aria-label="Open StudentHub AI"
          title="StudentHub AI"
          className="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-gradient-to-br from-primary to-secondary text-white flex items-center justify-center shadow-xl shadow-primary/40 hover:scale-110 active:scale-95 transition-transform"
        >
          <FiCpu size={22} />
        </Link>
      )}
    </div>
  );
}
