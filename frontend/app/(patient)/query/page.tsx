"use client";

import { FormEvent, useState } from "react";

import { apiPost } from "../../../lib/api";
import { getPatientId, getToken } from "../../../lib/session";
import type { QueryResult } from "../../../lib/types";

export default function PatientQueryPage() {
  const [question, setQuestion] = useState("Where are my keys?");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    const patientId = getPatientId();
    if (!token || !patientId) {
      setError("Login and set patient ID in Patient Home first");
      return;
    }

    const res = await apiPost<QueryResult>("/query", { patient_id: patientId, question }, token);
    setError(res.error || null);
    setResult(res.data || null);
  }

  return (
    <main>
      <h1>Find My Things</h1>
      <form className="grid" style={{ maxWidth: 620 }} onSubmit={onSubmit}>
        <input className="input" value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button className="btn" type="submit">Ask</button>
      </form>
      {error && <p style={{ color: "#b42318" }}>{error}</p>}
      {result && (
        <div className="card" style={{ marginTop: 16 }}>
          <strong>{result.answer_type}</strong>
          <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(result.results, null, 2)}</pre>
        </div>
      )}
    </main>
  );
}
