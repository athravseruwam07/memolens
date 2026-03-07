"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiGet, apiPost } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import type { Reminder } from "../../../../lib/types";

export default function RemindersPage({ params }: { params: { patientId: string } }) {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [type, setType] = useState("time");
  const [meta, setMeta] = useState('{"time":"09:00"}');
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token) return;
    const res = await apiGet<Reminder[]>(`/patients/${params.patientId}/reminders/`, token);
    setError(res.error || null);
    setReminders(res.data || []);
  }

  useEffect(() => {
    setPatientId(params.patientId);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.patientId]);

  async function createReminder(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;

    let triggerMeta: Record<string, unknown> = {};
    try {
      triggerMeta = meta ? (JSON.parse(meta) as Record<string, unknown>) : {};
    } catch {
      setError("Invalid trigger_meta JSON");
      return;
    }

    const res = await apiPost<Reminder>(
      `/patients/${params.patientId}/reminders/`,
      { type, trigger_meta: triggerMeta, message, active: true },
      token
    );
    if (res.error) {
      setError(res.error);
      return;
    }

    setMessage("");
    await load();
  }

  return (
    <main>
      <h1>Reminders</h1>
      <form className="grid" style={{ maxWidth: 580 }} onSubmit={createReminder}>
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="time">time</option>
          <option value="person">person</option>
          <option value="location">location</option>
          <option value="object">object</option>
        </select>
        <textarea rows={3} value={meta} onChange={(e) => setMeta(e.target.value)} />
        <input className="input" placeholder="Message" value={message} onChange={(e) => setMessage(e.target.value)} required />
        <button className="btn" type="submit">Create Reminder</button>
      </form>

      {error && <p style={{ color: "#b42318" }}>{error}</p>}

      <div className="grid" style={{ marginTop: 16 }}>
        {reminders.map((r) => (
          <div className="card" key={r.id}>
            <strong>{r.type}</strong>
            <div>{r.message}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
