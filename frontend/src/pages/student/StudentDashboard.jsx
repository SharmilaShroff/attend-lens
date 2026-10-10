import { useState, useEffect } from "react";
import api from "../../api/client";
import Navbar from "../../components/Navbar";
import Sidebar from "../../components/Sidebar";
import AIChatbotWidget from "../../components/AIChatbotWidget";
import {
  TrendingUp, TrendingDown, CheckCircle, AlertTriangle, Calculator, FileUp, Send, MessageSquare, BookOpen, Calendar
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LineChart, Line } from "recharts";

export default function StudentDashboard() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [data, setData] = useState(null);
  const [selectedSubject, setSelectedSubject] = useState(null);
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
        setSelectedSubject(dbData.subjects[0]);
      }
      if (dbData.student?.id) {
        try {
          const { data: rems } = await api.get(`/remarks/student/${dbData.student.id}`);
          setMentorRemarks(rems || []);
        } catch (e) {
          console.error("Failed to fetch mentor remarks for student:", e);
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
  }, []);

  const handleSubmitReason = async (e) => {
    e.preventDefault();
    if (!reasonText.trim()) return;
    try {
      await api.post("/student/absence-reasons", {
        subject_id: selectedSubject?.subject_id,
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

  const handleReplyCounselling = async (caseId) => {
    if (!replyText.trim()) return;
    try {
      await api.post(`/counselling/cases/${caseId}/reply`, { body: replyText });
      setReplyText("");
      loadStudentData();
    } catch (err) {
      alert("Failed to send reply");
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

  const getBarColor = (pct) => {
    if (pct >= 85) return "#1e4d3b"; // Green
    if (pct >= 75) return "#b78103"; // Amber
    return "#c62828"; // Red
  };

  return (
    <div className="min-h-screen bg-[#f4f8f5]">
      <Navbar />

      <div className="flex">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} role="student" />

        <main className="flex-1 p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
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


          {/* Mentor Feedback & Remarks Card */}
          {mentorRemarks.length > 0 && (
            <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-3">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-[#1e4d3b]" />
                <h3 className="text-base font-extrabold text-[#143628]">Mentor Feedback & Remarks</h3>
              </div>
              <div className="space-y-2.5">
                {mentorRemarks.slice(0, 3).map((rem) => (
                  <div key={rem.id} className="p-3.5 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 space-y-1 text-xs">
                    <div className="flex items-center justify-between text-[10px] text-gray-500">
                      <span className="font-bold text-[#143628]">{rem.author_name || "Mentor"}</span>
                      <span>{new Date(rem.created_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
                    </div>
                    <p className="text-gray-800 leading-relaxed font-medium">{rem.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Overall Attendance Bar Graph & Classes Needed Calculator */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

            {/* Subject Overall Attendance Bar Chart */}
            <div className="lg:col-span-7 bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-extrabold text-[#143628]">Overall Subject Breakdown</h3>
                  <p className="text-xs text-gray-500">Click any bar to view monthly trend line graph</p>
                </div>
                <div className="flex items-center gap-3 text-[10px] font-bold">
                  <span className="flex items-center gap-1 text-[#1e4d3b]"><span className="w-2.5 h-2.5 rounded-full bg-[#1e4d3b]"></span> &ge;85%</span>
                  <span className="flex items-center gap-1 text-[#b78103]"><span className="w-2.5 h-2.5 rounded-full bg-[#b78103]"></span> 75-85%</span>
                  <span className="flex items-center gap-1 text-[#c62828]"><span className="w-2.5 h-2.5 rounded-full bg-[#c62828]"></span> &lt;75%</span>
                </div>
              </div>

              <div className="h-64 w-full pt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={subjects} onClick={(e) => { if (e && e.activePayload) setSelectedSubject(e.activePayload[0].payload); }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                    <XAxis dataKey="subject_code" tick={{ fontSize: 11, fontWeight: 700 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                    <Tooltip
                      formatter={(val) => [`${val}%`, "Attendance"]}
                      contentStyle={{ borderRadius: "1rem", borderColor: "#1e4d3b" }}
                    />
                    <Bar
                      dataKey="percentage"
                      radius={[12, 12, 0, 0]}
                      fill="#1e4d3b"
                      onClick={(data) => setSelectedSubject(data)}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* "Classes Needed" Calculator Card */}
            <div className="lg:col-span-5 bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Calculator className="w-5 h-5 text-[#1e4d3b]" />
                  <h3 className="text-base font-extrabold text-[#143628]">Classes Needed Calculator</h3>
                </div>
                <p className="text-xs text-gray-500 mb-4">
                  Calculated based on formula: <code className="bg-[#f4f8f5] px-1.5 py-0.5 rounded text-[10px]">x = ceil((t*total - attended)/(1 - t))</code>
                </p>

                {selectedSubject && (
                  <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 space-y-3">
                    <div className="flex items-center justify-between border-b border-gray-200 pb-2">
                      <span className="text-xs font-bold text-[#143628]">{selectedSubject.subject_name}</span>
                      <span className="text-xs font-bold text-[#1e4d3b]">{selectedSubject.percentage}%</span>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 rounded-xl bg-white border border-gray-200 text-center">
                        <span className="text-[10px] font-bold text-gray-500 block uppercase">Classes Needed</span>
                        <span className="text-xl font-extrabold text-amber-700">{selectedSubject.classes_needed}</span>
                        <span className="text-[9px] text-gray-400 block mt-0.5">Consecutive attend</span>
                      </div>

                      <div className="p-3 rounded-xl bg-white border border-gray-200 text-center">
                        <span className="text-[10px] font-bold text-gray-500 block uppercase">Safe Misses</span>
                        <span className="text-xl font-extrabold text-[#1e4d3b]">{selectedSubject.safe_misses}</span>
                        <span className="text-[9px] text-gray-400 block mt-0.5">Available to skip</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="text-[11px] text-gray-500 bg-[#e8f5e9]/60 p-3 rounded-2xl border border-[#1e4d3b]/10">
                💡 Maintain at least <strong>{student.threshold}%</strong> attendance to qualify for semester final exams.
              </div>
            </div>
          </div>

          {/* Month-Wise Subject Line Graph */}
          {selectedSubject && selectedSubject.monthly_trend?.length > 0 && (
            <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
              <h3 className="text-base font-extrabold text-[#143628]">
                Month-Wise Attendance Trend: {selectedSubject.subject_name} ({selectedSubject.subject_code})
              </h3>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={selectedSubject.monthly_trend}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(val) => [`${val}%`, "Attendance"]} />
                    <Line type="monotone" dataKey="percentage" stroke="#1e4d3b" strokeWidth={3} dot={{ r: 5 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Day-Wise Absence Reason Submission & History */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-5 bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
              <h3 className="text-base font-extrabold text-[#143628]">Submit Absence Reason</h3>
              {submitMsg && <div className="p-3 rounded-xl bg-emerald-50 text-emerald-800 text-xs font-bold">{submitMsg}</div>}
              <form onSubmit={handleSubmitReason} className="space-y-3">
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
              <div className="space-y-2 overflow-y-auto max-h-[360px]">
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
          {counsellingCases.length > 0 && (
            <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-[#1e4d3b]" />
                <h3 className="text-base font-extrabold text-[#143628]">AI Counselling Inbox</h3>
              </div>

              {counsellingCases.map((c) => (
                <div key={c.id} className="p-5 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 space-y-4">
                  <div className="flex items-center justify-between border-b border-gray-200 pb-2">
                    <span className="text-xs font-bold text-[#143628]">Thread Status: {c.status}</span>
                    <span className="text-[10px] text-gray-500">Ref: {c.thread_token}</span>
                  </div>

                  <div className="space-y-3">
                    {c.messages?.map((m) => (
                      <div key={m.id} className={`p-3.5 rounded-2xl text-xs ${m.sender === "student" ? "bg-[#1e4d3b] text-white ml-8" : "bg-white text-gray-800 border border-gray-200 mr-8"}`}>
                        <div className="font-bold text-[10px] opacity-75 mb-1">{m.sender.toUpperCase()} ({m.channel})</div>
                        <div>{m.body}</div>
                      </div>
                    ))}
                  </div>

                  <div className="flex gap-2 pt-2">
                    <input
                      type="text"
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      placeholder="Type your response to the counselling team..."
                      className="flex-1 text-xs p-3 rounded-xl bg-white border border-gray-200 outline-none"
                    />
                    <button
                      onClick={() => handleReplyCounselling(c.id)}
                      className="bg-[#1e4d3b] text-white text-xs font-bold px-5 py-3 rounded-xl"
                    >
                      Reply
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

        </main>
      </div>

      {/* Student Floating Grounded AI Chatbot */}
      <AIChatbotWidget />
    </div>
  );
}
