"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiGet } from "../../../lib/api";
import { getPatientId, getToken, setPatientId } from "../../../lib/session";
import { useEventFeed } from "../../../lib/useEventFeed";
import type { EventItem, Reminder } from "../../../lib/types";

function extractReminderMessage(event: EventItem): string | null {
  if (event.type !== "reminder_triggered") return null;
  const payload = event.payload || {};
  const msg = payload.message;
  return typeof msg === "string" ? msg : null;
}

export default function PatientHomePage() {
  const token = getToken();
  const [patientId, setPatientInput] = useState(getPatientId() || "");
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [initialEvents, setInitialEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const { events, connected, error: wsError } = useEventFeed(patientId || null, token, initialEvents);

  const liveMessages = useMemo(() => {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const e of events) {
      const msg = extractReminderMessage(e);
      if (!msg || seen.has(msg)) continue;
      seen.add(msg);
      out.push(msg);
    }
    return out.slice(0, 6);
  }, [events]);

  async function load() {
    if (!token || !patientId) return;
    const [remRes, evRes] = await Promise.all([
      apiGet<Reminder[]>(`/patients/${patientId}/reminders/`, token),
      apiGet<EventItem[]>(`/patients/${patientId}/events?type=reminder_triggered&limit=30`, token),
    ]);
    setError(remRes.error || evRes.error || null);
    setReminders((remRes.data || []).filter((r) => r.active));
    setInitialEvents(evRes.data || []);
    setPatientId(patientId);
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main>
      <h1>Patient Home</h1>
      <div className="grid" style={{ maxWidth: 600 }}>
        <input className="input" placeholder="Patient ID" value={patientId} onChange={(e) => setPatientInput(e.target.value)} />
        <button className="btn" type="button" onClick={() => void load()}>Load</button>
      </div>

      {(error || wsError) && <p style={{ color: "#b42318" }}>{error || wsError}</p>}
      <p>Live updates: {connected ? "connected" : "disconnected"}</p>

      <h2>Active Reminders</h2>
      <div className="grid" style={{ marginTop: 8 }}>
        {reminders.map((r) => (
          <div className="card" key={r.id} style={{ fontSize: 24, fontWeight: 600 }}>
            {r.message}
          </div>
        ))}
      </div>

      <h2 style={{ marginTop: 20 }}>Live Prompts</h2>
      <div className="grid" style={{ marginTop: 8 }}>
        {liveMessages.map((msg, idx) => (
          <div className="card" key={`${msg}-${idx}`} style={{ fontSize: 24, fontWeight: 600 }}>
            {msg}
          </div>
        ))}
        {!liveMessages.length && <div className="card">Waiting for live reminder events...</div>}
      </div>

      {patientId && (
        <div style={{ marginTop: 16 }}>
          <Link href="/query">Find My Things</Link>
          <br />
          <Link href="/who">Who Is This?</Link>
        </div>
      )}
    </main>
  );
}
