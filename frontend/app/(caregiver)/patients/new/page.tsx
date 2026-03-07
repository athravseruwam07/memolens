"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { apiPost } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import type { Patient } from "../../../../lib/types";

export default function NewPatientPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [trackedItems, setTrackedItems] = useState("keys,phone,wallet");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) {
      setError("Please login first");
      return;
    }

    const payload = {
      name,
      age: age ? Number(age) : null,
      tracked_items: trackedItems.split(",").map((s) => s.trim()).filter(Boolean)
    };

    const res = await apiPost<Patient>("/patients/", payload, token);
    if (res.error) {
      setError(res.error);
      return;
    }

    setPatientId(res.data.id);
    router.push(`/patients/${res.data.id}`);
  }

  return (
    <main>
      <h1>Create Patient</h1>
      <form className="grid" style={{ maxWidth: 520 }} onSubmit={onSubmit}>
        <input className="input" placeholder="Patient name" value={name} onChange={(e) => setName(e.target.value)} required />
        <input className="input" placeholder="Age" value={age} onChange={(e) => setAge(e.target.value)} />
        <input className="input" placeholder="Tracked items (comma-separated)" value={trackedItems} onChange={(e) => setTrackedItems(e.target.value)} />
        <button className="btn" type="submit">Create</button>
      </form>
      {error && <p style={{ color: "#b42318" }}>{error}</p>}
    </main>
  );
}
