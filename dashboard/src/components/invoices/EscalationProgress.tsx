export default function EscalationProgress({ stage }: { stage: string }) {
  // STAGE_1 -> 1, STAGE_2 -> 2, etc. Default to 1 if unknown or empty.
  let level = 1;
  if (stage === "STAGE_2") level = 2;
  else if (stage === "STAGE_3") level = 3;
  else if (stage === "STAGE_4") level = 4;

  return (
    <div className="flex items-center gap-1 group relative" title={stage || "No Stage"}>
      {[1, 2, 3, 4].map((step) => (
        <div 
          key={step} 
          className={`h-2 w-4 rounded-sm transition-colors ${
            step <= level 
              ? 'bg-accent-primary shadow-[0_0_5px_var(--accent-primary)]' 
              : 'bg-white/10'
          }`}
        />
      ))}
      <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-black text-white text-[10px] font-mono px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
        {stage || "None"}
      </span>
    </div>
  );
}
