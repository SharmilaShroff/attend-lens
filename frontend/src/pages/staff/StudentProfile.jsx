import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../../api/client";
import Navbar from "../../components/Navbar";
import {
  ArrowLeft,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  Calendar,
  Users,
  Clock,
  Award,
  AlertCircle,
  MessageSquare,
  Send,
  ChevronRight,
  ShieldCheck
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
  ReferenceLine,
  LabelList
} from "recharts";

const BAR_COLORS = [
  "#1e4d3b", // Forest Green
  "#0288d1", // Ocean Blue
  "#7b1fa2", // Deep Purple
  "#e65100", // Warm Amber/Orange
  "#2e7d32", // Leaf Green
  "#c2185b", // Crimson Rose
  "#00796b", // Dark Teal
  "#d32f2f"  // Deep Red
];

export default function StudentProfile() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [aiRunning, setAiRunning] = useState(false);

  // Remarks state
  const [remarks, setRemarks] = useState([]);
  const [newRemarkText, setNewRemarkText] = useState("");
  const [savingRemark, setSavingRemark] = useState(false);
  const [remarkError, setRemarkError] = useState(null);

  const fetchProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get(`/analytics/student-profile/${id}`);
      setProfile(data);
    } catch (err) {
      console.error("Failed to load student profile:", err);
      setError("Failed to load student attendance analytics. Please verify backend connection.");
    } finally {
      setLoading(false);
    }
  };

  const fetchRemarks = async () => {
    try {
      const { data } = await api.get(`/remarks/student/${id}`);
      setRemarks(data || []);
    } catch (err) {
      console.error("Failed to fetch student remarks:", err);
    }
  };

  useEffect(() => {
    fetchProfile();
    fetchRemarks();
  }, [id]);

  const handleRerunAi = async () => {
    setAiRunning(true);
    try {
      const { data } = await api.post(`/analytics/student-profile/${id}/rerun-ai`);
      if (data && data.analysis_points) {
        setProfile((prev) => ({
          ...prev,
          analysis_points: data.analysis_points
        }));
      } else {
        await fetchProfile();
      }
    } catch (err) {
      console.error("Failed to re-run AI analysis:", err);
      alert("Failed to refresh AI analysis. Please check network connection.");
    } finally {
      setAiRunning(false);
    }
  };

  const handleSaveRemark = async (e) => {
    e.preventDefault();
    if (!newRemarkText.trim()) {
      setRemarkError("Remark content cannot be empty.");
      return;
    }
    setSavingRemark(true);
    setRemarkError(null);
    try {
      await api.post("/remarks", {
        student_id: Number(id),
        text: newRemarkText.trim()
      });
      setNewRemarkText("");
      await fetchRemarks();
    } catch (err) {
      console.error("Failed to save remark:", err);
      setRemarkError("Failed to save remark. Please check connection and try again.");
    } finally {
      setSavingRemark(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f4f8f5]">
        <Navbar />
        <div className="max-w-6xl mx-auto p-8 space-y-6">
          <div className="h-10 bg-white/60 rounded-2xl animate-pulse w-1/4"></div>
          <div className="h-32 bg-white rounded-3xl animate-pulse border border-[#1e4d3b]/10"></div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-96 bg-white rounded-3xl animate-pulse border border-[#1e4d3b]/10"></div>
            <div className="h-96 bg-white rounded-3xl animate-pulse border border-[#1e4d3b]/10"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-[#f4f8f5]">
        <Navbar />
        <div className="max-w-2xl mx-auto mt-16 p-8 bg-white rounded-3xl border border-red-200 text-center space-y-4 shadow-sm">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
          <h2 className="text-xl font-extrabold text-[#143628]">Unable to Load Student Data</h2>
          <p className="text-xs text-gray-600">{error || "Student record not found."}</p>
          <div className="flex justify-center gap-3 pt-2">
            <button
              onClick={() => navigate("/staff")}
              className="text-xs font-bold text-gray-700 bg-gray-100 px-4 py-2.5 rounded-2xl hover:bg-gray-200"
            >
              &larr; Back to Dashboard
            </button>
            <button
              onClick={fetchProfile}
              className="text-xs font-bold text-white bg-[#1e4d3b] px-5 py-2.5 rounded-2xl hover:bg-[#143628] flex items-center gap-2"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { student, subjects = [], analysis_points = {}, attendance_cutoff = 75 } = profile;

  const {
    point_1_lowest = {},
    point_2_pattern = {},
    point_3_eligibility = {},
    point_4_streak = {},
    point_5_peer = {},
    point_6_reasons = {},
    point_7_summary = {}
  } = analysis_points;

  // Chart Data format
  const chartData = subjects.map((sub) => ({
    name: sub.name,
    shortName: sub.code || sub.name.substring(0, 10),
    percentage: sub.percentage,
    attended: sub.attended,
    total: sub.total
  }));

  // Risk Level badge styling
  const riskBadgeClass =
    {
      High: "pill-badge-red",
      Medium: "pill-badge-amber",
      Low: "pill-badge-green"
    }[student.risk_level] || "pill-badge-green";

  const recentRemarks = remarks.slice(0, 2);

  // Absence Pattern Bullets
  const patternBullets = point_2_pattern.bullets || (point_2_pattern.detail ? [point_2_pattern.detail] : []);

  // Reasons info list or single string
  const reasonsInfoList = Array.isArray(point_6_reasons.reasons_info)
    ? point_6_reasons.reasons_info
    : point_6_reasons.reasons_info
    ? [point_6_reasons.reasons_info]
    : ["No information found"];

  return (
    <div className="min-h-screen bg-[#f4f8f5] pb-16">
      <Navbar />

      <main className="max-w-7xl mx-auto p-4 sm:p-6 md:p-8 space-y-6">
        {/* Navigation Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <button
            onClick={() => navigate("/staff")}
            className="inline-flex items-center gap-2 text-xs font-bold text-[#1e4d3b] bg-white border border-[#1e4d3b]/20 px-4 py-2.5 rounded-2xl hover:bg-[#e8f5e9] transition-all shadow-sm w-fit"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRerunAi}
              disabled={aiRunning}
              className="inline-flex items-center gap-2 bg-[#1e4d3b] text-white text-xs font-bold px-4 py-2.5 rounded-2xl hover:bg-[#143628] transition-all shadow-sm disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${aiRunning ? "animate-spin" : ""}`} />
              <span>{aiRunning ? "Analyzing..." : "Re-run AI Analysis"}</span>
            </button>
          </div>
        </div>

        {/* Student Profile Header Card */}
        <div className="bg-white p-6 md:p-8 rounded-3xl border border-[#1e4d3b]/10 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-3xl bg-[#1e4d3b] text-white flex items-center justify-center font-extrabold text-2xl shadow-md shrink-0">
              {student.name ? student.name.slice(0, 2).toUpperCase() : "ST"}
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl font-extrabold text-[#143628]">{student.name}</h1>
                <span className={`pill-badge ${riskBadgeClass}`}>{student.risk_level} Risk</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                USN: <strong className="text-gray-700">{student.usn}</strong> | Class:{" "}
                <span className="text-gray-700 font-semibold">{student.class_name}</span> | Email:{" "}
                <span className="text-gray-700">{student.email || "-"}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 flex-wrap">
            <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 text-center min-w-[130px] flex-1 sm:flex-none">
              <span className="text-[10px] font-bold text-gray-500 uppercase block">Overall Attendance</span>
              <span className="text-3xl font-extrabold text-[#143628]">{student.overall_pct}%</span>
            </div>

            <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 text-center min-w-[130px] flex-1 sm:flex-none">
              <span className="text-[10px] font-bold text-gray-500 uppercase block">Required Cutoff</span>
              <span className="text-3xl font-extrabold text-[#1e4d3b]">{attendance_cutoff}%</span>
            </div>
          </div>
        </div>

        {/* Side-by-Side Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* LEFT DIVISION: Bar Graph, Subject Buttons & Remarks */}
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-6">
              <div className="flex items-center justify-between pb-2 border-b border-gray-100">
                <div>
                  <span className="text-[10px] font-extrabold text-[#1e4d3b] uppercase tracking-wider bg-[#e8f5e9] px-2.5 py-1 rounded-full">
                    SUBJECT ATTENDANCE
                  </span>
                  <h2 className="text-lg font-extrabold text-[#143628] mt-1">
                    Subject-Wise Attendance Bar Graph
                  </h2>
                </div>
                <div className="text-[11px] font-bold text-gray-500">
                  Cutoff: <span className="text-red-600 font-extrabold">{attendance_cutoff}%</span>
                </div>
              </div>

              {/* Recharts Bar Chart */}
              <div className="h-72 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 25, right: 20, left: -15, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                    <XAxis
                      dataKey="shortName"
                      tick={{ fontSize: 11, fill: "#4b5563", fontWeight: 600 }}
                      interval={0}
                    />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#4b5563" }} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-[#143628] text-white p-3 rounded-2xl shadow-xl text-xs space-y-1">
                              <p className="font-bold text-emerald-300">{data.name}</p>
                              <p>
                                Attendance: <span className="font-extrabold">{data.percentage}%</span>
                              </p>
                              <p className="text-gray-300 text-[10px]">
                                Classes: {data.attended} / {data.total}
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <ReferenceLine
                      y={attendance_cutoff}
                      stroke="#d32f2f"
                      strokeDasharray="4 4"
                      label={{
                        value: `${attendance_cutoff}% Cutoff`,
                        fill: "#d32f2f",
                        position: "top",
                        fontSize: 10,
                        fontWeight: "bold"
                      }}
                    />
                    <Bar dataKey="percentage" radius={[8, 8, 0, 0]}>
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                      ))}
                      <LabelList
                        dataKey="percentage"
                        position="top"
                        formatter={(val) => `${val}%`}
                        style={{ fontSize: "11px", fontWeight: "bold", fill: "#143628" }}
                      />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Subject Attendance Breakdown - Interactive Buttons Only */}
              <div className="space-y-3 pt-2 border-t border-gray-100">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-extrabold text-[#143628] uppercase tracking-wider">
                    Subject Attendance Breakdown
                  </h3>
                  <span className="text-[10px] text-gray-500 font-bold">Click subject to view trend</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {subjects.map((sub, idx) => {
                    const color = BAR_COLORS[idx % BAR_COLORS.length];
                    return (
                      <button
                        key={sub.subject_id}
                        onClick={() => navigate(`/student/${id}/subject/${sub.subject_id}`)}
                        className="p-3.5 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 space-y-2 text-left hover:shadow-md hover:border-[#1e4d3b]/30 transition-all group"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <span
                              className="w-3 h-3 rounded-full shrink-0 group-hover:scale-110 transition-transform"
                              style={{ backgroundColor: color }}
                            ></span>
                            <span className="font-bold text-[#143628] truncate max-w-[130px]">
                              {sub.name}
                            </span>
                          </div>
                          <span className="font-extrabold text-[#1e4d3b]">{sub.percentage}%</span>
                        </div>

                        <div className="w-full bg-gray-200 h-2 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${Math.min(100, sub.percentage)}%`,
                              backgroundColor: color
                            }}
                          ></div>
                        </div>

                        <div className="flex justify-between items-center text-[10px] text-gray-500 pt-0.5">
                          <span>Attended: {sub.attended} / {sub.total}</span>
                          <span className="text-[#1e4d3b] font-bold group-hover:underline flex items-center gap-0.5">
                            Line Graph &rarr;
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Mentor Remarks Section */}
            <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-[#1e4d3b]" />
                  <h2 className="text-base font-extrabold text-[#143628]">Mentor Remarks</h2>
                </div>
                <span className="text-[10px] font-bold text-gray-500 bg-[#f4f8f5] px-2.5 py-1 rounded-full border border-[#1e4d3b]/10">
                  STUDENT FEEDBACK
                </span>
              </div>

              {/* Add Remark Form */}
              <form onSubmit={handleSaveRemark} className="space-y-2">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newRemarkText}
                    onChange={(e) => setNewRemarkText(e.target.value)}
                    placeholder="Write a remark for this student..."
                    className="flex-1 text-xs border border-gray-200 rounded-2xl px-3.5 py-2.5 outline-none focus:border-[#1e4d3b] focus:ring-1 focus:ring-[#1e4d3b] bg-[#f4f8f5]"
                  />
                  <button
                    type="submit"
                    disabled={savingRemark}
                    className="bg-[#1e4d3b] text-white text-xs font-bold px-4 py-2.5 rounded-2xl hover:bg-[#143628] transition-all flex items-center gap-1.5 shrink-0 disabled:opacity-50 shadow-sm"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>{savingRemark ? "Saving..." : "Save"}</span>
                  </button>
                </div>
                {remarkError && (
                  <p className="text-[11px] font-semibold text-red-600 pl-1">{remarkError}</p>
                )}
              </form>

              {/* 2 Most Recent Remarks List */}
              <div className="space-y-2.5 pt-1">
                {recentRemarks.length === 0 ? (
                  <p className="text-xs text-gray-500 italic p-3 bg-[#f4f8f5] rounded-2xl text-center">
                    No remarks recorded yet. Add a remark above.
                  </p>
                ) : (
                  recentRemarks.map((rem) => (
                    <div
                      key={rem.id}
                      className="p-3.5 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 space-y-1 text-xs"
                    >
                      <div className="flex items-center justify-between text-[10px] text-gray-500">
                        <span className="font-bold text-[#143628]">{rem.author_name || "Mentor"}</span>
                        <span>{new Date(rem.created_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
                      </div>
                      <p className="text-gray-800 leading-relaxed font-medium">{rem.text}</p>
                    </div>
                  ))
                )}
              </div>

              {/* Show More Link */}
              {remarks.length > 2 && (
                <div className="pt-1 text-right">
                  <button
                    onClick={() => navigate(`/student/${id}/remarks`)}
                    className="inline-flex items-center gap-1 text-xs font-bold text-[#1e4d3b] hover:underline"
                  >
                    <span>Show more ({remarks.length} total)</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* RIGHT DIVISION: Attendance Analysis (Light Green Background Card Style) */}
          <div className="bg-[#f0fdf4] p-5 rounded-3xl border border-emerald-200/80 shadow-sm space-y-4">
            <div className="bg-white p-4 rounded-2xl border border-emerald-200/60 shadow-sm flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-[#1e4d3b]" />
                <h2 className="text-lg font-extrabold text-[#143628]">
                  Attendance Analysis
                </h2>
              </div>
              <span className="text-[10px] font-bold text-emerald-800 bg-emerald-100 px-3 py-1 rounded-full border border-emerald-300 flex items-center gap-1">
                <span>✨ AI Generated</span>
              </span>
            </div>

            {/* AI Error Alert with Retry button if OpenRouter call returned error */}
            {analysis_points.ai_error && (
              <div className="bg-red-50 p-4 rounded-2xl border border-red-200 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-red-700 font-bold">
                    <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                    <span>OpenRouter AI Notice</span>
                  </div>
                  <button
                    onClick={handleRerunAi}
                    disabled={aiRunning}
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-white bg-red-600 px-3 py-1 rounded-xl hover:bg-red-700 transition-all shadow-sm"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${aiRunning ? "animate-spin" : ""}`} /> Retry
                  </button>
                </div>
                <p className="text-red-800 text-[11px] font-medium pl-6">{analysis_points.ai_error}</p>
              </div>
            )}

            {/* Compact Scroll Container for Analysis Cards */}
            <div className="max-h-[620px] overflow-y-auto pr-1 space-y-4">
              {/* Point 1: Lowest Attendance Subject (Neutral green if all >= 75%, no warning style!) */}
              <div className="bg-white p-5 rounded-3xl border border-emerald-200/60 shadow-sm space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-extrabold ${point_1_lowest.is_warning ? "bg-red-100 text-red-700" : "bg-emerald-100 text-emerald-700"}`}>
                      1
                    </span>
                    <h3 className="text-sm font-extrabold text-[#143628]">{point_1_lowest.title || "Lowest Attendance Subject"}</h3>
                  </div>
                  <span className={`text-xs font-extrabold px-2.5 py-0.5 rounded-full border ${point_1_lowest.is_warning ? "bg-red-100 text-red-800 border-red-300" : "bg-emerald-100 text-emerald-800 border-emerald-300"}`}>
                    {point_1_lowest.badge || "75%+"}
                  </span>
                </div>
                <p className="text-xs text-gray-700 leading-relaxed font-medium pl-8">
                  {point_1_lowest.detail || "All subjects are at or above 75%."}
                </p>
              </div>

              {/* Point 2: Absence Pattern Analysis (Short Bullet Points) */}
              <div className="bg-white p-5 rounded-3xl border border-emerald-200/60 shadow-sm space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-extrabold">
                      2
                    </span>
                    <h3 className="text-sm font-extrabold text-[#143628]">{point_2_pattern.title || "Absence Pattern Analysis"}</h3>
                  </div>
                  <Calendar className="w-4 h-4 text-amber-600" />
                </div>

                <div className="pl-8">
                  <ul className="list-disc pl-4 text-xs text-gray-700 space-y-1 font-medium">
                    {patternBullets.map((bullet, idx) => (
                      <li key={idx} className="leading-relaxed">{bullet}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Point 3: Next Exam Eligibility (Per Subject, NO EXAM NAMES) */}
              <div className="bg-white p-5 rounded-3xl border border-emerald-200/60 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-extrabold">
                      3
                    </span>
                    <h3 className="text-sm font-extrabold text-[#143628]">{point_3_eligibility.title || "Next Exam Eligibility"}</h3>
                  </div>
                  <Award className="w-4 h-4 text-emerald-600" />
                </div>

                <p className="text-xs text-gray-700 leading-relaxed font-medium pl-8">
                  {point_3_eligibility.detail || "Exam eligibility status per subject based on 75% cutoff:"}
                </p>

                {/* Per-Subject Status Rows (No Exam Names) */}
                {point_3_eligibility.subjects && point_3_eligibility.subjects.length > 0 ? (
                  <div className="pl-8 space-y-2">
                    {point_3_eligibility.subjects.map((s, idx) => {
                      const isEligible = s.status === "Eligible";
                      return (
                        <div
                          key={idx}
                          className="flex items-center justify-between text-xs p-2.5 rounded-2xl bg-[#f4f8f5] border border-gray-100"
                        >
                          <span className="font-bold text-[#143628]">{s.name} ({s.pct}%)</span>
                          <span
                            className={`text-[10px] font-extrabold px-2.5 py-0.5 rounded-full border ${
                              isEligible
                                ? "bg-emerald-100 text-emerald-900 border-emerald-300"
                                : "bg-red-100 text-red-900 border-red-300"
                            }`}
                          >
                            {s.status}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="pl-8 text-xs text-gray-500 italic">No subject eligibility data available.</div>
                )}
              </div>

              {/* Point 4: Consecutive Absences (Two Columns Side by Side) */}
              <div className="bg-white p-5 rounded-3xl border border-emerald-200/60 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-extrabold">
                      4
                    </span>
                    <h3 className="text-sm font-extrabold text-[#143628]">Consecutive Absences</h3>
                  </div>
                  <Clock className="w-4 h-4 text-purple-600" />
                </div>

                {/* Two Columns Side by Side */}
                <div className="pl-8 grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 text-center">
                    <span className="text-[10px] text-gray-500 font-bold block uppercase">Recent Continuous Absence</span>
                    <span className="font-extrabold text-[#143628] text-lg block mt-0.5">
                      {point_4_streak.recent_continuous_absence ?? 0} days
                    </span>
                  </div>
                  <div className="p-3 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 text-center">
                    <span className="text-[10px] text-gray-500 font-bold block uppercase">Longest Continuous Absence</span>
                    <span className="font-extrabold text-purple-800 text-lg block mt-0.5">
                      {point_4_streak.longest_continuous_absence ?? 0} days
                    </span>
                  </div>
                </div>

                {point_4_streak.detail && (
                  <p className="text-xs text-gray-700 leading-relaxed font-medium pl-8">
                    {point_4_streak.detail}
                  </p>
                )}
              </div>

              {/* Point 5: Peer Comparison (Per Subject) */}
              <div className="bg-white p-5 rounded-3xl border border-emerald-200/60 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-xs font-extrabold">
                      5
                    </span>
                    <h3 className="text-sm font-extrabold text-[#143628]">{point_5_peer.title || "Peer Comparison"}</h3>
                  </div>
                  <Users className="w-4 h-4 text-indigo-600" />
                </div>

                <p className="text-xs text-gray-700 leading-relaxed font-medium pl-8">
                  {point_5_peer.detail || "Student attendance vs class overall average per subject:"}
                </p>

                {point_5_peer.subjects && point_5_peer.subjects.length > 0 && (
                  <div className="pl-8 space-y-2">
                    {point_5_peer.subjects.map((s, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between text-xs p-2.5 rounded-2xl bg-[#f4f8f5] border border-gray-100"
                      >
                        <span className="font-bold text-[#143628]">{s.name}</span>
                        <div className="flex items-center gap-3 text-[11px]">
                          <span className="font-bold text-[#1e4d3b]">Student: {s.student_pct}%</span>
                          <span className="text-gray-500 font-medium">Class Avg: {s.class_avg_pct}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Point 6: Reasons for Absence (No Valid / Not Valid tags!) */}
              <div className="bg-white p-5 rounded-3xl border border-emerald-200/60 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-[#e8f5e9] text-[#1e4d3b] flex items-center justify-center text-xs font-extrabold">
                      6
                    </span>
                    <h3 className="text-sm font-extrabold text-[#143628]">{point_6_reasons.title || "Reasons for Absence"}</h3>
                  </div>
                  <ShieldCheck className="w-4 h-4 text-[#1e4d3b]" />
                </div>

                <div className="pl-8 space-y-2">
                  {reasonsInfoList.map((info, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-2xl bg-[#f4f8f5] border border-gray-200 text-xs text-gray-800 font-medium"
                    >
                      {info}
                    </div>
                  ))}
                </div>
              </div>

              {/* Point 7: Attendance Summary & Mentor Action (Strictly Attendance Only, No "performance" word!) */}
              <div className="p-6 rounded-3xl dark-banner-card shadow-md space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-white/20 text-white flex items-center justify-center text-xs font-extrabold">
                      7
                    </span>
                    <h3 className="text-sm font-extrabold text-white">{point_7_summary.title || "Attendance Summary & Mentor Action"}</h3>
                  </div>
                  <Sparkles className="w-5 h-5 text-[#a3b899]" />
                </div>

                <div className="space-y-2 pt-1 text-xs text-white/90">
                  <div className="bg-white/10 p-3.5 rounded-2xl backdrop-blur-sm space-y-1">
                    <span className="text-[10px] font-bold text-[#a3b899] uppercase tracking-wider block">
                      Attendance Assessment
                    </span>
                    <p className="leading-relaxed font-medium">{point_7_summary.summary}</p>
                  </div>

                  <div className="bg-white/10 p-3.5 rounded-2xl backdrop-blur-sm space-y-1">
                    <span className="text-[10px] font-bold text-[#a3b899] uppercase tracking-wider block">
                      Recommended Action for Mentor
                    </span>
                    <p className="leading-relaxed font-medium">{point_7_summary.recommendation}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
