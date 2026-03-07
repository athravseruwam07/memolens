"use client";

import { useEffect, useState } from "react";

import { apiGet } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import type { ItemState } from "../../../../lib/types";

export default function ItemsPage({ params }: { params: { patientId: string } }) {
  const [items, setItems] = useState<ItemState[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const token = getToken();
      if (!token) return;
      const res = await apiGet<ItemState[]>(`/patients/${params.patientId}/item-states/`, token);
      setError(res.error || null);
      setItems(res.data || []);
      setPatientId(params.patientId);
    }
    void load();
  }, [params.patientId]);

  return (
    <main>
      <h1>Item States</h1>
      {error && <p style={{ color: "#b42318" }}>{error}</p>}
      <div className="grid">
        {items.map((i) => (
          <div className="card" key={i.id}>
            <strong>{i.item_name}</strong>
            <div>Room: {i.last_seen_room || "unknown"}</div>
            <div>Seen: {i.last_seen_at ? new Date(i.last_seen_at).toLocaleString() : "n/a"}</div>
            <div>Confidence: {typeof i.confidence === "number" ? i.confidence.toFixed(2) : "n/a"}</div>
          </div>
        ))}
        {!items.length && <div className="card">No tracked item states yet.</div>}
      </div>
    </main>
  );
}
