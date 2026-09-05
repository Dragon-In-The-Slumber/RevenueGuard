"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState, ReactNode } from "react";
import { mutate } from "swr";

const apiUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || apiUrl.replace(/^http/, "ws") + "/ws";

export interface NodeTrace {
  invoice_id: number;
  client_name: string;
  nodes: string[];
  action: string | null;
  status: string;
}

export interface TickPayload {
  virtual_date: string;
  active_nodes: string[];
  processed_count: number;
  traces: NodeTrace[];
}

interface WebSocketContextValue {
  connected: boolean;
  /** Nodes touched by the most recent tick — drives the graph animation. */
  activeNodes: string[];
  /** Per-invoice execution paths from the most recent tick. */
  traces: NodeTrace[];
  virtualDate: string | null;
  lastTickAt: number | null;
}

const WebSocketContext = createContext<WebSocketContextValue>({
  connected: false,
  activeNodes: [],
  traces: [],
  virtualDate: null,
  lastTickAt: null,
});

export const useWebSocketContext = () => useContext(WebSocketContext);

/**
 * One shared socket for the whole app.
 *
 * Previously `useWebSocket()` was called in a single component, so only /graph
 * had a live connection and every other page relied on a 5-second poll. It also
 * called `mutate(() => true)` on every message, revalidating every SWR key in the
 * app — a request storm during a fast auto-run. Keys are now targeted.
 */
export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [activeNodes, setActiveNodes] = useState<string[]>([]);
  const [traces, setTraces] = useState<NodeTrace[]>([]);
  const [virtualDate, setVirtualDate] = useState<string | null>(null);
  const [lastTickAt, setLastTickAt] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Revalidate the collections a tick can change, not every key in the app.
  const refresh = useCallback(() => {
    ["/api/metrics", "/api/funnel", "/api/invoices", "/api/audit-logs",
     "/api/clients", "/api/compliance/stats", "/api/compliance/rejected",
     "/api/simulation/state"].forEach((k) => mutate(k));
    // Per-invoice keys are parameterised, so match them by prefix.
    mutate((key) => typeof key === "string" && key.startsWith("/api/invoices/"));
  }, []);

  useEffect(() => {
    let reconnect: ReturnType<typeof setTimeout>;
    let closed = false;

    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "TICK_UPDATE" && data.payload) {
            const p = data.payload as TickPayload;
            setActiveNodes(p.active_nodes || []);
            setTraces(p.traces || []);
            setVirtualDate(p.virtual_date ?? null);
            setLastTickAt(Date.now());
          }
          if (data.virtual_date) setVirtualDate(data.virtual_date);
          if (data.event === "state_updated") refresh();
        } catch {
          /* ignore malformed frames */
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!closed) reconnect = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(reconnect);
      wsRef.current?.close();
    };
  }, [refresh]);

  return (
    <WebSocketContext.Provider value={{ connected, activeNodes, traces, virtualDate, lastTickAt }}>
      {children}
    </WebSocketContext.Provider>
  );
}
