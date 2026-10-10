import { useNavigate } from "react-router-dom";
import { Logo } from "../../components/Brand";
import { useAuth } from "../../context/AuthContext";

/** Student dashboard placeholder; the full dashboard (bar chart, calculator, chatbot) is step 7. */
export default function StudentDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="mx-auto max-w-4xl p-8">
      <div className="flex items-center justify-between">
        <Logo />
        <button className="text-sm font-semibold text-brand-700" onClick={() => { logout(); navigate("/"); }}>Log out</button>
      </div>
      <h1 className="mt-10 text-3xl font-extrabold tracking-tight">Hi, {user.name.split(" ")[0]}</h1>
      <p className="mt-1 text-sm text-ink-soft">Your attendance dashboard will appear here.</p>
    </div>
  );
}
