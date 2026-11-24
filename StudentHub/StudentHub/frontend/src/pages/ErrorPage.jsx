import { Link, useNavigate } from "react-router-dom";
import { FiAlertTriangle } from "react-icons/fi";

const CONTENT = {
  400: {
    title: "Invalid request",
    desc: "Something about that request doesn't look right. Double-check the details and try again.",
  },
  401: {
    title: "Please log in",
    desc: "You need to be logged in to view this page.",
  },
  403: {
    title: "Access denied",
    desc: "Your account doesn't have permission to view this page.",
  },
  404: {
    title: "Page not found",
    desc: "The page you're looking for doesn't exist or has moved.",
  },
  500: {
    title: "Something went wrong",
    desc: "An unexpected error occurred on our side. Please try again in a moment.",
  },
};

export default function ErrorPage({ code = 404 }) {
  const navigate = useNavigate();
  const { title, desc } = CONTENT[code] || CONTENT[404];

  return (
    <div className="min-h-screen flex items-center justify-center px-6 bg-gradient-to-br from-surface via-white to-secondary/10 dark:from-dark dark:via-dark dark:to-primary/10">
      <div className="glass-card w-full max-w-md p-10 text-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white text-2xl mx-auto mb-6">
          <FiAlertTriangle />
        </div>
        <p className="text-sm font-semibold text-primary mb-2">Error {code}</p>
        <h1 className="text-2xl font-display font-bold mb-2">{title}</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-8">{desc}</p>
        <div className="flex items-center justify-center gap-3">
          <button onClick={() => navigate(-1)} className="btn-secondary">
            Go back
          </button>
          <Link to="/" className="btn-primary">
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}
