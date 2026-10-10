import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import { LogOut, Bell } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <header className="bg-white/80 backdrop-blur-md border-b border-[#1e4d3b]/10 sticky top-0 z-30 px-6 py-3.5 flex items-center justify-between">
      <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate(user?.role === "student" ? "/student" : "/staff")}>
        <div className="w-8 h-8 rounded-full bg-[#1e4d3b] text-white flex items-center justify-center font-bold text-lg shadow-sm">
          A
        </div>
        <span className="text-xl font-bold tracking-tight text-[#143628]">Attend Lens</span>
        <span className="text-xs font-semibold px-3 py-1 rounded-full bg-[#e8f5e9] text-[#1e4d3b] uppercase tracking-wider ml-2">
          {user?.role === "student" ? "Student Workspace" : user?.role === "mentor" ? "Mentor Workspace" : "Teacher Workspace"}
        </span>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={() => alert("All AI Risk Alerts are up to date!")}
          className="w-9 h-9 rounded-full bg-[#f4f8f5] hover:bg-[#e8f5e9] flex items-center justify-center text-[#1e4d3b] transition-colors relative"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="w-2 h-2 rounded-full bg-red-500 absolute top-2 right-2 ring-2 ring-white"></span>
        </button>

        <div className="flex items-center gap-3 border-l border-gray-200 pl-4">
          <div className="w-9 h-9 rounded-full bg-[#1e4d3b] text-white flex items-center justify-center font-bold text-sm">
            {user?.name ? user.name.slice(0, 2).toUpperCase() : "U"}
          </div>
          <div className="hidden sm:flex flex-col">
            <span className="text-xs font-bold text-gray-800">{user?.name}</span>
            <span className="text-[10px] text-gray-500 capitalize">{user?.role}</span>
          </div>
          <button
            onClick={handleLogout}
            className="p-2 text-gray-400 hover:text-red-600 rounded-full hover:bg-red-50 transition-colors ml-1"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
