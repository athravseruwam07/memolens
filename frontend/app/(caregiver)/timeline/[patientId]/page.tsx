"use client";

import { useEffect, useState } from "react";

import { apiGet } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import { useEventFeed } from "../../../../lib/useEventFeed";
import type { EventItem } from "../../../../lib/types";

export default function TimelinePage({ params }: { params: { patientId: string } }) {
  const token = getToken();
  const [initialEvents, setInitialEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const { events, connected, error: wsError } = useEventFeed(params.patientId, token, initialEvents);

  useEffect(() => {
    async function loadInitial() {
      if (!token) {
        setError("Please login first");
        return;
      }
      const res = await apiGet<EventItem[]>(`/patients/${params.patientId}/events?limit=100`, token);
      setError(res.error || null);
      setInitialEvents(res.data || []);
      setPatientId(params.patientId);
    }
    void loadInitial();
  }, [params.patientId, token]);

  return (
    <main>
      <h1>Event Timeline</h1>
      <p>Live feed: {connected ? "connected" : "disconnected"}</p>
      {(error || wsError) && <p style={{ color: "#b42318" }}>{error || wsError}</p>}
      <div className="grid">
        {events.map((event) => (
          <div className="card" key={event.id}>
            <strong>{event.type || "event"}</strong>
            <div>{event.occurred_at ? new Date(event.occurred_at).toLocaleString() : "n/a"}</div>
            <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(event.payload || {}, null, 2)}</pre>
          </div>
        ))}
        {!events.length && <div className="card">No events yet.</div>}
      </div>
    </main>
  );
}
