import { FiSun, FiMoon } from "react-icons/fi";
import { useTheme } from "../context/ThemeContext";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      aria-label="Toggle dark mode"
      className="w-10 h-10 flex items-center justify-center rounded-xl glass-card hover:scale-105
                 active:scale-95 transition-transform duration-150"
    >
      {theme === "dark" ? <FiSun className="text-secondary" /> : <FiMoon className="text-primary" />}
    </button>
  );
}
