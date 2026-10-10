import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import RolePicker from "./pages/RolePicker";
import Login from "./pages/Login";
import MentorDashboard from "./pages/staff/MentorDashboard";
import TeacherDashboard from "./pages/staff/TeacherDashboard";
import StudentDashboard from "./pages/student/StudentDashboard";
import StudentSubjectDetail from "./pages/student/StudentSubjectDetail";
import StudentProfile from "./pages/staff/StudentProfile";
import SubjectMonthlyTrend from "./pages/staff/SubjectMonthlyTrend";
import StudentRemarksHistory from "./pages/staff/StudentRemarksHistory";
import FloatingChatbot from "./components/FloatingChatbot";

function StaffDispatcher() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "mentor") return <MentorDashboard />;
  if (user.role === "teacher") return <TeacherDashboard />;
  return <Navigate to="/student" replace />;
}

function ProtectedStudent() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <StudentDashboard />;
}

function AuthenticatedLayout({ children }) {
  const { user } = useAuth();
  return (
    <>
      {children}
      {user && <FloatingChatbot />}
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<RolePicker />} />
        <Route path="/login" element={<Login />} />
        <Route path="/staff/*" element={<AuthenticatedLayout><StaffDispatcher /></AuthenticatedLayout>} />
        <Route path="/student/subject/:subjectId" element={<AuthenticatedLayout><StudentSubjectDetail /></AuthenticatedLayout>} />
        <Route path="/student-profile/:id/subject/:subjectId" element={<AuthenticatedLayout><SubjectMonthlyTrend /></AuthenticatedLayout>} />
        <Route path="/student/:id/subject/:subjectId" element={<AuthenticatedLayout><SubjectMonthlyTrend /></AuthenticatedLayout>} />
        <Route path="/student-profile/:id/remarks" element={<AuthenticatedLayout><StudentRemarksHistory /></AuthenticatedLayout>} />
        <Route path="/student/:id/remarks" element={<AuthenticatedLayout><StudentRemarksHistory /></AuthenticatedLayout>} />
        <Route path="/student-profile/:id" element={<AuthenticatedLayout><StudentProfile /></AuthenticatedLayout>} />
        <Route path="/student/:id" element={<AuthenticatedLayout><StudentProfile /></AuthenticatedLayout>} />
        <Route path="/student/*" element={<AuthenticatedLayout><ProtectedStudent /></AuthenticatedLayout>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}


