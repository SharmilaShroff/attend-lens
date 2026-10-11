import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../../api/client";
import Navbar from "../../components/Navbar";
import { ArrowLeft, MessageSquare, Clock, AlertCircle, RefreshCw, UserCheck } from "lucide-react";

export default function StudentRemarksHistory() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [student, setStudent] = useState(null);
  const [remarks, setRemarks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [profileRes, remarksRes] = await Promise.all([
        api.get(`/analytics/student-profile/${id}`),
        api.get(`/remarks/student/${id}`)
      ]);
      setStudent(profileRes.data?.student || null);
      setRemarks(remarksRes.data || []);
    } catch (err) {
      console.error("Failed to fetch remarks history:", err);
      setError("Failed to load student remarks history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f4f8f5]">
        <Navbar />
        <div className="max-w-4xl mx-auto p-8 space-y-6">
          <div className="h-10 bg-white/60 rounded-2xl animate-pulse w-1/4"></div>
          <div className="h-32 bg-white rounded-3xl animate-pulse border border-[#1e4d3b]/10"></div>
          <div className="h-64 bg-white rounded-3xl animate-pulse border border-[#1e4d3b]/10"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#f4f8f5]">
        <Navbar />
        <div className="max-w-2xl mx-auto mt-16 p-8 bg-white rounded-3xl border border-red-200 text-center space-y-4 shadow-sm">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
          <h2 className="text-xl font-extrabold text-[#143628]">Unable to Load Remarks</h2>
          <p className="text-xs text-gray-600">{error}</p>
          <div className="flex justify-center gap-3 pt-2">
            <button
              onClick={() => navigate(`/student/${id}`)}
              className="text-xs font-bold text-gray-700 bg-gray-100 px-4 py-2.5 rounded-2xl hover:bg-gray-200"
            >
              &larr; Back to Student Profile
            </button>
            <button
              onClick={fetchData}
              className="text-xs font-bold text-white bg-[#1e4d3b] px-5 py-2.5 rounded-2xl hover:bg-[#143628] flex items-center gap-2"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f4f8f5] pb-16">
      <Navbar />

      <main className="max-w-4xl mx-auto p-4 sm:p-6 md:p-8 space-y-6">
        {/* Navigation */}
        <div>
          <button
            onClick={() => navigate(`/student/${id}`)}
            className="inline-flex items-center gap-2 text-xs font-bold text-[#1e4d3b] bg-white border border-[#1e4d3b]/20 px-4 py-2.5 rounded-2xl hover:bg-[#e8f5e9] transition-all shadow-sm"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Student Profile
          </button>
        </div>

        {/* Header Card */}
        <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-[#1e4d3b] text-white flex items-center justify-center font-extrabold text-lg shadow-md shrink-0">
              <MessageSquare className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-extrabold text-[#143628]">Full Remarks History</h1>
              {student && (
                <p className="text-xs text-gray-500 mt-0.5">
                  Student: <strong className="text-gray-800">{student.name}</strong> (USN: {student.usn})
                </p>
              )}
            </div>
          </div>
          <span className="text-xs font-bold text-[#1e4d3b] bg-[#e8f5e9] px-3.5 py-1.5 rounded-full border border-[#1e4d3b]/20 w-fit">
            {remarks.length} Total Remarks
          </span>
        </div>

        {/* Remarks Timeline List */}
        <div className="bg-white p-6 rounded-3xl border border-[#1e4d3b]/10 shadow-sm space-y-4">
          {remarks.length === 0 ? (
            <div className="p-12 text-center bg-[#f4f8f5] rounded-3xl border border-[#1e4d3b]/10 space-y-2">
              <MessageSquare className="w-10 h-10 text-gray-400 mx-auto" />
              <p className="text-sm font-bold text-gray-700">No Remarks Recorded</p>
              <p className="text-xs text-gray-500">There are no mentor remarks saved for this student yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {remarks.map((rem) => (
                <div
                  key={rem.id}
                  className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 space-y-2"
                >
                  <div className="flex items-center justify-between text-xs border-b border-gray-200/60 pb-2">
                    <div className="flex items-center gap-2">
                      <UserCheck className="w-4 h-4 text-[#1e4d3b]" />
                      <span className="font-extrabold text-[#143628]">{rem.author_name || "Mentor"}</span>
                      <span className="text-[10px] uppercase font-bold text-gray-500 bg-white px-2 py-0.5 rounded-md border border-gray-200">
                        {rem.role}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-[11px] text-gray-500 font-medium">
                      <Clock className="w-3.5 h-3.5 text-gray-400" />
                      <span>{new Date(rem.created_at).toLocaleString([], { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
                    </div>
                  </div>
                  <p className="text-xs text-gray-800 leading-relaxed font-medium pt-1 whitespace-pre-line">{rem.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
