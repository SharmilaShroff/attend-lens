import { useState, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import api from "../api/client";
import { MessageSquare, X, Send, Trash2, Sparkles, AlertCircle } from "lucide-react";

const CHAT_STORAGE_KEY = "attendlens_chat_history";

export default function FloatingChatbot() {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState(() => {
    try {
      const saved = sessionStorage.getItem(CHAT_STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch { }
    return [
      {
        role: "assistant",
        text: "Hello! I am your Attend Lens AI Assistant. Ask me anything—from study help, writing, and general questions to attendance records!"
      }
    ];
  });

  const chatEndRef = useRef(null);

  // Extract student_id if on student detail page
  const studentIdMatch = location.pathname.match(/\/(?:student|student-profile)\/(\d+)/);
  const currentStudentId = studentIdMatch ? Number(studentIdMatch[1]) : null;

  useEffect(() => {
    try {
      sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
    } catch { }
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  const handleSend = async (e) => {
    e?.preventDefault();
    const q = input.trim();
    if (!q || loading) return;

    const userMsg = { role: "user", text: q };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const { data } = await api.post("/chatbot", {
        question: q,
        student_id: currentStudentId
      });

      const replyText = data?.answer || "No response received.";
      setMessages((prev) => [...prev, { role: "assistant", text: replyText }]);
    } catch (err) {
      console.error("Chatbot request error:", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "AI features are not configured. Please add OPENROUTER_API_KEY to backend .env",
          isError: true
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    const defaultMsg = [
      {
        role: "assistant",
        text: "Chat cleared. How can I assist you today?"
      }
    ];
    setMessages(defaultMsg);
    try {
      sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(defaultMsg));
    } catch { }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Floating Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="w-14 h-14 rounded-full bg-[#1e4d3b] text-white shadow-2xl flex items-center justify-center hover:bg-[#143628] hover:scale-105 transition-all duration-300 ring-4 ring-[#1e4d3b]/20"
          title="Open Attend Lens AI Assistant"
        >
          <Sparkles className="w-6 h-6 text-[#a3b899]" />
        </button>
      )}

      {/* Floating Chat Panel */}
      {isOpen && (
        <div className="bg-white rounded-3xl border border-[#1e4d3b]/15 shadow-2xl w-[90vw] sm:w-[380px] h-[520px] flex flex-col overflow-hidden transition-all duration-300 animate-in fade-in slide-in-from-bottom-4">
          {/* Header */}
          <div className="bg-[#1e4d3b] text-white p-4 flex items-center justify-between shadow-md">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-2xl bg-white/20 flex items-center justify-center text-[#a3b899]">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-extrabold text-white">Attend Lens Assistant</h3>
                <span className="text-[10px] text-[#a3b899] font-medium block">
                  General AI Assistant & Academic Help
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={handleClear}
                className="p-1.5 text-white/70 hover:text-white hover:bg-white/10 rounded-xl transition-colors"
                title="Clear Chat History"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-white/70 hover:text-white hover:bg-white/10 rounded-xl transition-colors"
                title="Minimize"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Message List */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-[#f4f8f5] text-xs">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] p-3.5 rounded-2xl whitespace-pre-wrap leading-relaxed shadow-sm ${
                    m.role === "user"
                      ? "bg-[#1e4d3b] text-white rounded-br-none"
                      : m.isError
                      ? "bg-red-50 border border-red-200 text-red-900 rounded-bl-none"
                      : "bg-white text-gray-800 border border-[#1e4d3b]/10 rounded-bl-none font-medium"
                  }`}
                >
                  {m.isError && (
                    <div className="flex items-center gap-1.5 mb-1 font-bold text-red-700">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>AI Feature Notice</span>
                    </div>
                  )}
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-white p-3.5 rounded-2xl border border-[#1e4d3b]/10 text-gray-500 font-bold flex items-center gap-2 rounded-bl-none">
                  <Sparkles className="w-4 h-4 text-[#1e4d3b] animate-spin" />
                  <span>AI Assistant is thinking...</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input Form */}
          <form onSubmit={handleSend} className="p-3 bg-white border-t border-gray-100 flex items-center gap-2">
            <input
              type="text"
              placeholder="Ask anything (study help, coding, attendance)..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 text-xs px-3.5 py-2.5 rounded-2xl bg-[#f4f8f5] border border-transparent focus:border-[#1e4d3b] outline-none font-medium text-gray-800"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-2.5 bg-[#1e4d3b] text-white rounded-2xl hover:bg-[#143628] transition-all disabled:opacity-40"
              title="Send Message"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
