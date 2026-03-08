"use client";

import { useEffect, useState } from "react";

import { websocketBase } from "./env";

export function useVideoFeed(patientId: string | null, token: string | null) {
  const [frameB64, setFrameB64] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!patientId) return;

    const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : "";
    const wsUrl = `${websocketBase()}/ws/view/${patientId}${tokenQuery}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnected(true);
      setError(null);
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as { type?: string; frame_b64?: string };
        if (msg.type === "frame" && msg.frame_b64) {
          setFrameB64(msg.frame_b64);
        }
      } catch {
        // Ignore malformed messages.
      }
    };

    ws.onerror = () => {
      setError("Video feed connection error");
    };

    ws.onclose = () => {
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [patientId, token]);

  return { frameB64, connected, error };
}
