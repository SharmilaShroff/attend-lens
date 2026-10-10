import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Logo } from "./Brand";
import { useAuth } from "../context/AuthContext";

// Sidebar items per role (more routes are added as each module is built).
const NAV = {
  mentor: [["Overview", "/staff"], ["Students", "/staff/students"], ["Attendance", "/staff/attendance"], ["Insights", "/staff/insights"], ["Reports", "/staff/reports"]],
  teacher: [["Overview", "/staff"], ["Classes", "/staff/classes"], ["Mark attendance", "/staff/attendance"], ["Insights", "/staff/insights"]],
};

export default function StaffLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const items = NAV[user.role] || NAV.teacher;
  const initials = user.name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="flex min-h-screen bg-surface">
      <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col border-r border-brand-100 bg-white px-4 py-6 md:flex">
        <Logo />
        <nav className="mt-8 flex flex-col gap-1">
          {items.map(([label, to]) => (
            <NavLink key={to} to={to} end={to === "/staff"}
              className={({ isActive }) => `rounded-full px-4 py-2.5 text-sm font-semibold transition ${isActive ? "bg-brand-700 text-white" : "text-ink-soft hover:bg-brand-50"}`}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto flex items-center gap-3 rounded-xl2 bg-brand-50 p-3">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-700 text-xs font-bold text-white">{initials}</span>
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-bold">{user.name}</div>
            <div className="text-[11px] capitalize text-ink-soft">{user.role}</div>
          </div>
          <button onClick={() => { logout(); navigate("/"); }} className="text-[11px] font-semibold text-brand-700 hover:underline">Log out</button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-6 lg:p-8"><Outlet /></main>
    </div>
  );
}
