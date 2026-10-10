import { useState } from "react";
import api from "../api/client";
import { MessageSquare, X, Send, Bot, User } from "lucide-react";

export default function AIChatbotWidget() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([
    {
      sender: "bot",
      text: "Hi! I am your Rollcall AI Assistant. Ask me anything about your attendance, classes needed, or risk flags!"
    }
  ]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    const q = question;
    setQuestion("");
    setMessages((prev) => [...prev, { sender: "user", text: q }]);
    setLoading(true);

    try {
      const { data } = await api.post("/chatbot", { question: q });
      setMessages((prev) => [...prev, { sender: "bot", text: data.answer }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "Sorry, I am having trouble fetching your attendance facts right now." }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-40">
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 bg-[#1e4d3b] text-white font-bold px-5 py-3.5 rounded-full shadow-2xl hover:bg-[#143628] transition-all transform hover:scale-105"
        >
          <Bot className="w-5 h-5" />
          <span>Ask Rollcall AI</span>
        </button>
      ) : (
        <div className="bg-white w-80 sm:w-96 h-[480px] rounded-3xl shadow-2xl border border-[#1e4d3b]/20 flex flex-col justify-between overflow-hidden">
          {/* Header */}
          <div className="bg-[#1e4d3b] text-white p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot className="w-5 h-5 text-[#a3b899]" />
              <div>
                <h4 className="text-sm font-bold">Rollcall Student Chatbot</h4>
                <span className="text-[10px] text-white/70">Grounded in real DB attendance metrics</span>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="p-1 rounded-full hover:bg-white/10 text-white/80">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages Area */}
          <div className="p-4 flex-1 overflow-y-auto space-y-3 bg-[#f4f8f5]">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-2 text-xs ${m.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.sender === "bot" && (
                  <div className="w-6 h-6 rounded-full bg-[#1e4d3b] text-white flex items-center justify-center text-[10px] font-bold shrink-0">
                    AI
                  </div>
                )}
                <div
                  className={`p-3 rounded-2xl max-w-[80%] leading-relaxed ${
                    m.sender === "user"
                      ? "bg-[#1e4d3b] text-white rounded-br-none"
                      : "bg-white text-gray-800 border border-gray-200 rounded-bl-none shadow-sm"
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-2 text-xs justify-start">
                <div className="w-6 h-6 rounded-full bg-[#1e4d3b] text-white flex items-center justify-center text-[10px] font-bold">
                  AI
                </div>
                <div className="p-3 rounded-2xl bg-white text-gray-500 border border-gray-200 text-xs italic">
                  Analyzing attendance time-series...
                </div>
              </div>
            )}
          </div>

          {/* Input Form */}
          <form onSubmit={handleSend} className="p-3 bg-white border-t border-gray-100 flex items-center gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Can I skip tomorrow's DBMS class?"
              className="flex-1 text-xs p-2.5 rounded-xl bg-[#f4f8f5] border border-transparent focus:border-[#1e4d3b] outline-none"
            />
            <button
              type="submit"
              disabled={loading}
              className="p-2.5 bg-[#1e4d3b] text-white rounded-xl hover:bg-[#143628] transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
