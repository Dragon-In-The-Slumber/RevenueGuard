"use client";
import { useState } from "react";
import WebhookFirePanel, { WebhookEventLog } from "@/components/events/WebhookFirePanel";
import EventLog from "@/components/events/EventLog";

export default function EventsPage() {
  const [logs, setLogs] = useState<WebhookEventLog[]>([]);

  const handleEventFired = (log: WebhookEventLog) => {
    setLogs(prev => [log, ...prev]);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 h-[calc(100vh-80px)] flex flex-col">
      <div className="shrink-0">
        <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Webhook & Event Simulator</h1>
        <p className="text-white/50 text-sm font-mono max-w-2xl">
          Trigger system events to simulate real-world actions like incoming payments, disputes, or bank transfers. These events push directly to the FastAPI backend and instantly update invoice state.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 flex-1 min-h-0">
        <div className="lg:col-span-1">
          <WebhookFirePanel onEventFired={handleEventFired} />
        </div>
        
        <div className="lg:col-span-2 h-full">
          <EventLog logs={logs} />
        </div>
      </div>
    </div>
  );
}
