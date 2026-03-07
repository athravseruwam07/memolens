"use client";

import { useEffect, useState } from "react";

import { apiGet } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import type { CaregiverLink, Patient } from "../../../../lib/types";

export default function PatientDetailPage({ params }: { params: { id: string } }) {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [caregivers, setCaregivers] = useState<CaregiverLink[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const token = getToken();
      if (!token) {
        setError("Please login first");
        return;
      }
      const p = await apiGet<Patient>(`/patients/${params.id}`, token);
      const c = await apiGet<CaregiverLink[]>(`/patients/${params.id}/caregivers`, token);
      setError(p.error || c.error || null);
      setPatient(p.data || null);
      setCaregivers(c.data || []);
      setPatientId(params.id);
    }
    void load();
  }, [params.id]);

  return (
    <main>
      <h1>Patient Detail</h1>
      {error && <p style={{ color: "#b42318" }}>{error}</p>}
      {patient && (
        <div className="card">
          <h2>{patient.name}</h2>
          <p>Age: {patient.age ?? "n/a"}</p>
          <p>Tracked items: {(patient.tracked_items || []).join(", ") || "none"}</p>
        </div>
      )}

      <h2 style={{ marginTop: 16 }}>Caregivers</h2>
      <div className="grid">
        {caregivers.map((c) => (
          <div className="card" key={c.caregiver_id}>
            <strong>{c.caregiver_name || c.caregiver_email || c.caregiver_id}</strong>
            <div>{c.role}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
