import axios from "axios";

// All requests go through the /api prefix, which vite.config.js proxies
// to the FastAPI backend in dev. In production, point this at your
// deployed API origin via an env var instead.
const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("studenthub_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On a 401, try exactly one silent refresh using the stored refresh token.
// If that also fails, force a full logout so the app never sits in a
// half-authenticated state.
let isRefreshing = false;
let queue = [];

function processQueue(error, token = null) {
  queue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  queue = [];
}

// Public auth endpoints answer 401 for "wrong password" / "bad token". That is an ANSWER for the page that asked,
// not an expired session — treating it as one used to wipe the form and bounce the user to portal selection.
const PUBLIC_AUTH_PATHS = ["/auth/login/", "/auth/forgot-password", "/auth/reset-password", "/auth/signup", "/auth/verify-email", "/auth/refresh"];
const isPublicAuthRequest = (config) => PUBLIC_AUTH_PATHS.some((p) => (config?.url || "").includes(p));

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (isPublicAuthRequest(originalRequest)) {
      return Promise.reject(error);
    }
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem("studenthub_refresh_token");
      if (!refreshToken) {
        forceLogout("expired");
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          queue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post("/api/auth/refresh", {
          refresh_token: refreshToken,
        });
        localStorage.setItem("studenthub_access_token", data.access_token);
        localStorage.setItem("studenthub_refresh_token", data.refresh_token);
        processQueue(null, data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        forceLogout("expired");
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    // Admin deactivated this account while it was signed in: end the session cleanly.
    if (error.response?.status === 403 && /disabled/i.test(String(error.response?.data?.detail || ""))) {
      forceLogout("disabled");
    }
    return Promise.reject(error);
  }
);

let loggingOut = false;

/**
 * Clears the session and returns the user to THEIR portal's login page (not the portal chooser), with a short
 * notice. `reason` is "expired" | "disabled" | undefined (a normal, user-initiated logout).
 */
function forceLogout(reason) {
  let role = null;
  try { role = JSON.parse(localStorage.getItem("studenthub_user") || "null")?.role || null; } catch { /* corrupt entry: ignore */ }
  localStorage.removeItem("studenthub_access_token");
  localStorage.removeItem("studenthub_refresh_token");
  localStorage.removeItem("studenthub_user");

  const onLoginPage = window.location.pathname.startsWith("/login");
  if (loggingOut || (reason && onLoginPage)) return;   // already heading to login: don't reload in a loop
  loggingOut = true;
  const target = role ? `/login/${role}` : "/login";
  // Full reload clears all in-memory state and replaces history so the back button can't reveal a dashboard.
  window.location.replace(reason ? `${target}?${reason}=1` : target);
}

export default api;
export { forceLogout };
