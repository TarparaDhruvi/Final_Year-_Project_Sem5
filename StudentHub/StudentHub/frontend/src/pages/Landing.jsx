import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  FiCpu,
  FiBell,
  FiBarChart2,
  FiUsers,
  FiShield,
  FiMessageSquare,
} from "react-icons/fi";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

const FEATURES = [
  {
    icon: FiCpu,
    title: "AI Study Coach",
    desc: "Upload any notes and get smart summaries, flashcards, MCQs, and a personalized planner until exam day.",
  },
  {
    icon: FiBell,
    title: "Smart Deadline Reminders",
    desc: "Never miss a deadline — countdown timers, missed-activity recovery, and catch-up popups after time away.",
  },
  {
    icon: FiBarChart2,
    title: "Campus Pulse Analytics",
    desc: "Live attendance trends, engagement heatmaps, and performance insights for every department.",
  },
  {
    icon: FiUsers,
    title: "Three Dedicated Portals",
    desc: "Purpose-built dashboards for Admins, Faculty, and Students — each seeing only what matters to them.",
  },
  {
    icon: FiMessageSquare,
    title: "Anonymous Doubt Wall",
    desc: "Students ask questions freely; faculty answer publicly; the best answers rise to the top.",
  },
  {
    icon: FiShield,
    title: "Secure by Design",
    desc: "JWT auth, bcrypt hashing, role-based access, and Gmail-verified accounts protect every login.",
  },
];

const STATS = [
  { value: "3", label: "Dedicated Portals" },
  { value: "20+", label: "Integrated Modules" },
  { value: "24/7", label: "AI Assistant Access" },
  { value: "100%", label: "Real-Time Notifications" },
];

const TESTIMONIALS = [
  {
    quote: "The AI Study Coach turned my messy scanned notes into a real revision plan before my DBMS final.",
    name: "Priya, B.Tech CSE",
  },
  {
    quote: "Clash detection on the timetable alone saved our department hours every semester.",
    name: "Rahul, Faculty Coordinator",
  },
  {
    quote: "Campus Pulse gives us a live read on engagement we never had before.",
    name: "Admin Office",
  },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen overflow-x-hidden">
      <Navbar />

      {/* Hero */}
      <section
        id="home"
        className="relative pt-40 pb-32 px-6 bg-gradient-to-br from-surface via-white to-secondary/10
                   dark:from-dark dark:via-dark dark:to-primary/10"
      >
        <div
          className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-gradient-to-br from-primary/30 to-secondary/30
                     blur-3xl animate-float pointer-events-none"
        />
        <div
          className="absolute top-40 -left-24 w-72 h-72 rounded-full bg-gradient-to-br from-secondary/20 to-primary/20
                     blur-3xl animate-float pointer-events-none"
          style={{ animationDelay: "2s" }}
        />

        <div className="relative max-w-4xl mx-auto text-center">
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-block px-4 py-1.5 rounded-full glass-card text-sm font-medium text-primary mb-6"
          >
            AI-Powered College Management
          </motion.span>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-4xl md:text-6xl font-display font-extrabold leading-tight mb-6"
          >
            One Platform Connecting
            <br />
            <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Students, Faculty & Administration
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto mb-10"
          >
            StudentHub brings attendance, assignments, timetables, and a ChatGPT-style AI assistant
            into one calm, modern workspace — built for real campuses.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <button onClick={() => navigate("/signup")} className="btn-primary">
              Get Started as Student
            </button>
            <button onClick={() => navigate("/login")} className="btn-secondary">
              Log in to your portal
            </button>
          </motion.div>
        </div>
      </section>

      {/* Stats */}
      <section className="px-6 -mt-16 relative z-10">
        <div className="max-w-5xl mx-auto glass-card grid grid-cols-2 md:grid-cols-4 gap-6 p-8">
          {STATS.map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="text-3xl font-display font-bold text-primary">{stat.value}</p>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 py-28 max-w-6xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-display font-bold mb-4">
            Everything a campus needs, in one place
          </h2>
          <p className="text-slate-500 dark:text-slate-400">
            Purpose-built modules for the three people who run a college day to day.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div key={f.title} className="glass-card p-7 hover:-translate-y-1 transition-transform duration-300">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white text-xl mb-4">
                <f.icon />
              </div>
              <h3 className="font-display font-semibold text-lg mb-2">{f.title}</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* About */}
      <section id="about" className="px-6 py-20 bg-white/50 dark:bg-white/5">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-display font-bold mb-6">Built like a real SaaS product</h2>
          <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
            StudentHub replaces scattered spreadsheets, WhatsApp groups, and paper notices with a single
            secure system — three role-based portals, real-time notifications, and an AI assistant that
            actually understands each student's uploaded notes.
          </p>
        </div>
      </section>

      {/* Testimonials */}
      <section className="px-6 py-28 max-w-6xl mx-auto">
        <h2 className="text-3xl font-display font-bold text-center mb-14">What people are saying</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {TESTIMONIALS.map((t) => (
            <div key={t.name} className="glass-card p-7">
              <p className="text-slate-600 dark:text-slate-300 mb-5 italic">"{t.quote}"</p>
              <p className="font-semibold text-sm">{t.name}</p>
            </div>
          ))}
        </div>
      </section>

      <Footer />
    </div>
  );
}
