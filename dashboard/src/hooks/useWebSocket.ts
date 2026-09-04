"use client";
import { useEffect, useCallback, useState } from "react";
import { mutate } from "swr";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

export function useWebSocket() {
  const [wsInstance, setWsInstance] = useState<WebSocket | null>(null);

  const refresh = useCallback(() => {
    // Revalidate all SWR caches when the backend broadcasts a state update
    mutate(() => true); // Revalidates ALL SWR keys
  }, []);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        setWsInstance(ws);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === "state_updated") {
            refresh();
          }
        } catch(e) {}
      };
      ws.onclose = () => {
        setWsInstance(null);
        reconnectTimeout = setTimeout(connect, 3000);
      };
    };
    connect();

    return () => {
      ws?.close();
      clearTimeout(reconnectTimeout);
    };
  }, [refresh]);

  return { ws: wsInstance };
}
