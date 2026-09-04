"use client";
import { useState } from "react";
import { apiPost } from "@/lib/api";
import { useApi } from "@/hooks/useApi";

export default function SimulationController() {
  const [loading, setLoading] = useState(false);
  const [autoRun, setAutoRun] = useState(false);
  const [autoRunProgress, setAutoRunProgress] = useState(0);
  const [virtualDate, setVirtualDate] = useState<string | null>(null);

  const handleGenerate = async () => {
    try {
      setLoading(true);
      await apiPost("/api/invoices/simulate_batch", { count: 100 });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleTick = async () => {
    try {
      setLoading(true);
      const res: any = await apiPost("/api/simulation/tick", {});
      if (res.virtual_date) setVirtualDate(res.virtual_date);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoRun = () => {
    if (autoRun) return;
    setAutoRun(true);
    setAutoRunProgress(0);
    
    let ticks = 0;
    const interval = setInterval(async () => {
      if (ticks >= 30) {
        clearInterval(interval);
        setAutoRun(false);
        return;
      }
      try {
        const res: any = await apiPost("/api/simulation/tick", {});
        if (res.virtual_date) setVirtualDate(res.virtual_date);
        ticks++;
        setAutoRunProgress(ticks);
      } catch (e) {
        console.error("Tick failed", e);
        clearInterval(interval);
        setAutoRun(false);
      }
    }, 1000);
  };

  return (
    <div className="glass-panel p-4 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <button 
          onClick={handleGenerate} 
          disabled={loading || autoRun} 
          className="pill-btn primary"
        >
          {loading && !autoRun ? "Generating..." : "Generate 100 Invoices"}
        </button>
        <button 
          onClick={handleTick} 
          disabled={loading || autoRun} 
          className="pill-btn"
        >
          Advance 1 Day
        </button>
        <button 
          onClick={handleAutoRun} 
          disabled={loading || autoRun} 
          className="pill-btn"
        >
          {autoRun ? `Auto-Running (${autoRunProgress}/30)...` : "Auto-Run 30 Days"}
        </button>
      </div>
      
      {autoRun && (
        <div className="flex-1 max-w-xs mx-4 h-2 bg-white/10 rounded-full overflow-hidden">
          <div 
            className="h-full bg-[#00F0FF] transition-all duration-300"
            style={{ width: `${(autoRunProgress / 30) * 100}%` }}
          />
        </div>
      )}
      
      {virtualDate && (
        <div className="text-xs font-mono text-white/50 bg-white/5 px-2 py-1 rounded">
          Date: {virtualDate}
        </div>
      )}
    </div>
  );
}
