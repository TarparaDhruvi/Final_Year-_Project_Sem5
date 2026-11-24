import { useState } from "react";
import toast from "react-hot-toast";
import { FiDownload, FiFileText, FiFile } from "react-icons/fi";
import DashboardLayout from "../../layouts/DashboardLayout";
import { useAuth } from "../../context/AuthContext";
import { downloadReport } from "../../utils/download";

const DEPARTMENTS = ["Computer Science", "Information Technology", "Electronics & Communication", "Electrical Engineering", "Mechanical Engineering", "Civil Engineering", "Commerce", "Science", "Law", "Other"];

function ReportButton({ label, icon: Icon, onClick, busy }) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      className="glass-card p-5 text-left hover:-translate-y-1 hover:shadow-xl transition-all duration-200 disabled:opacity-60 disabled:hover:translate-y-0 w-full"
    >
      <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-3"><Icon /></div>
      <p className="text-sm font-semibold flex items-center gap-2">{busy ? "Preparing…" : label} {!busy && <FiDownload className="text-slate-400" size={14} />}</p>
    </button>
  );
}

export default function Reports() {
  const { user } = useAuth();
  const [department, setDepartment] = useState("");
  const [semester, setSemester] = useState("");
  const [busyKey, setBusyKey] = useState(null);

  const run = async (key, url, params, filename) => {
    setBusyKey(key);
    try {
      await downloadReport(url, params, filename);
      toast.success("Report downloaded.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Couldn't generate that report.");
    } finally {
      setBusyKey(null);
    }
  };

  const scopeParams = (format) => ({ format, ...(department && { department }), ...(semester && { semester }) });

  return (
    <DashboardLayout>
      <div className="pt-2">
        <h1 className="text-2xl font-display font-bold mb-1">Reports</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          {user.role === "admin" && "Attendance and marks reports across the college, filterable by department and semester."}
          {user.role === "faculty" && "A performance report across every student in your assigned subjects."}
          {user.role === "student" && "Your own attendance and marks, as a downloadable PDF."}
        </p>

        {user.role === "admin" && (
          <>
            <div className="glass-card p-4 mb-6 flex flex-wrap gap-3">
              <select className="input-field !py-2 w-auto" value={department} onChange={(e) => setDepartment(e.target.value)}>
                <option value="">All Departments</option>
                {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
              <select className="input-field !py-2 w-auto" value={semester} onChange={(e) => setSemester(e.target.value)}>
                <option value="">All Semesters</option>
                {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => <option key={s} value={s}>Semester {s}</option>)}
              </select>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <ReportButton label="Attendance — PDF" icon={FiFileText} busy={busyKey === "att-pdf"} onClick={() => run("att-pdf", "/reports/attendance", scopeParams("pdf"), "attendance_report.pdf")} />
              <ReportButton label="Attendance — Excel" icon={FiFile} busy={busyKey === "att-xlsx"} onClick={() => run("att-xlsx", "/reports/attendance", scopeParams("excel"), "attendance_report.xlsx")} />
              <ReportButton label="Marks — PDF" icon={FiFileText} busy={busyKey === "marks-pdf"} onClick={() => run("marks-pdf", "/reports/marks", scopeParams("pdf"), "marks_report.pdf")} />
              <ReportButton label="Marks — Excel" icon={FiFile} busy={busyKey === "marks-xlsx"} onClick={() => run("marks-xlsx", "/reports/marks", scopeParams("excel"), "marks_report.xlsx")} />
            </div>
          </>
        )}

        {user.role === "faculty" && (
          <div className="grid sm:grid-cols-2 gap-4">
            <ReportButton label="Student Performance — PDF" icon={FiFileText} busy={busyKey === "perf-pdf"} onClick={() => run("perf-pdf", "/reports/my-students", { format: "pdf" }, "student_performance_report.pdf")} />
            <ReportButton label="Student Performance — Excel" icon={FiFile} busy={busyKey === "perf-xlsx"} onClick={() => run("perf-xlsx", "/reports/my-students", { format: "excel" }, "student_performance_report.xlsx")} />
          </div>
        )}

        {user.role === "student" && (
          <div className="max-w-sm">
            <ReportButton label="My Progress Report — PDF" icon={FiFileText} busy={busyKey === "progress"} onClick={() => run("progress", "/reports/my-progress", {}, "my_progress_report.pdf")} />
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
