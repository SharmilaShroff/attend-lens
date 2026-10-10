import { Navigate, Outlet } from "react-router-dom";
import { homeFor, useAuth } from "../context/AuthContext";

/** Route guard: only users whose role is in `allow` may render the nested routes. */
export default function RoleGuard({ allow }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="grid min-h-screen place-items-center text-ink-soft">Loading…</div>;
  if (!user) return <Navigate to="/" replace />;
  if (!allow.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return <Outlet />;
}
