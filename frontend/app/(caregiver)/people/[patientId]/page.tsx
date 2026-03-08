"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiGet, apiPost } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import type { FamiliarPerson } from "../../../../lib/types";

export default function PeoplePage({ params }: { params: { patientId: string } }) {
  const [people, setPeople] = useState<FamiliarPerson[]>([]);
  const [name, setName] = useState("");
  const [relationship, setRelationship] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token) return;
    const res = await apiGet<FamiliarPerson[]>(`/patients/${params.patientId}/people/`, token);
    setError(res.error || null);
    setPeople(res.data || []);
  }

  useEffect(() => {
    setPatientId(params.patientId);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.patientId]);

  async function addPerson(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;

    const fd = new FormData();
    fd.append("name", name);
    if (relationship) fd.append("relationship", relationship);
    if (photos.length === 0) {
      setError("Please upload at least one face photo.");
      return;
    }
    for (const photo of photos) {
      fd.append("photos", photo);
    }

    const res = await apiPost<FamiliarPerson>(`/patients/${params.patientId}/people/`, fd, token);
    if (res.error) {
      setError(res.error);
      return;
    }
    setName("");
    setRelationship("");
    setPhotos([]);
    setError(null);
    await load();
  }

  return (
    <main>
      <h1>Familiar People</h1>
      <form className="grid" style={{ maxWidth: 520 }} onSubmit={addPerson}>
        <input className="input" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <input className="input" placeholder="Relationship" value={relationship} onChange={(e) => setRelationship(e.target.value)} />
        <input
          className="input"
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => setPhotos(Array.from(e.target.files || []))}
          required
        />
        <button className="btn" type="submit">Add</button>
      </form>

      {error && <p style={{ color: "#b42318" }}>{error}</p>}

      <div className="grid" style={{ marginTop: 16 }}>
        {people.map((p) => (
          <div className="card" key={p.id}>
            <strong>{p.name}</strong>
            <div>{p.relationship || ""}</div>
            <div>{p.notes || ""}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
