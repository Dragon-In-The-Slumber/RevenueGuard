"use client";
import { useState } from "react";
import { apiPost } from "@/lib/api";
import { useApi } from "@/hooks/useApi";

export default function SimulationController() {
  const [loading, setLoading] = useState(false);
  const [autoRun, setAutoRun] = useState(false);
  const [autoRunProgress, setAutoRunProgress] = useState(0);
  const [autoRunTotal, setAutoRunTotal] = useState(30);
  const [virtualDate, setVirtualDate] = useState<string | null>(null);

  const handleGenerate = async (count: number) => {
    try {
      setLoading(true);
      await apiPost("/api/invoices/simulate_batch", { count });
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

  const handleAutoRun = async (days: number) => {
    if (autoRun) return;
    setAutoRun(true);
    setAutoRunTotal(days);
    setAutoRunProgress(0);
    
    try {
      for (let i = 0; i < days; i++) {
        const res: any = await apiPost("/api/simulation/tick", {});
        if (res.virtual_date) setVirtualDate(res.virtual_date);
        setAutoRunProgress(i + 1);
      }
    } catch (e) {
      console.error("Tick failed", e);
    } finally {
      setAutoRun(false);
    }
  };

  const handleReset = async () => {
    try {
      setLoading(true);
      await apiPost("/api/simulation/reset", {});
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel p-4 flex flex-col gap-4 relative">
      <button 
        onClick={handleReset} 
        disabled={loading || autoRun} 
        className="absolute top-4 right-4 text-xs px-3 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full hover:bg-red-500/20 transition-colors"
      >
        Reset Demo
      </button>

      {/* Demo Mode Row */}
      <div>
        <p className="text-[10px] font-mono uppercase tracking-widest text-white/30 mb-2">Demo Mode (Small Batches)</p>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => handleGenerate(5)} 
            disabled={loading || autoRun} 
            className="pill-btn text-xs px-3 py-1 bg-white/5 border border-white/10"
          >
            {loading && !autoRun ? "Generating..." : "Generate 5 Invoices"}
          </button>
          <button 
            onClick={() => handleAutoRun(5)} 
            disabled={loading || autoRun} 
            className="pill-btn text-xs px-3 py-1 bg-white/5 border border-white/10"
          >
            {autoRun && autoRunTotal === 5 ? `Auto-Running (${autoRunProgress}/5)...` : "Advance 5 Days"}
          </button>
          <button 
            onClick={() => handleAutoRun(15)} 
            disabled={loading || autoRun} 
            className="pill-btn text-xs px-3 py-1 bg-white/5 border border-white/10"
          >
            {autoRun && autoRunTotal === 15 ? `Auto-Running (${autoRunProgress}/15)...` : "Advance 15 Days"}
          </button>
        </div>
      </div>

      {/* Full Scale Row */}
      <div>
        <p className="text-[10px] font-mono uppercase tracking-widest text-white/30 mb-2">Full Scale Simulation</p>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => handleGenerate(100)} 
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
              onClick={() => handleAutoRun(30)} 
              disabled={loading || autoRun} 
              className="pill-btn"
            >
              {autoRun && autoRunTotal === 30 ? `Auto-Running (${autoRunProgress}/30)...` : "Auto-Run 30 Days"}
            </button>
          </div>
          
          {autoRun && (
            <div className="flex-1 max-w-xs mx-4 h-2 bg-white/10 rounded-full overflow-hidden">
              <div 
                className="h-full bg-accent-primary transition-all duration-300"
                style={{ width: `${(autoRunProgress / autoRunTotal) * 100}%` }}
              />
            </div>
          )}
          
          {virtualDate && (
            <div className="text-xs font-mono text-white/50 bg-white/5 px-2 py-1 rounded">
              Date: {virtualDate}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
