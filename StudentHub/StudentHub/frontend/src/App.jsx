import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { NotificationProvider } from "./context/NotificationContext";
import ProtectedRoute from "./routes/ProtectedRoute";

import Landing from "./pages/Landing";
import RoleSelect from "./pages/RoleSelect";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import VerifyEmail from "./pages/VerifyEmail";
import ErrorPage from "./pages/ErrorPage";

import AdminDashboard from "./pages/dashboards/AdminDashboard";
import FacultyDashboard from "./pages/dashboards/FacultyDashboard";
import StudentDashboard from "./pages/dashboards/StudentDashboard";

import StudentManagement from "./pages/admin/StudentManagement";
import FacultyManagement from "./pages/admin/FacultyManagement";
import SubjectManagement from "./pages/admin/SubjectManagement";
import TimetableManagement from "./pages/admin/TimetableManagement";
import LeaveManagement from "./pages/admin/LeaveManagement";

import FacultyAttendance from "./pages/faculty/FacultyAttendance";
import FacultyAssignments from "./pages/faculty/FacultyAssignments";
import FacultyNotes from "./pages/faculty/FacultyNotes";
import FacultyMarks from "./pages/faculty/FacultyMarks";
import FacultyStudents from "./pages/faculty/FacultyStudents";

import StudentAttendance from "./pages/student/StudentAttendance";
import StudentAssignments from "./pages/student/StudentAssignments";
import StudentNotes from "./pages/student/StudentNotes";
import StudentMarks from "./pages/student/StudentMarks";

import AnnouncementCenter from "./pages/shared/AnnouncementCenter";
import AnnouncementsView from "./pages/shared/AnnouncementsView";
import LeaveApply from "./pages/shared/LeaveApply";
import NotificationCenter from "./pages/shared/NotificationCenter";
import AIChat from "./pages/student/AIChat";
import Profile from "./pages/shared/Profile";
import MySchedule from "./pages/shared/MySchedule";
import Reports from "./pages/shared/Reports";
import SkillWallet from "./pages/student/SkillWallet";
import StudyCoach from "./pages/student/StudyCoach";
import DoubtWall from "./pages/shared/DoubtWall";
import SmartCalendar from "./pages/shared/SmartCalendar";
import FacultyHeatmap from "./pages/admin/FacultyHeatmap";
import SilentStudentFinder from "./pages/admin/SilentStudentFinder";
import CampusPulse from "./pages/admin/CampusPulse";
import MissedActivityModal from "./components/MissedActivityModal";

function Protected({ role, children }) {
  return <ProtectedRoute allowedRoles={[role]}>{children}</ProtectedRoute>;
}

function ProtectedAny({ children }) {
  return <ProtectedRoute>{children}</ProtectedRoute>;
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <NotificationProvider>
          <BrowserRouter>
            <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
            <MissedActivityModal />
            <Routes>
              {/* Public */}
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<RoleSelect />} />
              <Route path="/login/:role" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/verify-email" element={<VerifyEmail />} />

              {/* Admin */}
              <Route path="/admin/dashboard" element={<Protected role="admin"><AdminDashboard /></Protected>} />
              <Route path="/admin/students" element={<Protected role="admin"><StudentManagement /></Protected>} />
              <Route path="/admin/faculty" element={<Protected role="admin"><FacultyManagement /></Protected>} />
              <Route path="/admin/subjects" element={<Protected role="admin"><SubjectManagement /></Protected>} />
              <Route path="/admin/timetable" element={<Protected role="admin"><TimetableManagement /></Protected>} />
              <Route path="/admin/leave" element={<Protected role="admin"><LeaveManagement /></Protected>} />
              <Route path="/admin/announcements" element={<Protected role="admin"><AnnouncementCenter /></Protected>} />
              <Route path="/admin/reports" element={<Protected role="admin"><Reports /></Protected>} />
              <Route path="/admin/faculty-heatmap" element={<Protected role="admin"><FacultyHeatmap /></Protected>} />
              <Route path="/admin/silent-students" element={<Protected role="admin"><SilentStudentFinder /></Protected>} />
              <Route path="/admin/campus-pulse" element={<Protected role="admin"><CampusPulse /></Protected>} />
              <Route path="/admin/calendar" element={<Protected role="admin"><SmartCalendar /></Protected>} />

              {/* Faculty */}
              <Route path="/faculty/dashboard" element={<Protected role="faculty"><FacultyDashboard /></Protected>} />
              <Route path="/faculty/students" element={<Protected role="faculty"><FacultyStudents /></Protected>} />
              <Route path="/faculty/attendance" element={<Protected role="faculty"><FacultyAttendance /></Protected>} />
              <Route path="/faculty/assignments" element={<Protected role="faculty"><FacultyAssignments /></Protected>} />
              <Route path="/faculty/notes" element={<Protected role="faculty"><FacultyNotes /></Protected>} />
              <Route path="/faculty/marks" element={<Protected role="faculty"><FacultyMarks /></Protected>} />
              <Route path="/faculty/leave" element={<Protected role="faculty"><LeaveApply /></Protected>} />
              <Route path="/faculty/announcements" element={<Protected role="faculty"><AnnouncementCenter /></Protected>} />
              <Route path="/faculty/schedule" element={<Protected role="faculty"><MySchedule /></Protected>} />
              <Route path="/faculty/reports" element={<Protected role="faculty"><Reports /></Protected>} />
              <Route path="/faculty/doubt-wall" element={<Protected role="faculty"><DoubtWall /></Protected>} />
              <Route path="/faculty/calendar" element={<Protected role="faculty"><SmartCalendar /></Protected>} />

              {/* Student */}
              <Route path="/student/dashboard" element={<Protected role="student"><StudentDashboard /></Protected>} />
              <Route path="/student/attendance" element={<Protected role="student"><StudentAttendance /></Protected>} />
              <Route path="/student/assignments" element={<Protected role="student"><StudentAssignments /></Protected>} />
              <Route path="/student/notes" element={<Protected role="student"><StudentNotes /></Protected>} />
              <Route path="/student/marks" element={<Protected role="student"><StudentMarks /></Protected>} />
              <Route path="/student/leave" element={<Protected role="student"><LeaveApply /></Protected>} />
              <Route path="/student/announcements" element={<Protected role="student"><AnnouncementsView /></Protected>} />
              <Route path="/student/ai" element={<Protected role="student"><AIChat /></Protected>} />
              <Route path="/student/schedule" element={<Protected role="student"><MySchedule /></Protected>} />
              <Route path="/student/reports" element={<Protected role="student"><Reports /></Protected>} />
              <Route path="/student/skill-wallet" element={<Protected role="student"><SkillWallet /></Protected>} />
              <Route path="/student/study-coach" element={<Protected role="student"><StudyCoach /></Protected>} />
              <Route path="/student/doubt-wall" element={<Protected role="student"><DoubtWall /></Protected>} />
              <Route path="/student/calendar" element={<Protected role="student"><SmartCalendar /></Protected>} />

              {/* Shared across all roles (AI pages are NOT shared — they live only under /student) */}
              <Route path="/notifications" element={<ProtectedAny><NotificationCenter /></ProtectedAny>} />
              <Route path="/profile" element={<ProtectedAny><Profile /></ProtectedAny>} />

              {/* Errors */}
              <Route path="/400" element={<ErrorPage code={400} />} />
              <Route path="/401" element={<ErrorPage code={401} />} />
              <Route path="/403" element={<ErrorPage code={403} />} />
              <Route path="/500" element={<ErrorPage code={500} />} />
              <Route path="*" element={<ErrorPage code={404} />} />
            </Routes>
          </BrowserRouter>
        </NotificationProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
