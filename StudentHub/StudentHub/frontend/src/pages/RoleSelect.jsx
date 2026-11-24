import { Link } from "react-router-dom";
import { FiShield, FiBookOpen, FiUser, FiArrowRight } from "react-icons/fi";
import ThemeToggle from "../components/ThemeToggle";

const PORTALS = [
  {
    role: "admin",
    title: "Admin Portal",
    desc: "Manage students, faculty, subjects, timetable, and campus-wide reports.",
    icon: FiShield,
    path: "/login/admin",
  },
  {
    role: "faculty",
    title: "Faculty Portal",
    desc: "Mark attendance, manage assignments, upload notes, and publish marks.",
    icon: FiBookOpen,
    path: "/login/faculty",
  },
  {
    role: "student",
    title: "Student Portal",
    desc: "Track attendance, submit assignments, download notes, and view results.",
    icon: FiUser,
    path: "/login/student",
  },
];

export default function RoleSelect() {
  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-16 bg-gradient-to-br from-surface via-white to-secondary/10 dark:from-dark dark:via-dark dark:to-primary/10">
      <div className="absolute top-6 right-6">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-4xl">
        <Link to="/" className="flex items-center gap-2 mb-10 justify-center">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-display font-bold">
            S
          </div>
          <span className="font-display font-bold text-lg">StudentHub</span>
        </Link>

        <h1 className="text-3xl font-display font-bold text-center mb-2">Who's logging in?</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center mb-12">
          Choose your portal to continue
        </p>

        <div className="grid sm:grid-cols-3 gap-6">
          {PORTALS.map((p) => (
            <Link
              key={p.role}
              to={p.path}
              className="glass-card p-7 flex flex-col hover:-translate-y-1.5 hover:shadow-xl transition-all duration-300 group"
            >
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white text-xl mb-5">
                <p.icon />
              </div>
              <h2 className="font-display font-semibold text-lg mb-2">{p.title}</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 flex-1">{p.desc}</p>
              <div className="flex items-center gap-1.5 text-primary text-sm font-medium mt-5 group-hover:gap-2.5 transition-all">
                Continue <FiArrowRight />
              </div>
            </Link>
          ))}
        </div>

        <p className="text-center text-xs text-slate-400 mt-10">
          Only students can create a new account.{" "}
          <Link to="/signup" className="text-primary hover:underline">
            Sign up here
          </Link>
          . Faculty and Admin accounts are provisioned by the institution.
        </p>
      </div>
    </div>
  );
}
