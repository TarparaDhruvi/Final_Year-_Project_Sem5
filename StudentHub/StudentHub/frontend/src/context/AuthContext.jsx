import { createContext, useContext, useEffect, useState } from "react";
import api, { forceLogout } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("studenthub_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(true);
  const [missedActivity, setMissedActivity] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("studenthub_access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get("/auth/me")
      .then(({ data }) => {
        setUser(data);
        localStorage.setItem("studenthub_user", JSON.stringify(data));
      })
      .catch(() => {
        // interceptor already handles forced logout on a real 401
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (role, credentials) => {
    const { data } = await api.post(`/auth/login/${role}`, credentials);
    localStorage.setItem("studenthub_access_token", data.access_token);
    localStorage.setItem("studenthub_refresh_token", data.refresh_token);
    localStorage.setItem("studenthub_user", JSON.stringify(data.user));
    setUser(data.user);
    if (data.missed_activity) {
      setMissedActivity(data.missed_activity);
    }
    return data.user;
  };

  const signup = async (payload) => {
    const { data } = await api.post("/auth/signup", payload);
    return data;
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem("studenthub_refresh_token");
    try {
      if (refreshToken) {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      }
    } catch {
      // Even if the server call fails, still clear local session.
    }
    forceLogout();
  };

  return (
    <AuthContext.Provider value={{ user, setUser, login, signup, logout, loading, missedActivity, clearMissedActivity: () => setMissedActivity(null) }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
