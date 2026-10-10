import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../../api/client";
import Navbar from "../../components/Navbar";
import { ArrowLeft, CheckCircle2, XCircle, Clock } from "lucide-react";

export default function StudentSubjectDetail() {
  const { subjectId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const { data: res } = await api.get(`/student/subjects/${subjectId}/records`);
        setData(res);
      } catch (err) {
        console.error("Failed to fetch subject records:", err);
      } finally {
        setLoading(false);
      }
    };
    if (subjectId) {
      fetchData();
    }
  }, [subjectId]);

  if (loading || !data) {
    return (
      <div className="min-h-screen bg-[#f4f8f5] flex items-center justify-center text-[#143628] font-bold text-sm">
        Loading Subject Attendance Records...
      </div>
    );
  }

  const { subject, present_classes, absent_classes } = data;

  return (
    <div className="h-screen bg-[#f4f8f5] flex flex-col overflow-hidden">
      <Navbar />

      <main className="flex-1 w-full max-w-7xl mx-auto p-4 md:p-6 flex flex-col overflow-hidden">
        {/* Header Card */}
        <div className="bg-white p-5 rounded-3xl border border-[#1e4d3b]/10 shadow-sm flex items-center justify-between gap-4 shrink-0 mb-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/student")}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-2xl bg-[#f4f8f5] text-[#143628] hover:bg-[#e8f5e9] border border-[#1e4d3b]/15 text-xs font-bold transition-all shadow-sm"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Student Portal</span>
            </button>

            <div>
              <h1 className="text-xl font-extrabold text-[#143628]">
                {subject.name} <span className="text-sm font-semibold text-gray-500">({subject.code})</span>
              </h1>
              <p className="text-xs text-gray-500">Detailed Per-Class Attendance Log</p>
            </div>
          </div>

          <div className="px-4 py-2.5 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 text-center">
            <span className="text-[10px] font-bold text-gray-500 uppercase block">Overall Subject Attendance</span>
            <span className={`text-xl font-extrabold ${subject.overall_pct >= 75 ? "text-[#1e4d3b]" : "text-red-600"}`}>
              {subject.overall_pct}%
            </span>
          </div>
        </div>

        {/* Two Equal Halves Side by Side Container */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 overflow-hidden min-h-0">
          
          {/* Left Half: Present Classes */}
          <div className="bg-white p-5 rounded-3xl border border-[#1e4d3b]/10 shadow-sm flex flex-col h-full overflow-hidden">
            <div className="sticky top-0 bg-white z-10 pb-3 border-b border-gray-100 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-[#1e4d3b]" />
                <h3 className="text-sm font-extrabold text-[#143628]">
                  Present Classes <span className="text-emerald-700 bg-[#e8f5e9] px-2.5 py-0.5 rounded-full text-xs ml-1">({subject.attended_classes})</span>
                </h3>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2.5 pt-3 pr-1">
              {present_classes.length > 0 ? (
                present_classes.map((item) => (
                  <div key={item.id} className="p-3.5 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 flex items-center justify-between text-xs hover:bg-[#e8f5e9]/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-xl bg-emerald-100 text-[#1e4d3b] flex items-center justify-center font-extrabold shrink-0">
                        <CheckCircle2 className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="font-bold text-[#143628]">{item.day_of_week}, {item.formatted_date}</div>
                        <div className="text-[10px] text-gray-500 flex items-center gap-1 mt-0.5">
                          <Clock className="w-3 h-3" /> Period {item.period || 1}
                        </div>
                      </div>
                    </div>
                    <span className="pill-badge pill-badge-green text-[10px]">Present</span>
                  </div>
                ))
              ) : (
                <div className="text-xs text-gray-400 text-center py-12">No present classes recorded.</div>
              )}
            </div>
          </div>

          {/* Right Half: Absent Classes */}
          <div className="bg-white p-5 rounded-3xl border border-[#1e4d3b]/10 shadow-sm flex flex-col h-full overflow-hidden">
            <div className="sticky top-0 bg-white z-10 pb-3 border-b border-gray-100 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <XCircle className="w-5 h-5 text-red-600" />
                <h3 className="text-sm font-extrabold text-[#143628]">
                  Absent Classes <span className="text-red-700 bg-red-50 px-2.5 py-0.5 rounded-full text-xs ml-1">({subject.absent_classes})</span>
                </h3>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2.5 pt-3 pr-1">
              {absent_classes.length > 0 ? (
                absent_classes.map((item) => (
                  <div key={item.id} className="p-3.5 rounded-2xl bg-red-50/50 border border-red-100 flex items-center justify-between text-xs hover:bg-red-50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-xl bg-red-100 text-red-600 flex items-center justify-center font-extrabold shrink-0">
                        <XCircle className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="font-bold text-[#143628]">{item.day_of_week}, {item.formatted_date}</div>
                        <div className="text-[10px] text-gray-500 flex items-center gap-1 mt-0.5">
                          <Clock className="w-3 h-3" /> Period {item.period || 1}
                        </div>
                      </div>
                    </div>
                    <span className="pill-badge pill-badge-red text-[10px]">Absent</span>
                  </div>
                ))
              ) : (
                <div className="text-xs text-gray-400 text-center py-12">No absent classes recorded.</div>
              )}
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
