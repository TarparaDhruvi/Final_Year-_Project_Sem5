import { createContext, useContext, useEffect, useRef, useState, useCallback } from "react";
import api from "../services/api";
import { useAuth } from "./AuthContext";

const NotificationContext = createContext(null);

export function NotificationProvider({ children }) {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const wsRef = useRef(null);

  const refresh = useCallback(async () => {
    if (!user) return;
    try {
      const [{ data: list }, { data: countData }] = await Promise.all([
        api.get("/notifications"),
        api.get("/notifications/unread-count"),
      ]);
      setNotifications(list);
      setUnreadCount(countData.count);
    } catch {
      // Non-fatal — the bell just stays empty until next refresh.
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Live push over WebSocket so the bell updates without polling.
  useEffect(() => {
    if (!user) return;
    const token = localStorage.getItem("studenthub_access_token");
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/${token}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.event === "notification") {
          setNotifications((prev) => [payload.notification, ...prev].slice(0, 50));
          setUnreadCount((prev) => prev + 1);
        }
      } catch {
        // ignore malformed frames
      }
    };

    return () => ws.close();
  }, [user]);

  const markRead = async (id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    setUnreadCount((prev) => Math.max(0, prev - 1));
    try {
      await api.put(`/notifications/${id}/read`);
    } catch {
      refresh(); // reconcile on failure
    }
  };

  const markAllRead = async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
    try {
      await api.put("/notifications/read-all");
    } catch {
      refresh();
    }
  };

  return (
    <NotificationContext.Provider value={{ notifications, unreadCount, markRead, markAllRead, refresh }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("useNotifications must be used within a NotificationProvider");
  return ctx;
}
