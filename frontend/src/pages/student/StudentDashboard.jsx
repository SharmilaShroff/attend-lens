import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api/client";
import Navbar from "../../components/Navbar";
import AIChatbotWidget from "../../components/AIChatbotWidget";
import {
  TrendingUp, TrendingDown, Calculator, MessageSquare, BookOpen, Sparkles, Send, RefreshCw, ShieldAlert
} from "lucide-react";
import {
  BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine, LabelList
} from "recharts";

const SUBJECT_BAR_COLORS = [
  "#1e4d3b", // Deep Forest Green
  "#2563eb", // Royal Blue
  "#d97706", // Warm Amber
  "#7c3aed", // Violet
  "#059669", // Emerald Green
  "#dc2626", // Crimson Red
  "#0891b2", // Cyan / Teal
  "#c026d3", // Magenta
];

export default function StudentDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState(null);
  const [reasons, setReasons] = useState([]);
  const [counsellingCases, setCounsellingCases] = useState([]);
  const [replyText, setReplyText] = useState("");
  const [loading, setLoading] = useState(true);

  // Absence Reason Form
  const [reasonDate, setReasonDate] = useState(new Date().toISOString().split("T")[0]);
  const [reasonCategory, setReasonCategory] = useState("medical");
  const [reasonText, setReasonText] = useState("");
  const [proofFile, setProofFile] = useState(null);
  const [submitMsg, setSubmitMsg] = useState("");

  const [mentorRemarks, setMentorRemarks] = useState([]);

  const loadStudentData = async () => {
    setLoading(true);
    try {
      const [{ data: dbData }, { data: rs }, { data: cs }] = await Promise.all([
        api.get("/student/dashboard-data"),
        api.get("/student/absence-reasons"),
        api.get("/student/counselling-cases")
      ]);
      setData(dbData);
      setReasons(rs);
      setCounsellingCases(cs);
      if (dbData.subjects && dbData.subjects.length > 0) {
        setSelectedSubjectId(dbData.subjects[0].subject_id);
      }
      if (dbData.student?.id) {
        try {
          const { data: rems } = await api.get(`/remarks/student/${dbData.student.id}`);
          const validRemarks = (rems || []).filter(
            (r) => (!r.text || !r.text.includes("Counselling Summary"))
          );
          setMentorRemarks(validRemarks);
        } catch (e) {
          try {
            const { data: rems } = await api.get("/remarks/my-remarks");
            setMentorRemarks(rems || []);
          } catch (err) {
            console.error("Failed to fetch mentor remarks for student:", err);
          }
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStudentData();
    const interval = setInterval(() => {
      loadStudentData();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmitReason = async (e) => {
    e.preventDefault();
    if (!reasonText.trim()) return;
    try {
      await api.post("/student/absence-reasons", {
        subject_id: selectedSubjectId,
        date: reasonDate,
        category: reasonCategory,
        reason: reasonText,
        proof_path: proofFile ? proofFile.name : null
      });
      setSubmitMsg("Absence reason submitted for staff review!");
      setReasonText("");
      loadStudentData();
    } catch (err) {
      alert("Failed to submit absence reason");
    }
  };

  const [sendingReply, setSendingReply] = useState(false);

  const handleReplyCounselling = async (caseId) => {
    if (!replyText.trim() || sendingReply) return;
    setSendingReply(true);
    try {
      await api.post(`/counselling/cases/${caseId}/reply`, { body: replyText.trim() });
      setReplyText("");
      await loadStudentData();
    } catch (err) {
      alert("Failed to send reply");
    } finally {
      setSendingReply(false);
    }
  };

  const handleStartCheckIn = async () => {
    try {
      await api.post("/student/absence-reasons", {
        subject_id: selectedSubjectId,
        date: new Date().toISOString().split("T")[0],
        category: "personal",
        reason: "Requesting academic and attendance guidance from the AI counselling team."
      });
      await loadStudentData();
    } catch (err) {
      alert("Failed to initiate counselling check-in");
    }
  };

  if (loading || !data) {
    return (
      <div className="min-h-screen bg-[#f4f8f5] flex items-center justify-center text-[#143628] font-bold text-sm">
        Loading Student Dashboard...
      </div>
    );
  }

  const { student, subjects } = data;
  const threshold = student.threshold || 75;

  return (
    <div className="min-h-screen bg-[#f4f8f5]">
      <Navbar />

      <main className="w-full max-w-7xl mx-auto p-6 md:p-8 space-y-6">
        {/* Header Card */}
        <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="text-[10px] font-bold text-[#1e4d3b] uppercase tracking-wider bg-[#e8f5e9] px-3 py-1 rounded-full">
              STUDENT PROGRESS DASHBOARD
            </span>
            <h1 className="text-2xl font-extrabold text-[#143628] mt-2">
              Welcome back, {student.name}!
            </h1>
            <p className="text-xs text-gray-500">USN: {student.usn} | Target Threshold: {student.threshold}%</p>
          </div>

          <div className="flex items-center gap-4">
            {/* Overall Percentage Stat */}
            <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 flex items-center gap-3">
              <div className="text-center">
                <span className="text-[10px] font-bold text-gray-500 uppercase block">Overall Attendance</span>
                <span className="text-2xl font-extrabold text-[#143628]">{student.overall_pct}%</span>
              </div>
            </div>

            {/* Weekly Improvement Trend Indicator */}
            <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 flex items-center gap-2">
              {student.trend_arrow === "up" ? (
                <TrendingUp className="w-6 h-6 text-emerald-600" />
              ) : (
                <TrendingDown className="w-6 h-6 text-red-500" />
              )}
              <div>
                <span className="text-[10px] font-bold text-gray-500 uppercase block">Weekly Trend</span>
                <span className={`text-xs font-extrabold ${student.weekly_change >= 0 ? "text-emerald-700" : "text-red-700"}`}>
                  {student.weekly_change >= 0 ? `+${student.weekly_change}%` : `${student.weekly_change}%`}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Mentor Remarks Card */}
        <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-3">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-[#1e4d3b]" />
            <h3 className="text-base font-extrabold text-[#143628]">Mentor Remarks</h3>
          </div>
          {mentorRemarks.length > 0 ? (
            <div className="space-y-2.5 max-h-[160px] overflow-y-auto pr-1">
              {mentorRemarks.map((rem) => (
                <div key={rem.id} className="p-3.5 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 space-y-1 text-xs">
                  <div className="flex items-center justify-between text-[10px] text-gray-500">
                    <span className="font-bold text-[#143628]">{rem.author_name || "Mentor"}</span>
                    <span>{new Date(rem.created_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
                  </div>
                  <p className="text-gray-800 leading-relaxed font-medium">{rem.text}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 text-xs text-gray-500 font-medium text-center">
              No remarks yet.
            </div>
          )}
        </div>

        {/* Overall Attendance Bar Graph & Classes Needed Calculator */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* Subject Overall Attendance Bar Chart */}
          <div className="lg:col-span-7 bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
            <div>
              <h3 className="text-base font-extrabold text-[#143628]">Overall Subject Breakdown</h3>
              <p className="text-xs text-gray-500">Attendance percentage by subject</p>
            </div>

            <div className="h-72 w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={subjects} margin={{ top: 20, right: 20, left: -10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis
                    dataKey="subject_code"
                    tick={{ fontSize: 11, fontWeight: 700, fill: "#143628" }}
                    interval={0}
                  />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(val) => [`${val}%`, "Attendance"]}
                    contentStyle={{ borderRadius: "1rem", borderColor: "#1e4d3b" }}
                  />
                  <ReferenceLine
                    y={threshold}
                    stroke="#c62828"
                    strokeDasharray="3 3"
                    label={{ value: `${threshold}% Cutoff`, fill: "#c62828", fontSize: 10, position: "right" }}
                  />
                  <Bar dataKey="percentage" radius={[10, 10, 0, 0]}>
                    {subjects.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={SUBJECT_BAR_COLORS[index % SUBJECT_BAR_COLORS.length]} />
                    ))}
                    <LabelList
                      dataKey="percentage"
                      position="top"
                      formatter={(val) => `${val}%`}
                      style={{ fontSize: 11, fontWeight: 700, fill: "#143628" }}
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Subject Buttons directly below the graph */}
            <div className="pt-3 border-t border-gray-100 space-y-1.5">
              <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block">
                View Subject Attendance Records
              </span>
              <div className="flex flex-wrap gap-2">
                {subjects.map((subj) => (
                  <button
                    key={subj.subject_id}
                    onClick={() => navigate(`/student/subject/${subj.subject_id}`)}
                    className="bg-[#f4f8f5] text-[#143628] hover:bg-[#e8f5e9] border border-[#1e4d3b]/20 px-3.5 py-2 rounded-2xl text-xs font-bold transition-all shadow-sm flex items-center gap-1.5"
                  >
                    <BookOpen className="w-3.5 h-3.5 text-[#1e4d3b]" />
                    <span>{subj.subject_name}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* "Classes Needed" Calculator Card */}
          <div className="lg:col-span-5 bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Calculator className="w-5 h-5 text-[#1e4d3b]" />
                <h3 className="text-base font-extrabold text-[#143628]">Classes Needed Calculator</h3>
              </div>

              <div className="space-y-3 overflow-y-auto max-h-[340px] pr-1">
                {subjects.map((subj) => {
                  const total = subj.total || 0;
                  const attended = subj.attended || 0;
                  const pct = subj.percentage ?? (total > 0 ? Math.round((attended / total) * 100) : 0);

                  let safeMisses = 0;
                  let classesNeeded = 0;

                  if (total > 0) {
                    if (pct >= threshold) {
                      safeMisses = Math.max(0, Math.floor((100 * attended - threshold * total) / threshold));
                      classesNeeded = 0;
                    } else {
                      safeMisses = 0;
                      classesNeeded = Math.max(0, Math.ceil((threshold * total - 100 * attended) / (100 - threshold)));
                    }
                  }

                  const isSafe = pct >= threshold;

                  return (
                    <div key={subj.subject_id} className="p-3.5 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-[#143628]">{subj.subject_name} ({subj.subject_code})</span>
                        <span className={`text-xs font-extrabold ${isSafe ? "text-[#1e4d3b]" : "text-red-600"}`}>
                          {pct}%
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-center text-xs">
                        <div className="p-2 rounded-xl bg-white border border-gray-200">
                          <span className="text-[9px] font-bold text-gray-500 block uppercase">Classes safe to miss</span>
                          <span className={`text-sm font-extrabold ${safeMisses > 0 ? "text-[#1e4d3b]" : "text-gray-400"}`}>
                            {safeMisses}
                          </span>
                        </div>
                        <div className="p-2 rounded-xl bg-white border border-gray-200">
                          <span className="text-[9px] font-bold text-gray-500 block uppercase">Classes needed to attend</span>
                          <span className={`text-sm font-extrabold ${classesNeeded > 0 ? "text-amber-700" : "text-gray-400"}`}>
                            {classesNeeded}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="text-[11px] text-gray-500 bg-[#e8f5e9]/60 p-3 rounded-2xl border border-[#1e4d3b]/10">
              💡 Maintain at least <strong>{threshold}%</strong> attendance to qualify for semester final exams.
            </div>
          </div>
        </div>

        {/* Day-Wise Absence Reason Submission & History */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-5 bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
            <h3 className="text-base font-extrabold text-[#143628]">Submit Absence Reason</h3>
            {submitMsg && <div className="p-3 rounded-xl bg-emerald-50 text-emerald-800 text-xs font-bold">{submitMsg}</div>}
            <form onSubmit={handleSubmitReason} className="space-y-3">
              <div>
                <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Subject (Optional)</label>
                <select
                  value={selectedSubjectId || ""}
                  onChange={(e) => setSelectedSubjectId(Number(e.target.value))}
                  className="w-full text-xs p-3 rounded-xl bg-[#f4f8f5] outline-none"
                >
                  {subjects.map((s) => (
                    <option key={s.subject_id} value={s.subject_id}>
                      {s.subject_name} ({s.subject_code})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Absence Date</label>
                <input
                  type="date"
                  required
                  value={reasonDate}
                  onChange={(e) => setReasonDate(e.target.value)}
                  className="w-full text-xs p-3 rounded-xl bg-[#f4f8f5] outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Category</label>
                <select
                  value={reasonCategory}
                  onChange={(e) => setReasonCategory(e.target.value)}
                  className="w-full text-xs p-3 rounded-xl bg-[#f4f8f5] outline-none"
                >
                  <option value="medical">Medical Reasons</option>
                  <option value="event">College Event / Competition</option>
                  <option value="personal">Personal / Family Emergency</option>
                </select>
              </div>
              <div>
                <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Detailed Reason</label>
                <textarea
                  rows="3"
                  required
                  value={reasonText}
                  onChange={(e) => setReasonText(e.target.value)}
                  placeholder="Provide details for staff review..."
                  className="w-full text-xs p-3 rounded-xl bg-[#f4f8f5] outline-none"
                ></textarea>
              </div>
              <div>
                <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Proof Upload (Optional)</label>
                <input
                  type="file"
                  onChange={(e) => setProofFile(e.target.files[0])}
                  className="w-full text-xs p-2 rounded-xl bg-[#f4f8f5] outline-none"
                />
              </div>
              <button
                type="submit"
                className="w-full bg-[#1e4d3b] text-white text-xs font-bold py-3 rounded-xl hover:bg-[#143628]"
              >
                Submit Reason for Review
              </button>
            </form>
          </div>

          <div className="lg:col-span-7 bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
            <h3 className="text-base font-extrabold text-[#143628]">Submitted Reason History</h3>
            <div className="space-y-2 overflow-y-auto max-h-[400px]">
              {reasons.map((r) => (
                <div key={r.id} className="p-4 rounded-2xl bg-[#f4f8f5] border border-gray-200 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#143628]">{r.date} ({r.category})</span>
                    <span className={`pill-badge ${r.status === "approved" ? "pill-badge-green" : r.status === "rejected" ? "pill-badge-red" : "pill-badge-amber"}`}>
                      {r.status}
                    </span>
                  </div>
                  <p className="text-gray-700">{r.reason}</p>
                  {r.proof_path && <span className="text-[10px] text-gray-400 block">Proof: {r.proof_path}</span>}
                </div>
              ))}
              {reasons.length === 0 && <div className="text-xs text-gray-400 text-center py-8">No absence reasons submitted yet.</div>}
            </div>
          </div>
        </div>

        {/* AI Counselling Inbox */}
        <div id="counselling" className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-[#1e4d3b]" />
              <h3 className="text-base font-extrabold text-[#143628]">AI Counselling Inbox</h3>
            </div>
            <span className="text-[10px] font-bold text-emerald-800 bg-[#e8f5e9] px-3 py-1 rounded-full border border-emerald-300 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" /> ML Pattern Engine Active
            </span>
          </div>

          {counsellingCases.length > 0 ? (
            counsellingCases.map((c) => (
              <div key={c.id} className="p-5 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 space-y-4">
                <div className="flex items-center justify-between border-b border-gray-200 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[#143628]">Thread Status: {c.status}</span>
                    <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                      c.status === "responded" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                    }`}>
                      {c.status.toUpperCase()}
                    </span>
                  </div>
                  <span className="text-[10px] text-gray-500">Ref: {c.thread_token}</span>
                </div>

                {/* Conversation Thread Stream */}
                <div className="space-y-3">
                  {c.messages?.map((m) => {
                    const isStudent = m.sender === "student";
                    const isAi = m.sender === "ai";
                    return (
                      <div
                        key={m.id}
                        className={`p-4 rounded-2xl text-xs space-y-1 ${
                          isStudent
                            ? "bg-[#1e4d3b] text-white ml-8 shadow-sm"
                            : "bg-white text-gray-800 border border-gray-200 mr-8 shadow-sm"
                        }`}
                      >
                        <div className="flex items-center justify-between text-[10px] opacity-80 font-bold mb-1">
                          <span className="flex items-center gap-1">
                            {isAi && <Sparkles className="w-3 h-3 text-[#1e4d3b]" />}
                            {isStudent ? "YOU (STUDENT)" : isAi ? "AI COUNSELLOR (ML POWERED)" : "MENTOR / STAFF"}
                          </span>
                          <span>{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                        </div>
                        <div className="whitespace-pre-line leading-relaxed font-medium">{m.body}</div>
                      </div>
                    );
                  })}
                </div>

                {/* Interactive Reply Input with Real-time ML Inference */}
                <div className="flex gap-2 pt-2">
                  <input
                    type="text"
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleReplyCounselling(c.id);
                      }
                    }}
                    placeholder="Type a response to the counselling team (e.g. explain your situation, request help)..."
                    disabled={sendingReply}
                    className="flex-1 text-xs p-3.5 rounded-2xl bg-white border border-gray-200 outline-none focus:border-[#1e4d3b] focus:ring-1 focus:ring-[#1e4d3b]"
                  />
                  <button
                    onClick={() => handleReplyCounselling(c.id)}
                    disabled={sendingReply || !replyText.trim()}
                    className="bg-[#1e4d3b] text-white text-xs font-bold px-5 py-3 rounded-2xl hover:bg-[#143628] transition-all flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                  >
                    {sendingReply ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Analyzing...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-3.5 h-3.5" />
                        <span>Reply</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 text-center space-y-3">
              <p className="text-xs text-gray-600 font-medium">
                No active counselling alerts. Your attendance is currently healthy or no open cases are queued.
              </p>
              <button
                onClick={handleStartCheckIn}
                className="bg-[#1e4d3b] text-white text-xs font-bold px-5 py-2.5 rounded-2xl hover:bg-[#143628] transition-all inline-flex items-center gap-2 shadow-sm"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Start Proactive AI Counselling Check-in</span>
              </button>
            </div>
          )}
        </div>

      </main>

      {/* Student Floating Grounded AI Chatbot */}
      <AIChatbotWidget />
    </div>
  );
}
