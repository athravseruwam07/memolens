import type { EventItem } from "../../lib/types";

export function LiveEventFeed({ events }: { events: EventItem[] }) {
  return (
    <div className="grid">
      {events.map((event) => (
        <div key={event.id} className="card">
          <strong>{event.type || "event"}</strong>
          <div>{new Date(event.occurred_at).toLocaleString()}</div>
        </div>
      ))}
      {events.length === 0 && <div className="card">No events yet.</div>}
    </div>
  );
}
