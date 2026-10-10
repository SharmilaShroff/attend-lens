import { useAuth } from "../../context/AuthContext";

/** Staff overview shell (design screen 3). KPI cards, trend chart, student table and
 *  the alert card are wired to live data in the mentor/teacher/analytics steps. */
const KPIS = [
  ["Overall attendance", "—", "bg-brand-100"],
  ["Total students", "—", "bg-sky-50"],
  ["Present today", "—", "bg-violet-50"],
  ["Need a check-in", "—", "bg-orange-50"],
];

export default function Overview() {
  const { user } = useAuth();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  return (
    <div>
      <h1 className="text-3xl font-extrabold tracking-tight">{greeting}, {user.name.split(" ")[0]}</h1>
      <p className="mt-1 text-sm text-ink-soft">Here’s how your students are showing up.</p>
      <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {KPIS.map(([label, value, bg]) => (
          <div key={label} className={`rounded-xl2 p-5 ${bg}`}>
            <div className="text-xs text-ink-soft">{label}</div>
            <div className="mt-2 text-3xl font-extrabold">{value}</div>
          </div>
        ))}
      </div>
      <div className="card mt-6 p-6 text-sm text-ink-soft">Charts, student list and AI alerts appear here once attendance data is connected.</div>
    </div>
  );
}
