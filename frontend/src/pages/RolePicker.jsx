import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserCheck, BookOpen, GraduationCap, ArrowUpRight, ArrowRight } from "lucide-react";

export default function RolePicker() {
  const [selectedRole, setSelectedRole] = useState("mentor");
  const navigate = useNavigate();

  const handleContinue = () => {
    navigate(`/login?role=${selectedRole}`);
  };

  const roles = [
    {
      id: "mentor",
      title: "Mentor",
      subtitle: "Your class. Your students. Your impact.",
      desc: "See the bigger picture. Guide your students toward better habits.",
      icon: UserCheck,
    },
    {
      id: "teacher",
      title: "Subject Teacher",
      subtitle: "Every subject, with a clearer view.",
      desc: "Make every lesson count. Track attendance across your subjects.",
      icon: BookOpen,
    },
    {
      id: "student",
      title: "Student",
      subtitle: "Your journey, in your hands.",
      desc: "Own your progress. Stay on top of your attendance and goals.",
      icon: GraduationCap,
    },
  ];

  return (
    <div className="min-h-screen bg-[#f4f8f5] flex flex-col justify-between p-6 md:p-12 relative overflow-hidden">
      {/* Background ambient concentric rings */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20">
        <div className="w-[600px] h-[600px] rounded-full border border-[#1e4d3b]"></div>
        <div className="w-[900px] h-[900px] rounded-full border border-[#1e4d3b] absolute"></div>
        <div className="w-[1200px] h-[1200px] rounded-full border border-[#1e4d3b] absolute"></div>
      </div>

      {/* Header */}
      <header className="flex items-center justify-between z-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-[#1e4d3b] text-white flex items-center justify-center font-bold text-lg">
            A
          </div>
          <span className="text-xl font-bold tracking-tight text-[#143628]">Attend Lens</span>
        </div>
        <div className="text-xs font-semibold text-[#1e4d3b]/70 bg-white/80 px-4 py-2 rounded-full border border-[#1e4d3b]/10">
          Campus Portal v1.0
        </div>
      </header>

      {/* Main Role Selection Area */}
      <main className="max-w-5xl mx-auto w-full py-8 text-center z-10 flex flex-col items-center">
        <span className="text-xs font-bold uppercase tracking-widest text-[#1e4d3b] bg-[#e8f5e9] px-3.5 py-1.5 rounded-full mb-3">
          02 / FIND YOUR SPACE
        </span>
        <h1 className="text-4xl md:text-5xl font-extrabold text-[#143628] tracking-tight mb-3">
          One campus. Your perspective.
        </h1>
        <p className="text-sm md:text-base text-gray-600 max-w-lg mb-12">
          Choose how you'll use Attend Lens. We'll make the workspace feel like you.
        </p>

        {/* 3 Circular Interactive Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full mb-12">
          {roles.map((role) => {
            const Icon = role.icon;
            const isSelected = selectedRole === role.id;
            return (
              <button
                key={role.id}
                onClick={() => setSelectedRole(role.id)}
                className={`group flex flex-col items-center text-center p-8 rounded-full transition-all duration-300 transform hover:-translate-y-1 relative ${
                  isSelected
                    ? "bg-[#1e4d3b] text-white shadow-xl ring-4 ring-[#1e4d3b]/20"
                    : "bg-white/80 text-[#143628] hover:bg-white border border-[#1e4d3b]/15 shadow-sm"
                }`}
                style={{ aspectRatio: "1/1" }}
              >
                <div
                  className={`w-14 h-14 rounded-full flex items-center justify-center mb-4 transition-transform group-hover:scale-110 ${
                    isSelected ? "bg-white/20 text-white" : "bg-[#e8f5e9] text-[#1e4d3b]"
                  }`}
                >
                  <Icon className="w-7 h-7" />
                </div>

                <h3 className="text-2xl font-bold mb-2">{role.title}</h3>
                <p className={`text-xs max-w-[200px] mb-4 ${isSelected ? "text-white/80" : "text-gray-600"}`}>
                  {role.desc}
                </p>

                <div className="mt-auto pt-2 flex items-center gap-1 text-[11px] font-medium opacity-90">
                  <span>{role.subtitle}</span>
                  {isSelected ? (
                    <div className="w-4 h-4 rounded-full bg-white text-[#1e4d3b] flex items-center justify-center ml-1">
                      ✓
                    </div>
                  ) : (
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Bottom Continue Action */}
        <div className="flex flex-col items-center gap-2">
          <button
            onClick={handleContinue}
            className="flex items-center gap-3 bg-[#1e4d3b] text-white font-semibold px-8 py-4 rounded-full hover:bg-[#143628] transition-all shadow-lg hover:shadow-xl text-base group"
          >
            <span>Continue as {selectedRole.charAt(0).toUpperCase() + selectedRole.slice(1)}</span>
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center group-hover:translate-x-1 transition-transform">
              <ArrowRight className="w-4 h-4" />
            </div>
          </button>
          <span className="text-xs text-gray-500 mt-1">You can switch your role anytime.</span>
        </div>
      </main>

      {/* Footer */}
      <footer className="flex items-center justify-between text-xs text-gray-500 z-10">
        <button onClick={() => navigate("/login")} className="hover:underline">
          &larr; Direct sign in
        </button>
        <span>Not sure? Ask your campus admin</span>
      </footer>
    </div>
  );
}
