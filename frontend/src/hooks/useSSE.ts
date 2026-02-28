"use client";
import { useEffect, useRef, useState } from "react";

interface SSEEvent {
  type: string;
  data?: unknown;
  message?: string;
  count?: number;
}

const MAX_RETRIES = 10;
const BASE_DELAY_MS = 2000;

export function useSSE() {
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

  useEffect(() => {
    const connect = () => {
      const eventSource = new EventSource(`${API_BASE}/api/v1/events`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        retryCountRef.current = 0;
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
        if (retryCountRef.current >= MAX_RETRIES) {
          console.warn("SSE 최대 재시도 횟수 초과. 재연결 중단.");
          return;
        }
        // 지수 백오프: 2s, 4s, 8s, 16s, ... (최대 60s)
        const delay = Math.min(60000, BASE_DELAY_MS * Math.pow(2, retryCountRef.current));
        retryCountRef.current += 1;
        retryTimerRef.current = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      eventSourceRef.current?.close();
    };
  }, [API_BASE]);

  return { lastEvent, isConnected };
}
