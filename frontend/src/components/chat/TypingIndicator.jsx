export default function TypingIndicator({ phase = 'Thinking...' }) {
  return (
    <div className="flex gap-3 animate-fade-in" role="status" aria-label="Astra is typing" aria-live="polite">
      <div className="mt-0.5 flex h-7 min-w-11 flex-shrink-0 items-center justify-center rounded-full border border-white/20 bg-white/[0.03] px-2">
        <span className="text-[8px] font-semibold uppercase tracking-[0.08em] text-[#8E969F]">Astra</span>
      </div>
      <div className="max-w-xs rounded-xl border border-white/12 bg-white/[0.03] px-3.5 py-3 text-[#C5C6C7] shadow-[0_6px_18px_rgba(2,6,23,0.16)] md:max-w-md">
        <p className="mb-2 text-[10px] uppercase tracking-[0.12em] text-[#8E969F]">{phase}</p>
        <div className="typing-indicator">
          <span aria-hidden="true" />
          <span aria-hidden="true" />
          <span aria-hidden="true" />
        </div>
      </div>
    </div>
  )
}
