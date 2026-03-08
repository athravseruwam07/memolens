"use client";

import { useEffect, useMemo, useState } from "react";

import { apiGet } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import { useEventFeed } from "../../../../lib/useEventFeed";
import type { EventItem, ItemState } from "../../../../lib/types";

function applyItemEvents(base: ItemState[], events: EventItem[]): ItemState[] {
  const byName = new Map<string, ItemState>();
  for (const item of base) {
    byName.set(item.item_name, item);
  }

  for (const event of events) {
    if (event.type !== "item_seen") continue;
    const payload = event.payload || {};
    const itemName = typeof payload.item_name === "string" ? payload.item_name : null;
    if (!itemName) continue;

    const prev = byName.get(itemName);
    const next: ItemState = {
      id: prev?.id || `live-${itemName}`,
      patient_id: prev?.patient_id || event.patient_id,
      item_name: itemName,
      last_seen_room: typeof payload.room === "string" ? payload.room : (prev?.last_seen_room ?? null),
      last_seen_at: event.occurred_at || prev?.last_seen_at || null,
      snapshot_url: typeof payload.snapshot_url === "string" ? payload.snapshot_url : (prev?.snapshot_url ?? null),
      confidence: typeof payload.confidence === "number" ? payload.confidence : (prev?.confidence ?? null),
    };
    byName.set(itemName, next);
  }

  return Array.from(byName.values()).sort((a, b) => {
    const at = a.last_seen_at || "";
    const bt = b.last_seen_at || "";
    return at < bt ? 1 : -1;
  });
}

export default function ItemsPage({ params }: { params: { patientId: string } }) {
  const token = getToken();
  const [baseItems, setBaseItems] = useState<ItemState[]>([]);
  const [initialEvents, setInitialEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const { events, connected, error: wsError } = useEventFeed(params.patientId, token, initialEvents);

  const items = useMemo(() => applyItemEvents(baseItems, events), [baseItems, events]);

  useEffect(() => {
    async function load() {
      const tokenValue = getToken();
      if (!tokenValue) return;
      const [itemsRes, evRes] = await Promise.all([
        apiGet<ItemState[]>(`/patients/${params.patientId}/item-states/`, tokenValue),
        apiGet<EventItem[]>(`/patients/${params.patientId}/events?type=item_seen&limit=50`, tokenValue),
      ]);
      setError(itemsRes.error || evRes.error || null);
      setBaseItems(itemsRes.data || []);
      setInitialEvents(evRes.data || []);
      setPatientId(params.patientId);
    }
    void load();
  }, [params.patientId]);

  return (
    <main>
      <h1>Item States</h1>
      {(error || wsError) && <p style={{ color: "#b42318" }}>{error || wsError}</p>}
      <p>Live updates: {connected ? "connected" : "disconnected"}</p>
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
