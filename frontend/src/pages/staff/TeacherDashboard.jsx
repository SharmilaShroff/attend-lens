import { useState, useEffect } from "react";
import api from "../../api/client";
import Navbar from "../../components/Navbar";
import Sidebar from "../../components/Sidebar";
import { BookOpen, CheckCircle2, XCircle, Plus, Trash2, Calendar, Save, History, Layers } from "lucide-react";

export default function TeacherDashboard() {
  const [activeTab, setActiveTab] = useState("overview");
  const [myClasses, setMyClasses] = useState([]);
  const [availableClasses, setAvailableClasses] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
  const [period, setPeriod] = useState(1);
  const [studentsGrid, setStudentsGrid] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const loadInitialData = async () => {
    try {
      const [{ data: myCls }, { data: availCls }] = await Promise.all([
        api.get("/teacher/my-classes"),
        api.get("/teacher/available-classes")
      ]);
      setMyClasses(myCls);
      setAvailableClasses(availCls);

      const activeCId = selectedClassId || (myCls.length > 0 ? myCls[0].id : null);
      if (activeCId) {
        setSelectedClassId(activeCId);
        const { data: subs } = await api.get(`/mentor/classes/${activeCId}/subjects`);
        setSubjects(subs);
        if (subs.length > 0) setSelectedSubjectId(subs[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadGrid = async () => {
    if (!selectedClassId || !selectedSubjectId || !selectedDate) return;
    try {
      const { data } = await api.get(`/teacher/attendance-records?class_id=${selectedClassId}&subject_id=${selectedSubjectId}&date=${selectedDate}&period=${period}`);
      setStudentsGrid(data);

      const { data: ad } = await api.get(`/teacher/audit-logs?class_id=${selectedClassId}`);
      setAuditLogs(ad);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadGrid();
  }, [selectedClassId, selectedSubjectId, selectedDate, period]);

  const handleSelectClass = async (cId) => {
    try {
      await api.post(`/teacher/select-class/${cId}`);
      loadInitialData();
    } catch (err) {
      alert("Failed to select class");
    }
  };

  const handleRemoveClass = async (cId) => {
    try {
      await api.delete(`/teacher/remove-class/${cId}`);
      loadInitialData();
    } catch (err) {
      alert("Failed to remove class");
    }
  };

  const toggleStudentStatus = (sId) => {
    setStudentsGrid((prev) =>
      prev.map((item) => {
        if (item.student_id === sId) {
          const nextStatus = item.status === "present" ? "absent" : "present";
          return { ...item, status: nextStatus };
        }
        return item;
      })
    );
  };

  const handleMarkAllPresent = () => {
    setStudentsGrid((prev) => prev.map((item) => ({ ...item, status: "present" })));
  };

  const handleSaveAttendance = async () => {
    setSaving(true);
    setMsg("");
    try {
      const items = studentsGrid
        .filter((item) => item.status !== "not_marked")
        .map((item) => ({
          student_id: item.student_id,
          status: item.status
        }));

      await api.post("/teacher/mark-attendance", {
        class_id: selectedClassId,
        subject_id: selectedSubjectId,
        date: selectedDate,
        period: Number(period),
        items: items
      });

      setMsg("Attendance & Audit Log saved successfully!");
      loadGrid();
    } catch (err) {
      alert("Failed to save attendance");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f4f8f5]">
      <Navbar />

      <main className="w-full max-w-7xl mx-auto p-6 md:p-8 space-y-6">
          {/* Top Bar: My Classes Selection */}
          <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-[#1e4d3b] uppercase tracking-wider bg-[#e8f5e9] px-3 py-1 rounded-full">
                  SUBJECT TEACHER WORKSPACE
                </span>
                <h1 className="text-2xl font-extrabold text-[#143628] mt-2">
                  My Teaching Classes
                </h1>
              </div>
            </div>

            <div className="flex items-center gap-3 overflow-x-auto pb-2">
              {myClasses.map((c) => {
                const isSelected = c.id === selectedClassId;
                return (
                  <div
                    key={c.id}
                    className={`p-4 rounded-2xl border transition-all min-w-[200px] flex items-center justify-between ${
                      isSelected
                        ? "bg-[#1e4d3b] text-white border-[#1e4d3b] shadow-md"
                        : "bg-[#f4f8f5] text-[#143628] border-[#1e4d3b]/10 hover:bg-white"
                    }`}
                  >
                    <button onClick={() => setSelectedClassId(c.id)} className="text-left font-bold text-xs">
                      <div>{c.name}</div>
                      <div className={`text-[10px] font-medium ${isSelected ? "text-white/80" : "text-gray-500"}`}>
                        {c.academic_year}
                      </div>
                    </button>
                    <button
                      onClick={() => handleRemoveClass(c.id)}
                      className={`p-1 rounded-lg hover:bg-red-500/20 ${isSelected ? "text-white" : "text-gray-400"}`}
                      title="Remove from my list"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}

              {/* Add/Select class button */}
              <div className="relative group">
                <select
                  onChange={(e) => {
                    if (e.target.value) handleSelectClass(Number(e.target.value));
                  }}
                  defaultValue=""
                  className="bg-white text-xs font-bold text-[#1e4d3b] border border-[#1e4d3b]/30 px-4 py-3 rounded-2xl outline-none cursor-pointer hover:bg-[#e8f5e9]"
                >
                  <option value="" disabled>+ Add Class I Teach</option>
                  {availableClasses.map((ac) => (
                    <option key={ac.id} value={ac.id}>
                      {ac.name} ({ac.academic_year})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Controls bar: Subject, Date, Period */}
          <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3 flex-wrap">
              <div>
                <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Subject</label>
                <select
                  value={selectedSubjectId || ""}
                  onChange={(e) => setSelectedSubjectId(Number(e.target.value))}
                  className="bg-[#f4f8f5] border border-[#1e4d3b]/20 text-xs font-bold text-[#143628] px-4 py-2.5 rounded-2xl outline-none"
                >
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Date</label>
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="bg-[#f4f8f5] border border-[#1e4d3b]/20 text-xs font-bold text-[#143628] px-4 py-2 rounded-2xl outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Period Slot</label>
                <select
                  value={period}
                  onChange={(e) => setPeriod(Number(e.target.value))}
                  className="bg-[#f4f8f5] border border-[#1e4d3b]/20 text-xs font-bold text-[#143628] px-4 py-2.5 rounded-2xl outline-none"
                >
                  <option value={1}>Period 1 (9:00 AM)</option>
                  <option value={2}>Period 2 (10:00 AM)</option>
                  <option value={3}>Period 3 (11:15 AM)</option>
                  <option value={4}>Period 4 (12:15 PM)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleMarkAllPresent}
                className="text-xs font-bold text-[#1e4d3b] bg-[#e8f5e9] px-4 py-2.5 rounded-2xl hover:bg-[#c8e6c9] transition-all"
              >
                ✓ Mark All Present
              </button>
              <button
                onClick={handleSaveAttendance}
                disabled={saving}
                className="flex items-center gap-2 text-xs font-bold text-white bg-[#1e4d3b] px-6 py-2.5 rounded-2xl hover:bg-[#143628] transition-all shadow-md"
              >
                <Save className="w-4 h-4" /> Save / Overwrite Attendance
              </button>
            </div>
          </div>

          {msg && (
            <div className="p-4 rounded-2xl bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold">
              {msg}
            </div>
          )}

          {/* Student Attendance Marking Grid */}
          <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-extrabold text-[#143628]">Student Attendance Grid</h3>
              <span className="text-xs text-gray-500">
                Click status pill to toggle Present / Absent. Previously saved records will be audit-logged.
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {studentsGrid.map((st) => {
                const isPresent = st.status === "present";
                const isNotMarked = st.status === "not_marked";
                return (
                  <div
                    key={st.student_id}
                    onClick={() => toggleStudentStatus(st.student_id)}
                    className={`p-4 rounded-2xl border cursor-pointer transition-all flex items-center justify-between ${
                      isPresent
                        ? "bg-[#e8f5e9] border-[#1e4d3b]/30 text-[#1e4d3b]"
                        : isNotMarked
                        ? "bg-gray-50 border-gray-200 text-gray-600"
                        : "bg-red-50 border-red-200 text-red-800"
                    }`}
                  >
                    <div>
                      <div className="text-xs font-extrabold">{st.student_name}</div>
                      <div className="text-[10px] font-bold opacity-75">{st.usn}</div>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs font-bold capitalize">
                      {isPresent ? (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-[#1e4d3b]" />
                          <span>Present</span>
                        </>
                      ) : isNotMarked ? (
                        <span className="text-gray-400 font-semibold italic">Not marked</span>
                      ) : (
                        <>
                          <XCircle className="w-4 h-4 text-red-600" />
                          <span>Absent</span>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Audit Log Stream */}
          <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-extrabold text-[#143628]">Recent Audit Log</h3>
                <p className="text-xs text-gray-500">Immutable trail of attendance edits & overwrites</p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#f4f8f5] text-gray-600 font-bold uppercase text-[10px]">
                  <tr>
                    <th className="p-3 rounded-l-xl">Student</th>
                    <th className="p-3">Subject</th>
                    <th className="p-3">Date</th>
                    <th className="p-3">Old Value</th>
                    <th className="p-3">New Value</th>
                    <th className="p-3">Changed By</th>
                    <th className="p-3 rounded-r-xl">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-[#f4f8f5]/50">
                      <td className="p-3 font-bold text-[#143628]">{log.student_name}</td>
                      <td className="p-3">{log.subject_name}</td>
                      <td className="p-3">{log.date}</td>
                      <td className="p-3 font-semibold text-gray-500">{log.old_status || "Not Marked"}</td>
                      <td className="p-3 font-bold text-[#1e4d3b]">{log.new_status}</td>
                      <td className="p-3 text-gray-600">{log.changed_by_name}</td>
                      <td className="p-3 text-gray-400">{new Date(log.changed_at).toLocaleTimeString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </main>
    </div>
  );
}
