"use client";

import { useEffect, useMemo, useState } from "react";

import { websocketBase } from "./env";
import type { EventItem } from "./types";

export function useEventFeed(patientId: string | null, token: string | null, initialEvents: EventItem[] = []) {
  const [events, setEvents] = useState<EventItem[]>(initialEvents);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEvents(initialEvents);
  }, [initialEvents]);

  useEffect(() => {
    if (!patientId || !token) return;

    const wsUrl = `${websocketBase()}/ws/events/${patientId}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnected(true);
      setError(null);
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as { type?: string; event?: EventItem };
        if (msg.type === "event" && msg.event) {
          setEvents((prev) => {
            const exists = prev.some((e) => e.id === msg.event!.id);
            if (exists) return prev;
            const next = [msg.event!, ...prev];
            next.sort((a, b) => (a.occurred_at < b.occurred_at ? 1 : -1));
            return next.slice(0, 200);
          });
        }
      } catch {
        // Ignore malformed messages.
      }
    };

    ws.onerror = () => {
      setError("Live feed connection error");
    };

    ws.onclose = () => {
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [patientId, token]);

  const latest = useMemo(() => events[0] || null, [events]);

  return { events, connected, error, latest };
}
