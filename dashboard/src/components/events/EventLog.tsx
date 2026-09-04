"use client";
import { WebhookEventLog } from "./WebhookFirePanel";

export default function EventLog({ logs }: { logs: WebhookEventLog[] }) {
  return (
    <div className="glass-panel p-6 h-full flex flex-col">
      <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-widest flex items-center gap-2 shrink-0">
        <span className="text-[#00F0FF]">📝</span> Session Event Log
      </h3>

      <div className="flex-1 overflow-y-auto no-scrollbar space-y-4 pr-2 min-h-[400px]">
        {logs.length === 0 ? (
          <div className="h-full flex items-center justify-center border border-dashed border-white/10 rounded-lg">
            <p className="text-white/30 text-xs font-mono text-center">
              No events fired in this session.<br/>
              Use the panel to simulate webhooks.
            </p>
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="bg-white/[0.02] border border-white/5 p-4 rounded-lg">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded ${
                    log.success ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {log.success ? 'SUCCESS' : 'FAILED'}
                  </span>
                  <span className="text-sm font-bold text-white">{log.eventType}</span>
                </div>
                <span className="text-[10px] font-mono text-white/50">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
              </div>
              
              <div className="text-xs text-white/70 font-mono mb-2">
                Target Invoice: <span className="text-[#00F0FF]">#{log.invoiceId}</span>
              </div>
              
              <div className="bg-black/40 p-3 rounded border border-white/5 text-[10px] font-mono text-white/50 overflow-x-auto">
                <pre>{JSON.stringify(log.response, null, 2)}</pre>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
