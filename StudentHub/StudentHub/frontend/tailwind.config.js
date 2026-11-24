/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#6D4AFF",     // electric violet
        secondary: "#B51DC9",   // fuchsia
        accent: "#22D3EE",      // cyan — highlights/glows only, never under white text
        dark: "#0B0919",        // deep ink-violet
        surface: "#F6F4FF",     // soft lavender
        "primary-light": "#9F8BFF",    // readable violet on dark backgrounds
        "secondary-light": "#E26BF5",  // readable fuchsia on dark backgrounds
        success: "#22C55E",
        danger: "#EF4444",
        warning: "#F59E0B",
      },
      fontFamily: {
        display: ["'Sora'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(76, 29, 149, 0.10), inset 0 1px 0 0 rgba(255, 255, 255, 0.6)",
        "glass-dark": "0 8px 32px 0 rgba(0, 0, 0, 0.45), inset 0 1px 0 0 rgba(255, 255, 255, 0.06)",
        glow: "0 10px 28px -8px rgba(109, 74, 255, 0.6)",
        "glow-lg": "0 14px 36px -8px rgba(181, 29, 201, 0.55)",
      },
      backdropBlur: {
        xs: "2px",
      },
      borderRadius: {
        "2xl": "1.25rem",
        "3xl": "1.75rem",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-12px)" },
        },
        gradientShift: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        gradientShift: "gradientShift 8s ease infinite",
      },
    },
  },
  plugins: [],
};
