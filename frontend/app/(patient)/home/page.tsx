"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiGet } from "../../../lib/api";
import { getPatientId, getToken, setPatientId } from "../../../lib/session";
import type { Reminder } from "../../../lib/types";

export default function PatientHomePage() {
  const [patientId, setPatientInput] = useState(getPatientId() || "");
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token || !patientId) return;
    const res = await apiGet<Reminder[]>(`/patients/${patientId}/reminders/`, token);
    setError(res.error || null);
    setReminders((res.data || []).filter((r) => r.active));
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

      {error && <p style={{ color: "#b42318" }}>{error}</p>}

      <div className="grid" style={{ marginTop: 16 }}>
        {reminders.map((r) => (
          <div className="card" key={r.id} style={{ fontSize: 24, fontWeight: 600 }}>
            {r.message}
          </div>
        ))}
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
