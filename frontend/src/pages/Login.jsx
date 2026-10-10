import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useAuth, homeFor } from "../context/AuthContext";
import { errorMessage } from "../api/client";
import { Lock, Mail, HelpCircle, ArrowUpRight } from "lucide-react";

export default function Login() {
  const [searchParams] = useSearchParams();
  const roleParam = searchParams.get("role") || "mentor";

  const [role, setRole] = useState(roleParam);
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (roleParam) setRole(roleParam);
  }, [roleParam]);

  const handleRoleTabChange = (r) => {
    setRole(r);
    setError("");
    if (r === "mentor") {
      setIdentifier("mentor@example.com");
      setPassword("password123");
    } else if (r === "teacher") {
      setIdentifier("teacher1@example.com");
      setPassword("password123");
    } else {
      setIdentifier("1VA21CS001");
      setPassword("1VA21CS001");
    }
  };

  useEffect(() => {
    handleRoleTabChange(role);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const u = await login({ role, identifier, password });
      if (u) navigate(homeFor(u.role));
    } catch (err) {
      setError(errorMessage(err, "Invalid credentials. Please check your login details."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f4f8f5] flex items-center justify-center p-4 md:p-8">
      <div className="max-w-5xl w-full bg-white rounded-3xl shadow-2xl overflow-hidden grid grid-cols-1 md:grid-cols-12 min-h-[640px] border border-[#1e4d3b]/10">
        
        {/* Left Dark Forest Green Graphic Banner */}
        <div className="md:col-span-5 dark-banner-card p-8 md:p-10 flex flex-col justify-between relative overflow-hidden m-3">
          <div className="z-10">
            <div className="flex items-center gap-2 mb-8">
              <div className="w-8 h-8 rounded-full bg-white text-[#1e4d3b] flex items-center justify-center font-bold text-lg">
                A
              </div>
              <span className="text-xl font-bold tracking-tight text-white">Attend Lens</span>
            </div>

            <span className="text-[10px] font-bold uppercase tracking-widest text-[#a3b899] bg-white/10 px-3 py-1 rounded-full">
              EVERY STUDENT. EVERY DAY.
            </span>
            <h2 className="text-3xl md:text-4xl font-extrabold mt-4 mb-3 leading-tight">
              Small check-ins.<br />Big possibilities.
            </h2>
            <p className="text-xs text-white/80 leading-relaxed max-w-xs">
              Turn attendance into understanding. Help every student stay connected to their learning.
            </p>
          </div>

          <div className="z-10 my-8 flex items-center justify-center relative">
            <div className="w-48 h-48 rounded-full bg-white/10 border border-white/20 flex flex-col items-center justify-center text-center p-4 relative backdrop-blur-md">
              <span className="text-3xl font-extrabold text-white">94.2%</span>
              <span className="text-[11px] text-white/80 font-medium">Showing up. Growing up.</span>
              <div className="absolute top-3 left-4 bg-white text-[#1e4d3b] text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
                ✓ You're right on track!
              </div>
            </div>
          </div>

          <div className="z-10 flex items-center justify-between text-[10px] text-white/60 pt-4 border-t border-white/10">
            <span>A little presence makes a big difference.</span>
            <span>2026 / 27</span>
          </div>
        </div>

        {/* Right Sign-in Form Panel */}
        <div className="md:col-span-7 p-8 md:p-12 flex flex-col justify-between bg-white">
          <div>
            <div className="flex items-center justify-between mb-8">
              <div className="flex bg-[#f4f8f5] p-1 rounded-full border border-[#1e4d3b]/10">
                {["mentor", "teacher", "student"].map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => handleRoleTabChange(r)}
                    className={`px-4 py-1.5 rounded-full text-xs font-semibold capitalize transition-all ${
                      role === r
                        ? "bg-[#1e4d3b] text-white shadow-md"
                        : "text-gray-600 hover:text-[#1e4d3b]"
                    }`}
                  >
                    {r === "teacher" ? "Subject Teacher" : r}
                  </button>
                ))}
              </div>
              <button onClick={() => navigate("/")} className="text-xs text-gray-500 hover:text-[#1e4d3b] flex items-center gap-1">
                <HelpCircle className="w-3.5 h-3.5" /> Need a hand?
              </button>
            </div>

            <span className="text-[11px] font-bold uppercase tracking-wider text-[#1e4d3b]">
              {role.toUpperCase()} / LET'S GET YOU IN
            </span>
            <h2 className="text-3xl font-extrabold text-[#143628] mt-1 mb-2">
              Welcome back, {role}.
            </h2>
            <p className="text-xs text-gray-500 mb-8">
              Sign in to your {role} attendance workspace.
            </p>

            {error && (
              <div className="mb-6 p-3.5 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-2">
                  {role === "student" ? "USN (University Seat Number)" : "Faculty Email ID"}
                </label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder={role === "student" ? "e.g. 1VA21CS001" : "e.g. mentor@example.com"}
                    className="w-full pl-11 pr-4 py-3.5 rounded-2xl bg-[#f4f8f5] border border-transparent focus:border-[#1e4d3b] focus:bg-white text-sm text-[#143628] font-medium outline-none transition-all"
                  />
                  <Mail className="w-5 h-5 text-gray-400 absolute left-3.5 top-3.5" />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-2">Password</label>
                <div className="relative">
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-11 pr-4 py-3.5 rounded-2xl bg-[#f4f8f5] border border-transparent focus:border-[#1e4d3b] focus:bg-white text-sm text-[#143628] font-medium outline-none transition-all"
                  />
                  <Lock className="w-5 h-5 text-gray-400 absolute left-3.5 top-3.5" />
                </div>
              </div>

              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2 cursor-pointer text-gray-600">
                  <input type="checkbox" defaultChecked className="rounded border-gray-300 text-[#1e4d3b] focus:ring-[#1e4d3b]" />
                  Keep me signed in
                </label>
                <a href="#forgot" onClick={(e) => { e.preventDefault(); alert("Demo password for mentor/teacher is 'password123', for student it is their USN."); }} className="text-gray-500 hover:underline">
                  Forgot password?
                </a>
              </div>

              <div className="pt-4 flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-gray-800">Let's get started</h4>
                  <p className="text-[11px] text-gray-500">A good day begins with showing up.</p>
                </div>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-2 bg-[#1e4d3b] text-white font-bold px-6 py-3.5 rounded-full hover:bg-[#143628] transition-all shadow-md hover:shadow-lg disabled:opacity-50"
                >
                  <span>{submitting ? "Signing in..." : "Sign in"}</span>
                  <ArrowUpRight className="w-4 h-4" />
                </button>
              </div>
            </form>
          </div>

          <div className="pt-6 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-400">
            <span>Demo: {role === "mentor" ? "mentor@example.com" : role === "teacher" ? "teacher1@example.com" : "1VA21CS001"}</span>
            <span>&copy; 2026 Attend Lens</span>
          </div>
        </div>

      </div>
    </div>
  );
}
