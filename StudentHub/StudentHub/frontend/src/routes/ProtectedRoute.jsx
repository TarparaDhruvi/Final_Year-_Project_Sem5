import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * Wrap any dashboard route with this. `allowedRoles` restricts a page to
 * specific roles (e.g. ["admin"]); omit it to just require any logged-in user.
 * Because logout does a full window.location.replace (see api.js), the
 * browser history entry for a dashboard is replaced rather than left behind,
 * so the back button can't reveal it post-logout.
 */
export default function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface dark:bg-dark">
        <div className="w-10 h-10 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/403" replace />;
  }

  return children;
}
