import KpiCards from "@/components/command-center/KpiCards";
import SimulationController from "@/components/command-center/SimulationController";
import RecoveryFunnel from "@/components/command-center/RecoveryFunnel";
import ActivityTicker from "@/components/command-center/ActivityTicker";

export default function CommandCenterPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header & Controller */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">AI Command Center</h1>
          <p className="text-white/50 text-sm font-mono max-w-2xl">
            Autonomous revenue recovery operations. Generate a simulation batch and advance the virtual timeline to monitor agent performance.
          </p>
        </div>
        <SimulationController />
      </div>

      {/* KPI Cards row */}
      <KpiCards />

      {/* Main Grid: Funnel and Ticker */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6 min-h-[400px]">
        <RecoveryFunnel />
        <ActivityTicker />
      </div>
    </div>
  );
}
