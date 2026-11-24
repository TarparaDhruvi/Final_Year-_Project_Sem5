import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FiCheckCircle, FiXCircle } from "react-icons/fi";
import api from "../services/api";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState("verifying"); // verifying | success | error
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No verification token found in this link.");
      return;
    }
    api
      .post("/auth/verify-email", { token })
      .then(({ data }) => {
        setStatus("success");
        setMessage(data.message);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err.response?.data?.detail || "This verification link is invalid or expired.");
      });
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center px-6 bg-gradient-to-br from-surface via-white to-secondary/10 dark:from-dark dark:via-dark dark:to-primary/10">
      <div className="glass-card w-full max-w-md p-8 text-center">
        {status === "verifying" && (
          <div className="w-10 h-10 mx-auto border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-6" />
        )}
        {status === "success" && <FiCheckCircle className="text-success text-5xl mx-auto mb-6" />}
        {status === "error" && <FiXCircle className="text-danger text-5xl mx-auto mb-6" />}

        <h1 className="text-xl font-display font-bold mb-2">
          {status === "verifying" ? "Verifying your email..." : status === "success" ? "Email verified!" : "Verification failed"}
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">{message}</p>

        <Link to="/login/student" className="btn-primary inline-block">
          Go to login
        </Link>
      </div>
    </div>
  );
}
