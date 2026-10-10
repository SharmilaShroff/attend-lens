import { LayoutDashboard, Users, BookOpen, AlertTriangle, MessageSquare, History, FileSpreadsheet } from "lucide-react";

export default function Sidebar({ activeTab, setActiveTab, role }) {
  const mentorNav = [
    { id: "overview", label: "Overview & Analytics", icon: LayoutDashboard },
    { id: "classes", label: "Class Management", icon: Users },
    { id: "students", label: "Students & CSV Import", icon: FileSpreadsheet },
    { id: "subjects", label: "Subjects & Teachers", icon: BookOpen },
    { id: "alerts", label: "AI Risk Queue", icon: AlertTriangle },
    { id: "audit", label: "Audit Logs", icon: History },
  ];

  const teacherNav = [
    { id: "overview", label: "Teacher Dashboard", icon: LayoutDashboard },
    { id: "mark", label: "Mark Attendance Grid", icon: BookOpen },
    { id: "audit", label: "Audit & Edit History", icon: History },
    { id: "alerts", label: "Subject Alerts", icon: AlertTriangle },
  ];

  const studentNav = [
    { id: "dashboard", label: "My Attendance", icon: LayoutDashboard },
    { id: "reasons", label: "Absence Reasons", icon: FileSpreadsheet },
    { id: "counselling", label: "AI Counselling Inbox", icon: MessageSquare },
  ];

  const items = role === "student" ? studentNav : role === "mentor" ? mentorNav : teacherNav;

  return (
    <aside className="w-64 bg-white/70 backdrop-blur-md border-r border-[#1e4d3b]/10 min-h-[calc(100vh-61px)] p-4 flex flex-col justify-between">
      <div className="space-y-1">
        <span className="text-[10px] font-bold text-[#1e4d3b] uppercase tracking-wider px-3 mb-2 block">
          Navigation Menu
        </span>
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-3 rounded-2xl text-xs font-semibold transition-all ${
                isActive
                  ? "bg-[#1e4d3b] text-white shadow-md"
                  : "text-gray-600 hover:bg-[#e8f5e9] hover:text-[#1e4d3b]"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

    </aside>
  );
}
