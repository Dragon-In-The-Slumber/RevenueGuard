import LangGraphFlow from "@/components/graph/LangGraphFlow";
import ExecutionTrace from "@/components/graph/ExecutionTrace";

export default function GraphPage() {
  return (
    <div className="flex flex-col h-[calc(100vh-80px)] overflow-y-auto no-scrollbar">
      <div className="p-8 pb-4">
        <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">LangGraph Execution</h1>
        <p className="text-white/50 text-sm font-mono max-w-2xl">
          Real-time visualization of the AI agent's decision-making graph. Watch as invoices traverse through state validations, RAG lookups, and compliance checks.
        </p>
      </div>

      <div className="px-8 pb-8 flex-col flex min-h-max">
        <LangGraphFlow />
        <ExecutionTrace />
      </div>
    </div>
  );
}
