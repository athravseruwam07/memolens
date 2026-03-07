"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiGet } from "../../../lib/api";
import { getPatientId, getToken, setPatientId } from "../../../lib/session";
import { useEventFeed } from "../../../lib/useEventFeed";
import type { EventItem, Patient } from "../../../lib/types";

function pickLatest(events: EventItem[], type: string): EventItem | null {
  return events.find((e) => e.type === type) || null;
}

export default function CaregiverDashboardPage() {
  const token = getToken();
  const [patientId, setPatientIdInput] = useState<string>(getPatientId() || "");
  const [patient, setPatient] = useState<Patient | null>(null);
  const [initialEvents, setInitialEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const { events, connected, error: wsError } = useEventFeed(patientId || null, token, initialEvents);

  const latestPerson = useMemo(() => pickLatest(events, "face_recognized"), [events]);
  const latestReminder = useMemo(() => pickLatest(events, "reminder_triggered"), [events]);
  const latestItem = useMemo(() => pickLatest(events, "item_seen"), [events]);

  async function load() {
    if (!token || !patientId) {
      setError("Please login and provide patient ID");
      return;
    }

    const p = await apiGet<Patient>(`/patients/${patientId}`, token);
    const e = await apiGet<EventItem[]>(`/patients/${patientId}/events?limit=40`, token);

    setError(p.error || e.error || null);
    setPatient(p.data || null);
    setInitialEvents(e.data || []);
    setPatientId(patientId);
  }

  useEffect(() => {
    if (patientId && token) {
      void load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main>
      <h1>Caregiver Dashboard</h1>
      <div className="grid" style={{ maxWidth: 700 }}>
        <input className="input" placeholder="Patient ID" value={patientId} onChange={(e) => setPatientIdInput(e.target.value)} />
        <button className="btn" onClick={() => void load()} type="button">Set Patient Context</button>
      </div>

      {(error || wsError) && <p style={{ color: "#b42318" }}>{error || wsError}</p>}

      {patient && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2>{patient.name}</h2>
          <p>Live feed: {connected ? "connected" : "disconnected"}</p>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
            <div className="card">
              <strong>Last Person</strong>
              <div>{(latestPerson?.payload?.name as string) || "none"}</div>
            </div>
            <div className="card">
              <strong>Last Reminder</strong>
              <div>{(latestReminder?.payload?.message as string) || "none"}</div>
            </div>
            <div className="card">
              <strong>Last Item Seen</strong>
              <div>{(latestItem?.payload?.item_name as string) || "none"}</div>
            </div>
          </div>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", marginTop: 12 }}>
            <Link href={`/patients/${patient.id}`}>Patient Detail</Link>
            <Link href={`/people/${patient.id}`}>Familiar People</Link>
            <Link href={`/reminders/${patient.id}`}>Reminders</Link>
            <Link href={`/notes/${patient.id}`}>Daily Notes</Link>
            <Link href={`/items/${patient.id}`}>Item States</Link>
            <Link href={`/timeline/${patient.id}`}>Event Timeline</Link>
          </div>
        </div>
      )}

      <section style={{ marginTop: 20 }}>
        <h2>Recent Events (Live)</h2>
        <div className="grid">
          {events.slice(0, 20).map((event) => (
            <div key={event.id} className="card">
              <strong>{event.type || "event"}</strong>
              <div>{event.occurred_at ? new Date(event.occurred_at).toLocaleString() : "n/a"}</div>
            </div>
          ))}
          {!events.length && <div className="card">No events.</div>}
        </div>
      </section>
    </main>
  );
}
