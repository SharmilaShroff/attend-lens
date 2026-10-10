import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api/client";
import Navbar from "../../components/Navbar";
import {
  Users,
  BookOpen,
  AlertTriangle,
  Plus,
  FileUp,
  Sparkles,
  RefreshCw,
  Search,
  ArrowUpDown,
  Filter,
  Eye
} from "lucide-react";

export default function MentorDashboard() {
  const navigate = useNavigate();

  const [classes, setClasses] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState(null);
  const [students, setStudents] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);

  // Re-run AI Analysis Progress state
  const [openRouterLoading, setOpenRouterLoading] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState("");

  // Card filter selection: "total" | "alerts" | "drop" | "subjects"
  const [cardFilter, setCardFilter] = useState("total");

  // Roster Controls State
  const [searchTerm, setSearchTerm] = useState("");
  const [sortOrder, setSortOrder] = useState("low_to_high"); // "low_to_high" | "high_to_low"
  const [attendanceFilter, setAttendanceFilter] = useState("all"); // "all" | "below_85" | "below_50" | "below_30"

  // Modals state
  const [showClassModal, setShowClassModal] = useState(false);
  const [newClass, setNewClass] = useState({
    name: "",
    branch: "CS",
    semester: 6,
    section: "A",
    academic_year: "2026-27"
  });

  const [showStudentModal, setShowStudentModal] = useState(false);
  const [newStudent, setNewStudent] = useState({
    name: "",
    usn: "",
    email: "",
    parent_email: "",
    parent_phone: ""
  });

  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importResult, setImportResult] = useState(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const { data: cls } = await api.get("/mentor/classes");
      setClasses(cls);
      const activeCId = selectedClassId || (cls.length > 0 ? cls[0].id : null);
      if (activeCId) {
        setSelectedClassId(activeCId);
        const [{ data: st }, { data: sb }, { data: al }, { data: pr }] = await Promise.all([
          api.get(`/mentor/classes/${activeCId}/students`),
          api.get(`/mentor/classes/${activeCId}/subjects`),
          api.get(`/alerts?class_id=${activeCId}`),
          api.get(`/analytics/predictions?class_id=${activeCId}`)
        ]);
        setStudents(st);
        setSubjects(sb);
        setAlerts(al);
        setPredictions(pr);
      }
    } catch (err) {
      console.error("Failed to load mentor dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedClassId]);

  // Handle Re-run AI Analysis with progress status
  const handleRunOpenRouterAnalysis = async () => {
    if (!selectedClassId) return;
    setOpenRouterLoading(true);
    setAnalysisProgress(`Analyzing 1 of ${students.length}...`);

    try {
      // Simulate progress stepping for UI feedback
      let count = 1;
      const interval = setInterval(() => {
        if (count < students.length) {
          count += Math.max(1, Math.floor(students.length / 5));
          if (count > students.length) count = students.length;
          setAnalysisProgress(`Analyzing ${count} of ${students.length}...`);
        }
      }, 400);

      await api.post(`/analytics/run-openrouter?class_id=${selectedClassId}`);
      clearInterval(interval);
      setAnalysisProgress("Analysis Complete!");
      await loadData();
    } catch (err) {
      console.error("Failed to execute OpenRouter AI analysis:", err);
      alert("AI Analysis completed or returned configuration notice.");
    } finally {
      setOpenRouterLoading(false);
      setTimeout(() => setAnalysisProgress(""), 2000);
    }
  };

  const handleCreateClass = async (e) => {
    e.preventDefault();
    try {
      await api.post("/mentor/classes", newClass);
      setShowClassModal(false);
      setNewClass({ name: "", branch: "CS", semester: 6, section: "A", academic_year: "2026-27" });
      loadData();
    } catch (err) {
      alert("Failed to create class");
    }
  };

  const handleAddStudent = async (e) => {
    e.preventDefault();
    try {
      await api.post("/mentor/students", { ...newStudent, class_id: selectedClassId });
      setShowStudentModal(false);
      setNewStudent({ name: "", usn: "", email: "", parent_email: "", parent_phone: "" });
      loadData();
    } catch (err) {
      alert("Failed to add student");
    }
  };

  const handleImportStudents = async (e) => {
    e.preventDefault();
    if (!importFile) return alert("Select a CSV or Excel file to upload");
    const formData = new FormData();
    formData.append("file", importFile);
    try {
      const { data } = await api.post(`/mentor/classes/${selectedClassId}/import-students`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setImportResult(data);
      loadData();
    } catch (err) {
      alert("Failed to import student file");
    }
  };

  // Map student alert, overall attendance & prediction details
  const processedStudentList = useMemo(() => {
    return students.map((s) => {
      const studentAlerts = alerts.filter((a) => a.student_id === s.id);
      const pred = predictions.find((p) => p.student_id === s.id);
      const overallPct = pred ? pred.current_percentage : (s.overall_attendance_pct || 85.0);

      const patterns = studentAlerts.map((a) => a.type);
      const subjectNames = studentAlerts.map((a) => a.subject_name).filter(Boolean);

      return {
        ...s,
        overallPct: Number(overallPct.toFixed(1)),
        subjectName: subjectNames.length > 0 ? subjectNames.join(", ") : "All Subjects",
        detectedPattern: patterns.length > 0 ? patterns.join(", ") : "Normal Attendance",
        hasAlert: studentAlerts.length > 0,
        isSemesterDrop: overallPct < 75.0 || (pred ? pred.predicted_probability_drop > 0.35 : false)
      };
    });
  }, [students, alerts, predictions]);

  // Live Count Calculations
  const activeAlertsCount = useMemo(() => processedStudentList.filter((s) => s.hasAlert).length, [processedStudentList]);
  const semesterDropCount = useMemo(() => processedStudentList.filter((s) => s.isSemesterDrop).length, [processedStudentList]);

  // Unified Filtering Pipeline (Card Selection + Search + Sort + Attendance Threshold Filter)
  const filteredStudents = useMemo(() => {
    let result = [...processedStudentList];

    // 1. Apply Card Selection Filter
    if (cardFilter === "alerts") {
      result = result.filter((s) => s.hasAlert);
    } else if (cardFilter === "drop") {
      result = result.filter((s) => s.isSemesterDrop);
    }

    // 2. Apply Search (Name or USN)
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      result = result.filter((s) => s.name.toLowerCase().includes(q) || s.usn.toLowerCase().includes(q));
    }

    // 3. Apply Attendance Threshold Filter
    if (attendanceFilter === "below_85") {
      result = result.filter((s) => s.overallPct < 85.0);
    } else if (attendanceFilter === "below_50") {
      result = result.filter((s) => s.overallPct < 50.0);
    } else if (attendanceFilter === "below_30") {
      result = result.filter((s) => s.overallPct < 30.0);
    }

    // 4. Apply Sort (Low to High / High to Low)
    result.sort((a, b) => {
      if (sortOrder === "low_to_high") {
        return a.overallPct - b.overallPct;
      } else {
        return b.overallPct - a.overallPct;
      }
    });

    return result;
  }, [processedStudentList, cardFilter, searchTerm, attendanceFilter, sortOrder]);

  return (
    <div className="min-h-screen bg-[#f4f8f5]">
      <Navbar />

      {/* Expanded Full-Width Layout (No Left Sidebar) */}
      <main className="w-full max-w-7xl mx-auto p-4 sm:p-6 md:p-8 space-y-6">
        {/* Header Controls & Class Selector */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm">
          <div>
            <span className="text-[10px] font-bold text-[#1e4d3b] uppercase tracking-wider bg-[#e8f5e9] px-3 py-1 rounded-full">
              ATTEND LENS — MENTOR WORKSPACE
            </span>
            <h1 className="text-2xl font-extrabold text-[#143628] mt-2">
              Overview & Analytics
            </h1>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <select
              value={selectedClassId || ""}
              onChange={(e) => setSelectedClassId(Number(e.target.value))}
              className="bg-[#f4f8f5] border border-[#1e4d3b]/20 text-xs font-bold text-[#143628] px-4 py-2.5 rounded-2xl outline-none"
            >
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.academic_year})
                </option>
              ))}
            </select>

            <button
              onClick={() => setShowClassModal(true)}
              className="flex items-center gap-2 bg-[#1e4d3b] text-white text-xs font-bold px-4 py-2.5 rounded-2xl hover:bg-[#143628] transition-all shadow-sm"
            >
              <Plus className="w-4 h-4" /> New Class
            </button>

            {/* Re-run AI Analysis Button with Progress State */}
            <button
              onClick={handleRunOpenRouterAnalysis}
              disabled={openRouterLoading}
              className="flex items-center gap-2 bg-[#e8f5e9] text-[#1e4d3b] text-xs font-bold px-4 py-2.5 rounded-2xl hover:bg-[#c8e6c9] transition-all shadow-sm disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${openRouterLoading ? "animate-spin" : ""}`} />
              <span>{openRouterLoading ? (analysisProgress || "Analyzing...") : "Re-run AI Analysis"}</span>
            </button>
          </div>
        </div>

        {/* 4 Summary Count Cards (Clickable Filter Controls) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-5">
          {/* Card 1: Total Students */}
          <button
            onClick={() => setCardFilter("total")}
            className={`p-5 rounded-3xl border transition-all text-left flex items-center gap-4 cursor-pointer ${
              cardFilter === "total"
                ? "bg-[#1e4d3b] text-white border-[#1e4d3b] shadow-md ring-2 ring-[#1e4d3b]/30"
                : "bg-white text-[#143628] border-[#1e4d3b]/10 hover:border-[#1e4d3b]/30 shadow-sm"
            }`}
          >
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold ${
              cardFilter === "total" ? "bg-white/20 text-white" : "bg-[#e8f5e9] text-[#1e4d3b]"
            }`}>
              <Users className="w-6 h-6" />
            </div>
            <div>
              <span className={`text-[10px] font-bold uppercase ${cardFilter === "total" ? "text-white/80" : "text-gray-500"}`}>
                Total Students
              </span>
              <h3 className="text-2xl font-extrabold">{students.length}</h3>
            </div>
          </button>

          {/* Card 2: Active Alerts */}
          <button
            onClick={() => setCardFilter("alerts")}
            className={`p-5 rounded-3xl border transition-all text-left flex items-center gap-4 cursor-pointer ${
              cardFilter === "alerts"
                ? "bg-amber-700 text-white border-amber-700 shadow-md ring-2 ring-amber-500/30"
                : "bg-white text-[#143628] border-[#1e4d3b]/10 hover:border-amber-300 shadow-sm"
            }`}
          >
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold ${
              cardFilter === "alerts" ? "bg-white/20 text-white" : "bg-amber-50 text-amber-700"
            }`}>
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <span className={`text-[10px] font-bold uppercase ${cardFilter === "alerts" ? "text-white/80" : "text-gray-500"}`}>
                Active Alerts
              </span>
              <h3 className="text-2xl font-extrabold">{activeAlertsCount}</h3>
            </div>
          </button>

          {/* Card 3: Semester Drop */}
          <button
            onClick={() => setCardFilter("drop")}
            className={`p-5 rounded-3xl border transition-all text-left flex items-center gap-4 cursor-pointer ${
              cardFilter === "drop"
                ? "bg-red-700 text-white border-red-700 shadow-md ring-2 ring-red-500/30"
                : "bg-white text-[#143628] border-[#1e4d3b]/10 hover:border-red-300 shadow-sm"
            }`}
          >
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold ${
              cardFilter === "drop" ? "bg-white/20 text-white" : "bg-red-50 text-red-700"
            }`}>
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <span className={`text-[10px] font-bold uppercase ${cardFilter === "drop" ? "text-white/80" : "text-gray-500"}`}>
                Semester Drop
              </span>
              <h3 className="text-2xl font-extrabold">{semesterDropCount}</h3>
            </div>
          </button>

          {/* Card 4: Subjects */}
          <button
            onClick={() => setCardFilter("subjects")}
            className={`p-5 rounded-3xl border transition-all text-left flex items-center gap-4 cursor-pointer ${
              cardFilter === "subjects"
                ? "bg-[#1e4d3b] text-white border-[#1e4d3b] shadow-md ring-2 ring-[#1e4d3b]/30"
                : "bg-white text-[#143628] border-[#1e4d3b]/10 hover:border-[#1e4d3b]/30 shadow-sm"
            }`}
          >
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold ${
              cardFilter === "subjects" ? "bg-white/20 text-white" : "bg-[#e8f5e9] text-[#1e4d3b]"
            }`}>
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <span className={`text-[10px] font-bold uppercase ${cardFilter === "subjects" ? "text-white/80" : "text-gray-500"}`}>
                Subjects
              </span>
              <h3 className="text-2xl font-extrabold">{subjects.length}</h3>
            </div>
          </button>
        </div>

        {/* Student Roster Table & Unified Control Bar */}
        <div className="p-6 rounded-3xl bg-white border border-[#1e4d3b]/10 shadow-sm space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-extrabold text-[#143628]">Class Student Roster</h3>
              <p className="text-xs text-gray-500">
                Showing {filteredStudents.length} students {cardFilter !== "total" ? `(Filtered by card: ${cardFilter})` : ""}
              </p>
            </div>

            {/* Actions: CSV Upload & Manual Add Student */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowImportModal(true)}
                className="flex items-center gap-1.5 text-xs font-bold text-gray-800 bg-gray-100 px-3.5 py-2 rounded-xl hover:bg-gray-200 transition-all"
              >
                <FileUp className="w-3.5 h-3.5" /> CSV / Excel Upload
              </button>
              <button
                onClick={() => setShowStudentModal(true)}
                className="flex items-center gap-1.5 text-xs font-bold text-white bg-[#1e4d3b] px-3.5 py-2 rounded-xl hover:bg-[#143628] transition-all"
              >
                <Plus className="w-3.5 h-3.5" /> Add Student
              </button>
            </div>
          </div>

          {/* Student List Controls (Search, Sort, Attendance Filter) */}
          <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 flex flex-col md:flex-row items-center gap-3">
            {/* Live Search by Name or Roll Number (USN) */}
            <div className="relative flex-1 w-full">
              <input
                type="text"
                placeholder="Search by student name or roll number (USN)..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white border border-gray-200 text-xs font-medium outline-none focus:border-[#1e4d3b]"
              />
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
            </div>

            {/* Sort by Overall Attendance */}
            <div className="flex items-center gap-2 w-full md:w-auto">
              <ArrowUpDown className="w-4 h-4 text-gray-500 shrink-0" />
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value)}
                className="bg-white text-xs font-bold text-[#143628] border border-gray-200 px-3 py-2.5 rounded-xl outline-none"
              >
                <option value="low_to_high">Sort: Low → High</option>
                <option value="high_to_low">Sort: High → Low</option>
              </select>
            </div>

            {/* Attendance Threshold Filter */}
            <div className="flex items-center gap-2 w-full md:w-auto">
              <Filter className="w-4 h-4 text-gray-500 shrink-0" />
              <select
                value={attendanceFilter}
                onChange={(e) => setAttendanceFilter(e.target.value)}
                className="bg-white text-xs font-bold text-[#143628] border border-gray-200 px-3 py-2.5 rounded-xl outline-none"
              >
                <option value="all">Filter: All Students</option>
                <option value="below_85">Below 85%</option>
                <option value="below_50">Below 50%</option>
                <option value="below_30">Below 30%</option>
              </select>
            </div>
          </div>

          {/* Student Roster Table: Student | Subject | Detected Pattern | Overall Attendance | Action */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-[#f4f8f5] text-gray-600 font-bold uppercase text-[10px]">
                <tr>
                  <th className="p-3.5 rounded-l-xl">Student</th>
                  <th className="p-3.5">Subject</th>
                  <th className="p-3.5">Detected Pattern</th>
                  <th className="p-3.5">Overall Attendance</th>
                  <th className="p-3.5 text-right rounded-r-xl">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredStudents.map((st) => (
                  <tr key={st.id} className="hover:bg-[#f4f8f5]/50 transition-colors">
                    <td className="p-3.5">
                      <div className="font-bold text-[#143628]">{st.name}</div>
                      <div className="text-[10px] text-gray-500 font-medium">{st.usn}</div>
                    </td>
                    <td className="p-3.5 text-gray-700 font-medium">{st.subjectName}</td>
                    <td className="p-3.5 text-gray-800 font-semibold">{st.detectedPattern}</td>
                    <td className="p-3.5">
                      <span className={`pill-badge ${
                        st.overallPct < 50 ? "pill-badge-red" : st.overallPct < 75 ? "pill-badge-amber" : "pill-badge-green"
                      }`}>
                        {st.overallPct.toFixed(1)}%
                      </span>
                    </td>
                    <td className="p-3.5 text-right">
                      {/* View Action Button -> navigates to /student/:id */}
                      <button
                        onClick={() => navigate(`/student/${st.id}`)}
                        className="inline-flex items-center gap-1.5 bg-[#1e4d3b] text-white text-xs font-bold px-3.5 py-1.5 rounded-xl hover:bg-[#143628] transition-all"
                      >
                        <Eye className="w-3.5 h-3.5" /> View
                      </button>
                    </td>
                  </tr>
                ))}
                {filteredStudents.length === 0 && (
                  <tr>
                    <td colSpan="5" className="p-8 text-center text-gray-400 font-medium">
                      No students match the selected search or filter criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Modal: New Class */}
      {showClassModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-[#143628]">Create New Class</h3>
            <form onSubmit={handleCreateClass} className="space-y-3">
              <input
                type="text"
                placeholder="Class Name (e.g. 6th Sem CSE - Section A)"
                required
                value={newClass.name}
                onChange={(e) => setNewClass({ ...newClass, name: e.target.value })}
                className="w-full text-xs p-3 rounded-xl bg-[#f4f8f5] border border-transparent focus:border-[#1e4d3b] outline-none"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="Branch"
                  required
                  value={newClass.branch}
                  onChange={(e) => setNewClass({ ...newClass, branch: e.target.value })}
                  className="text-xs p-3 rounded-xl bg-[#f4f8f5] outline-none"
                />
                <input
                  type="number"
                  placeholder="Semester"
                  required
                  value={newClass.semester}
                  onChange={(e) => setNewClass({ ...newClass, semester: Number(e.target.value) })}
                  className="text-xs p-3 rounded-xl bg-[#f4f8f5] outline-none"
                />
              </div>
              <input
                type="text"
                placeholder="Academic Year (e.g. 2026-27)"
                required
                value={newClass.academic_year}
                onChange={(e) => setNewClass({ ...newClass, academic_year: e.target.value })}
                className="w-full text-xs p-3 rounded-xl bg-[#f4f8f5] outline-none"
              />
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowClassModal(false)} className="text-xs px-4 py-2 rounded-xl text-gray-500">Cancel</button>
                <button type="submit" className="text-xs font-bold px-5 py-2 rounded-xl bg-[#1e4d3b] text-white">Create Class</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Student */}
      {showStudentModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-[#143628]">Add Student Manually</h3>
            <form onSubmit={handleAddStudent} className="space-y-3">
              <input
                type="text"
                placeholder="Student Full Name"
                required
                value={newStudent.name}
                onChange={(e) => setNewStudent({ ...newStudent, name: e.target.value })}
                className="w-full text-xs p-3 rounded-xl bg-[#f4f8f5] outline-none"
              />
              <input
                type="text"
                placeholder="USN (e.g. 1VA21CS099)"
                required
                value={newStudent.usn}
                onChange={(e) => setNewStudent({ ...newStudent, usn: e.target.value })}
                className="w-full text-xs p-3 rounded-xl bg-[#f4f8f5] outline-none"
              />
              <input
                type="email"
                placeholder="Student Email"
                value={newStudent.email}
                onChange={(e) => setNewStudent({ ...newStudent, email: e.target.value })}
                className="w-full text-xs p-3 rounded-xl bg-[#f4f8f5] outline-none"
              />
              <input
                type="email"
                placeholder="Parent Email"
                value={newStudent.parent_email}
                onChange={(e) => setNewStudent({ ...newStudent, parent_email: e.target.value })}
                className="w-full text-xs p-3 rounded-xl bg-[#f4f8f5] outline-none"
              />
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowStudentModal(false)} className="text-xs px-4 py-2 rounded-xl text-gray-500">Cancel</button>
                <button type="submit" className="text-xs font-bold px-5 py-2 rounded-xl bg-[#1e4d3b] text-white">Save Student</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: CSV / Excel Upload */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-[#143628]">Bulk Upload Students (CSV/Excel)</h3>
            <form onSubmit={handleImportStudents} className="space-y-4">
              <input
                type="file"
                accept=".csv, .xlsx, .xls"
                onChange={(e) => setImportFile(e.target.files[0])}
                className="w-full text-xs p-3 rounded-xl bg-[#f4f8f5] border border-dashed border-[#1e4d3b]/40 outline-none"
              />
              {importResult && (
                <div className="p-3 rounded-xl bg-emerald-50 text-emerald-800 text-xs font-medium space-y-1">
                  <div>Added: {importResult.added_count} | Skipped: {importResult.skipped_count}</div>
                  {importResult.errors?.map((err, i) => (
                    <div key={i} className="text-[10px] text-red-600">{err}</div>
                  ))}
                </div>
              )}
              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => { setShowImportModal(false); setImportResult(null); }} className="text-xs px-4 py-2 rounded-xl text-gray-500">Close</button>
                <button type="submit" className="text-xs font-bold px-5 py-2 rounded-xl bg-[#1e4d3b] text-white">Upload File</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
