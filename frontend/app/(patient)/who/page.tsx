"use client";

import { useEffect, useState } from "react";

import { apiGet } from "../../../lib/api";
import { getPatientId, getToken } from "../../../lib/session";
import type { FamiliarPerson } from "../../../lib/types";

export default function PatientWhoPage() {
  const [people, setPeople] = useState<FamiliarPerson[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const token = getToken();
      const patientId = getPatientId();
      if (!token || !patientId) {
        setError("Login and set patient ID in Patient Home first");
        return;
      }
      const res = await apiGet<FamiliarPerson[]>(`/patients/${patientId}/people/`, token);
      setError(res.error || null);
      setPeople(res.data || []);
    }
    void load();
  }, []);

  return (
    <main>
      <h1>Who Is This?</h1>
      {error && <p style={{ color: "#b42318" }}>{error}</p>}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
        {people.map((p) => (
          <div className="card" key={p.id} style={{ fontSize: 24 }}>
            <strong>{p.name}</strong>
            <div>{p.relationship || ""}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
