"use client";

interface ClientData {
  name: string;
  invoice_count: number;
  total_amount: number;
  recovered_amount: number;
  risk_level: string;
  tier: string;
  terms: string;
  contact: string;
}

export default function ClientCard({ client, onClick, isSelected }: { client: ClientData, onClick: () => void, isSelected: boolean }) {
  const isHighRisk = client.risk_level === "HIGH" || client.risk_level === "EXTREME";
  
  return (
    <div 
      onClick={onClick}
      className={`glass-panel p-5 cursor-pointer transition-all duration-300 relative overflow-hidden group
        ${isSelected ? 'border-accent-primary shadow-[0_0_20px_rgba(0,240,255,0.2)]' : 'hover:bg-white/[0.03]'}
      `}
    >
      <div className={`absolute -right-10 -top-10 w-32 h-32 rounded-full blur-3xl opacity-20 transition-colors
        ${isHighRisk ? 'bg-red-500' : 'bg-emerald-500'}
      `} />
      
      <div className="flex justify-between items-start mb-4 relative z-10">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-bold text-lg text-white group-hover:text-accent-primary transition-colors">{client.name}</h3>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/10 text-white/70">{client.tier}</span>
          </div>
          <p className="text-xs text-white/50">{client.invoice_count} Active Invoices</p>
        </div>
        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
          isHighRisk ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'
        }`}>
          {client.risk_level} RISK
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4 relative z-10 border-t border-b border-white/5 py-3">
        <div>
          <p className="text-[9px] uppercase font-mono text-white/30">Terms</p>
          <p className="text-xs font-mono text-white/80">{client.terms}</p>
        </div>
        <div>
          <p className="text-[9px] uppercase font-mono text-white/30">Key Contact</p>
          <p className="text-xs font-mono text-white/80 truncate">{client.contact}</p>
        </div>
      </div>

      <div className="space-y-4 relative z-10">
        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-1">Total Exposure</p>
          <p className="text-xl font-mono font-bold text-white">₹{client.total_amount.toLocaleString("en-IN")}</p>
        </div>

        <div>
          <div className="flex justify-between text-[10px] uppercase font-mono tracking-wider text-white/30 mb-1">
            <span>Recovery Rate</span>
            <span>{client.total_amount > 0 ? Math.round((client.recovered_amount / client.total_amount) * 100) : 0}%</span>
          </div>
          <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div 
              className="h-full bg-accent-primary"
              style={{ width: `${client.total_amount > 0 ? (client.recovered_amount / client.total_amount) * 100 : 0}%` }}
            />
          </div>
        </div>
        
        {isHighRisk && (
          <div className="pt-2">
            <span className="inline-block text-[10px] bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-1 rounded">
              ⚠️ Strict PTP Enforcement
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
