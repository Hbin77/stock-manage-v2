"use client";
import { useEffect, useRef, useState } from "react";

interface SSEEvent {
  type: string;
  data?: unknown;
  message?: string;
  count?: number;
}

export function useSSE() {
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

  useEffect(() => {
    const connect = () => {
      const eventSource = new EventSource(`${API_BASE}/api/v1/events`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const parsed: SSEEvent = JSON.parse(event.data);
          setLastEvent(parsed);
        } catch (e) {
          console.error("SSE 파싱 오류:", e);
        }
      };

      eventSource.onerror = () => {
        setIsConnected(false);
        eventSource.close();
        // 5초 후 재연결
        setTimeout(connect, 5000);
      };
    };

    connect();

    return () => {
      eventSourceRef.current?.close();
    };
  }, [API_BASE]);

  return { lastEvent, isConnected };
}
