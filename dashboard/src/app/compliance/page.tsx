import ComplianceScore from "@/components/compliance/ComplianceScore";
import RejectedDraftsGallery from "@/components/compliance/RejectedDraftsGallery";
import CooldownBoard from "@/components/compliance/CooldownBoard";

export default function CompliancePage() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Compliance & Guardrails</h1>
        <p className="text-white/50 text-sm font-mono max-w-2xl">
          Complete oversight of the AI's adherence to legal and strategic guardrails. Monitor rejection rates, review blocked communications, and track mandatory cooldown periods.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1 space-y-8">
          <ComplianceScore />
          <CooldownBoard />
        </div>
        
        <div className="lg:col-span-2">
          <RejectedDraftsGallery />
        </div>
      </div>
    </div>
  );
}
