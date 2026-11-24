import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { FiMenu, FiX } from "react-icons/fi";
import ThemeToggle from "./ThemeToggle";

const LINKS = [
  { label: "Home", href: "#home" },
  { label: "Features", href: "#features" },
  { label: "About", href: "#about" },
  { label: "Contact", href: "#contact" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <header className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[95%] max-w-6xl">
      <nav className="glass-card flex items-center justify-between px-5 py-3">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-display font-bold">
            S
          </div>
          <span className="font-display font-bold text-lg">StudentHub</span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-primary transition-colors"
            >
              {link.label}
            </a>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          <ThemeToggle />
          <button onClick={() => navigate("/login")} className="btn-secondary !px-5 !py-2 text-sm">
            Log in
          </button>
        </div>

        <button className="md:hidden text-2xl" onClick={() => setOpen(!open)} aria-label="Toggle menu">
          {open ? <FiX /> : <FiMenu />}
        </button>
      </nav>

      {open && (
        <div className="glass-card mt-2 md:hidden flex flex-col gap-4 px-5 py-4">
          {LINKS.map((link) => (
            <a key={link.label} href={link.href} onClick={() => setOpen(false)} className="text-sm font-medium">
              {link.label}
            </a>
          ))}
          <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-white/10">
            <ThemeToggle />
            <button onClick={() => navigate("/login")} className="btn-primary !px-5 !py-2 text-sm">
              Log in
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
