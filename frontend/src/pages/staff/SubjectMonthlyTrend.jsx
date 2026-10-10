import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../../api/client";
import Navbar from "../../components/Navbar";
import {
  ArrowLeft,
  Calendar,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  RefreshCw,
  BookOpen,
  Award
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
  LabelList
} from "recharts";

const SUBJECT_COLORS = [
  "#1e4d3b", // Forest Green
  "#0288d1", // Ocean Blue
  "#7b1fa2", // Deep Purple
  "#e65100", // Warm Amber
  "#2e7d32", // Leaf Green
  "#c2185b", // Crimson Rose
  "#00796b"  // Dark Teal
];

export default function SubjectMonthlyTrend() {
  const { id, subjectId } = useParams();
  const navigate = useNavigate();

  const [trendData, setTrendData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTrend = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get(`/analytics/student-profile/${id}/subject/${subjectId}`);
      setTrendData(data);
    } catch (err) {
      console.error("Failed to fetch subject monthly trend:", err);
      setError("Failed to load subject monthly attendance trend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrend();
  }, [id, subjectId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f4f8f5]">
        <Navbar />
        <div className="max-w-5xl mx-auto p-8 space-y-6">
          <div className="h-10 bg-white/60 rounded-2xl animate-pulse w-1/4"></div>
          <div className="h-32 bg-white rounded-3xl animate-pulse border border-[#1e4d3b]/10"></div>
          <div className="h-96 bg-white rounded-3xl animate-pulse border border-[#1e4d3b]/10"></div>
        </div>
      </div>
    );
  }

  if (error || !trendData) {
    return (
      <div className="min-h-screen bg-[#f4f8f5]">
        <Navbar />
        <div className="max-w-2xl mx-auto mt-16 p-8 bg-white rounded-3xl border border-red-200 text-center space-y-4 shadow-sm">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
          <h2 className="text-xl font-extrabold text-[#143628]">Data Unavailable</h2>
          <p className="text-xs text-gray-600">{error || "Subject record not found."}</p>
          <div className="flex justify-center gap-3 pt-2">
            <button
              onClick={() => navigate(`/student/${id}`)}
              className="text-xs font-bold text-gray-700 bg-gray-100 px-4 py-2.5 rounded-2xl hover:bg-gray-200"
            >
              &larr; Back to Student Profile
            </button>
            <button
              onClick={fetchTrend}
              className="text-xs font-bold text-white bg-[#1e4d3b] px-5 py-2.5 rounded-2xl hover:bg-[#143628] flex items-center gap-2"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { student, subject, cutoff = 75, monthly_data = [], best_month, worst_month, trend } = trendData;

  // Pick color based on subject_id hash
  const lineColor = SUBJECT_COLORS[((subject.id || 1) - 1) % SUBJECT_COLORS.length];

  const trendIcon =
    trend === "Improving" ? (
      <TrendingUp className="w-4 h-4 text-emerald-600" />
    ) : trend === "Declining" ? (
      <TrendingDown className="w-4 h-4 text-red-600" />
    ) : (
      <Minus className="w-4 h-4 text-amber-600" />
    );

  const trendBadgeStyle =
    trend === "Improving"
      ? "bg-emerald-100 text-emerald-800 border-emerald-300"
      : trend === "Declining"
      ? "bg-red-100 text-red-800 border-red-300"
      : "bg-amber-100 text-amber-800 border-amber-300";

  return (
    <div className="min-h-screen bg-[#f4f8f5] pb-16">
      <Navbar />

      <main className="max-w-5xl mx-auto p-4 sm:p-6 md:p-8 space-y-6">
        {/* Navigation */}
        <div>
          <button
            onClick={() => navigate(`/student/${id}`)}
            className="inline-flex items-center gap-2 text-xs font-bold text-[#1e4d3b] bg-white border border-[#1e4d3b]/20 px-4 py-2.5 rounded-2xl hover:bg-[#e8f5e9] transition-all shadow-sm"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Student Profile
          </button>
        </div>

        {/* Subject Header Card */}
        <div className="bg-white p-6 md:p-8 rounded-3xl border border-[#1e4d3b]/10 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-2xl text-white flex items-center justify-center font-extrabold text-xl shadow-md shrink-0"
              style={{ backgroundColor: lineColor }}
            >
              <BookOpen className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-extrabold text-[#143628]">{subject.name}</h1>
                {subject.code && (
                  <span className="text-xs font-bold text-gray-500 bg-gray-100 px-2.5 py-0.5 rounded-lg">
                    {subject.code}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Student: <strong className="text-gray-800">{student.name}</strong> (USN: {student.usn})
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 flex-wrap">
            <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 text-center min-w-[130px] flex-1 sm:flex-none">
              <span className="text-[10px] font-bold text-gray-500 uppercase block">Subject Overall</span>
              <span className="text-3xl font-extrabold" style={{ color: lineColor }}>
                {subject.overall_pct}%
              </span>
            </div>

            <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 text-center min-w-[130px] flex-1 sm:flex-none">
              <span className="text-[10px] font-bold text-gray-500 uppercase block">Total Classes</span>
              <span className="text-2xl font-extrabold text-[#143628]">
                {subject.attended} / {subject.total}
              </span>
            </div>
          </div>
        </div>

        {/* Month-wise Line Graph Card */}
        <div className="bg-white p-6 md:p-8 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-4">
            <div>
              <span className="text-[10px] font-extrabold text-[#1e4d3b] uppercase tracking-wider bg-[#e8f5e9] px-2.5 py-1 rounded-full">
                SEMESTER TREND ANALYSIS
              </span>
              <h2 className="text-lg font-extrabold text-[#143628] mt-1.5">
                Month-Wise Attendance Line Graph
              </h2>
            </div>
            <div className="flex items-center gap-2 text-xs font-bold text-gray-600">
              <span className="w-3 h-0.5 bg-red-500 inline-block border-t border-dashed"></span>
              <span>Mandatory Cutoff: <strong className="text-red-600">{cutoff}%</strong></span>
            </div>
          </div>

          {/* Graph area */}
          {monthly_data.length === 0 ? (
            <div className="p-12 text-center bg-[#f4f8f5] rounded-3xl border border-[#1e4d3b]/10 space-y-2">
              <Calendar className="w-10 h-10 text-gray-400 mx-auto" />
              <p className="text-sm font-bold text-gray-700">No Monthly Attendance Records</p>
              <p className="text-xs text-gray-500">
                Attendance logs for this subject have not been registered yet.
              </p>
            </div>
          ) : (
            <div className="h-80 w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={monthly_data} margin={{ top: 25, right: 35, left: -10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 12, fill: "#4b5563", fontWeight: 700 }}
                  />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#4b5563" }} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="bg-[#143628] text-white p-3 rounded-2xl shadow-xl text-xs space-y-1">
                            <p className="font-bold text-emerald-300">{data.month} Attendance</p>
                            <p>
                              Percentage: <span className="font-extrabold">{data.percentage}%</span>
                            </p>
                            <p className="text-gray-300 text-[10px]">
                              Classes: {data.attended} attended out of {data.total}
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <ReferenceLine
                    y={cutoff}
                    stroke="#d32f2f"
                    strokeDasharray="4 4"
                    label={{
                      value: `${cutoff}% Cutoff`,
                      fill: "#d32f2f",
                      position: "right",
                      fontSize: 10,
                      fontWeight: "bold"
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="percentage"
                    stroke={lineColor}
                    strokeWidth={3}
                    dot={{ r: 6, fill: lineColor, stroke: "#ffffff", strokeWidth: 2 }}
                    activeDot={{ r: 8, fill: lineColor, stroke: "#ffffff", strokeWidth: 3 }}
                  >
                    <LabelList
                      dataKey="percentage"
                      position="top"
                      formatter={(val) => `${val}%`}
                      style={{ fontSize: "11px", fontWeight: "bold", fill: lineColor }}
                    />
                  </Line>
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Under Graph Summary Row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-gray-100">
            <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 flex items-center gap-3">
              <Award className="w-8 h-8 text-emerald-600 shrink-0" />
              <div>
                <span className="text-[10px] font-bold text-gray-500 uppercase block">Best Month</span>
                <span className="text-sm font-extrabold text-[#143628]">{best_month}</span>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 flex items-center gap-3">
              <Award className="w-8 h-8 text-amber-600 shrink-0" />
              <div>
                <span className="text-[10px] font-bold text-gray-500 uppercase block">Worst Month</span>
                <span className="text-sm font-extrabold text-[#143628]">{worst_month}</span>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-gray-500 uppercase block">Overall Trend</span>
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold border mt-1 ${trendBadgeStyle}`}>
                  {trendIcon}
                  <span>{trend}</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
