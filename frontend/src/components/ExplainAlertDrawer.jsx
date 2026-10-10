import { useState } from "react";
import api from "../api/client";
import { X, AlertTriangle, CheckCircle, ShieldAlert, Sparkles, Send } from "lucide-react";

export default function ExplainAlertDrawer({ alert, onClose, onRefresh }) {
  const [overrideLevel, setOverrideLevel] = useState("high");
  const [overrideReason, setOverrideReason] = useState("");
  const [dismissReason, setDismissReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState("");

  if (!alert) return null;

  const handleOverride = async (e) => {
    e.preventDefault();
    if (!overrideReason.trim()) return alert("Please enter a reason for overriding");
    setSubmitting(true);
    try {
      await api.post(`/alerts/${alert.id}/override`, {
        override_level: overrideLevel,
        reason: overrideReason
      });
      setMsg("Alert severity overridden successfully!");
      onRefresh();
    } catch (err) {
      alert("Failed to override alert");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDismiss = async (e) => {
    e.preventDefault();
    if (!dismissReason.trim()) return alert("Please enter a reason for dismissing");
    setSubmitting(true);
    try {
      await api.post(`/alerts/${alert.id}/dismiss`, {
        reason: dismissReason
      });
      setMsg("Alert dismissed successfully!");
      onRefresh();
    } catch (err) {
      alert("Failed to dismiss alert");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateCounselling = async () => {
    setSubmitting(true);
    try {
      await api.post(`/counselling/cases/from-alert/${alert.id}`);
      setMsg("Personalized AI Counselling message generated and queued!");
      onRefresh();
    } catch (err) {
      alert("Failed to trigger counselling case");
    } finally {
      setSubmitting(false);
    }
  };

  const levelColor = {
    critical: "bg-red-100 text-red-800 border-red-200",
    high: "bg-orange-100 text-orange-800 border-orange-200",
    medium: "bg-amber-100 text-amber-800 border-amber-200",
    low: "bg-green-100 text-green-800 border-green-200"
  }[alert.override_level || alert.level] || "bg-gray-100 text-gray-800";

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex justify-end transition-opacity">
      <div className="bg-white w-full max-w-lg h-full overflow-y-auto p-6 shadow-2xl flex flex-col justify-between">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-[#1e4d3b] text-white flex items-center justify-center">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-lg font-extrabold text-[#143628]">AI Risk Explainability</h3>
                <p className="text-xs text-gray-500">Pattern analysis breakdown for {alert.student_name}</p>
              </div>
            </div>
            <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-100 text-gray-400">
              <X className="w-5 h-5" />
            </button>
          </div>

          {msg && (
            <div className="mb-4 p-3 rounded-2xl bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold">
              {msg}
            </div>
          )}

          {/* Student & Alert Overview Pill */}
          <div className="p-4 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10 mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-gray-700">{alert.student_name}</span>
              <span className={`pill-badge border ${levelColor} capitalize`}>
                {alert.override_level || alert.level} Risk ({alert.risk_score.toFixed(0)}/100)
              </span>
            </div>
            <p className="text-xs text-gray-600">
              Subject: <strong className="text-[#143628]">{alert.subject_name || "Overall Attendance"}</strong> | Pattern: <span className="font-semibold">{alert.type}</span>
            </p>
            {alert.explanation?.low_confidence && (
              <div className="mt-2 text-[11px] text-amber-700 bg-amber-50 p-2 rounded-xl border border-amber-200">
                ⚠️ Low confidence alert: Less than 8 total attendance records available.
              </div>
            )}
          </div>

          {/* Human Readable Reasons */}
          <div className="mb-6">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#1e4d3b] mb-3">
              Detected Reasons & Evidence
            </h4>
            <div className="space-y-2">
              {alert.explanation?.reasons?.map((reason, i) => (
                <div key={i} className="p-3 rounded-xl bg-gray-50 border border-gray-200 text-xs font-medium text-gray-800 flex items-start gap-2">
                  <span className="text-[#1e4d3b] font-bold">•</span>
                  <span>{reason}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Contributing Factors Breakdown */}
          <div className="mb-6">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#1e4d3b] mb-3">
              Contributing Factors Breakdown
            </h4>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(alert.explanation?.factors || {}).map(([key, val]) => (
                <div key={key} className="p-3 rounded-2xl bg-[#f4f8f5] border border-[#1e4d3b]/10">
                  <span className="text-[10px] font-semibold text-gray-500 uppercase block">{key}</span>
                  <span className="text-sm font-extrabold text-[#143628]">{String(val)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Staff Actions */}
          <div className="space-y-4 pt-4 border-t border-gray-100">
            {/* Generate AI Counselling Button */}
            <button
              onClick={handleCreateCounselling}
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 bg-[#1e4d3b] text-white text-xs font-bold py-3 rounded-2xl hover:bg-[#143628] transition-all shadow-md"
            >
              <Send className="w-4 h-4" />
              <span>Generate Personalized AI Counselling Check-in</span>
            </button>

            {/* Staff Override Severity Form */}
            <form onSubmit={handleOverride} className="p-4 rounded-2xl bg-gray-50 border border-gray-200 space-y-3">
              <h5 className="text-xs font-bold text-gray-800">Staff Severity Override</h5>
              <div className="flex gap-2">
                {["low", "medium", "high", "critical"].map((lvl) => (
                  <button
                    key={lvl}
                    type="button"
                    onClick={() => setOverrideLevel(lvl)}
                    className={`flex-1 py-1.5 rounded-xl text-[11px] font-bold capitalize border transition-all ${
                      overrideLevel === lvl
                        ? "bg-[#1e4d3b] text-white border-[#1e4d3b]"
                        : "bg-white text-gray-700 border-gray-200 hover:bg-gray-100"
                    }`}
                  >
                    {lvl}
                  </button>
                ))}
              </div>
              <input
                type="text"
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="Reason for overriding risk severity..."
                className="w-full text-xs p-2.5 rounded-xl border border-gray-200 focus:border-[#1e4d3b] outline-none"
              />
              <button
                type="submit"
                disabled={submitting}
                className="w-full bg-gray-800 text-white text-xs font-semibold py-2 rounded-xl hover:bg-black"
              >
                Save Override
              </button>
            </form>

            {/* Dismiss Alert Form */}
            <form onSubmit={handleDismiss} className="p-4 rounded-2xl bg-red-50/50 border border-red-100 space-y-3">
              <h5 className="text-xs font-bold text-red-900">Dismiss Alert</h5>
              <input
                type="text"
                value={dismissReason}
                onChange={(e) => setDismissReason(e.target.value)}
                placeholder="Mandatory reason for dismissal (e.g., Medical leave approved)..."
                className="w-full text-xs p-2.5 rounded-xl border border-red-200 focus:border-red-500 outline-none"
              />
              <button
                type="submit"
                disabled={submitting}
                className="w-full bg-red-600 text-white text-xs font-semibold py-2 rounded-xl hover:bg-red-700"
              >
                Dismiss Alert (Retain Audit)
              </button>
            </form>
          </div>
        </div>

        <div className="pt-6 text-center border-t border-gray-100">
          <button onClick={onClose} className="text-xs font-bold text-gray-500 hover:text-gray-800">
            Close Drawer
          </button>
        </div>
      </div>
    </div>
  );
}
