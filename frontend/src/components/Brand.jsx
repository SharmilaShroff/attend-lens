export function Logo({ light = false, className = "" }) {
  return (
    <div className={`flex items-center gap-2 font-extrabold tracking-tight ${light ? "text-white" : "text-brand-800"} ${className}`}>
      <span className={`grid h-7 w-7 place-items-center rounded-full ${light ? "bg-white/20" : "bg-brand-700"}`}>
        <svg viewBox="0 0 24 24" className="h-4 w-4 text-white" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 12.5l4.5 4.5L19 7.5" />
        </svg>
      </span>
      <span className="text-lg">rollcall</span>
    </div>
  );
}

export const ArrowButton = ({ onClick, type = "button", disabled, size = "h-12 w-12" }) => (
  <button type={type} onClick={onClick} disabled={disabled}
    className={`grid ${size} place-items-center rounded-full bg-brand-700 text-white transition hover:bg-brand-800 disabled:opacity-60`}
    aria-label="Continue">
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 17L17 7M9 7h8v8" />
    </svg>
  </button>
);
