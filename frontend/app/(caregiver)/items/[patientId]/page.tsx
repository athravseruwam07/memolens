"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

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
  const [loading, setLoading] = useState(true);

  const { events, connected, error: wsError } = useEventFeed(params.patientId, token, initialEvents);

  const items = useMemo(() => applyItemEvents(baseItems, events), [baseItems, events]);

  useEffect(() => {
    async function load() {
      const tokenValue = getToken();
      if (!tokenValue) {
        setError("Please login to access this page");
        setLoading(false);
        return;
      }
      const [itemsRes, evRes] = await Promise.all([
        apiGet<ItemState[]>(`/patients/${params.patientId}/item-states/`, tokenValue),
        apiGet<EventItem[]>(`/patients/${params.patientId}/events?type=item_seen&limit=50`, tokenValue),
      ]);
      setError(itemsRes.error || evRes.error || null);
      setBaseItems(itemsRes.data || []);
      setInitialEvents(evRes.data || []);
      setPatientId(params.patientId);
      setLoading(false);
    }
    void load();
  }, [params.patientId]);

  function formatTimeAgo(timestamp: string): string {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return "Just now";
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      return `${diffDays}d ago`;
    } catch {
      return timestamp;
    }
  }

  return (
    <main>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Link href="/dashboard" className="btn ghost small" style={{ marginBottom: 16, padding: '8px 12px' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          Dashboard
        </Link>
        <div className="flex justify-between items-center">
          <div>
            <h1 style={{ marginBottom: 4 }}>Item Tracker</h1>
            <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
              View detected item locations
            </p>
          </div>
          <div className="flex items-center gap-sm">
            <div className={`status-dot ${connected ? 'online' : 'offline'}`} />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {connected ? 'Live' : 'Offline'}
            </span>
          </div>
        </div>
      </div>

      {(error || wsError) && (
        <div className="error-message" style={{ marginBottom: 16 }}>
          {error || wsError}
          {error?.includes("login") && (
            <Link href="/login" className="btn small" style={{ marginLeft: 12 }}>
              Sign In
            </Link>
          )}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="grid" style={{ gap: 12 }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-md">
                  <div className="skeleton" style={{ width: 40, height: 40, borderRadius: 10 }} />
                  <div>
                    <div className="skeleton" style={{ width: 80, height: 18, marginBottom: 6 }} />
                    <div className="skeleton" style={{ width: 100, height: 14 }} />
                  </div>
                </div>
                <div className="skeleton" style={{ width: 50, height: 14 }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Items List */}
      {!loading && items.length > 0 && (
        <div className="grid" style={{ gap: 12 }}>
          {items.map((item) => (
            <div key={item.id} className="card">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-md">
                  <div 
                    style={{ 
                      width: 40, 
                      height: 40, 
                      borderRadius: 10,
                      background: 'var(--accent-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--accent)'
                    }}
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="11" cy="11" r="8"/>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, textTransform: 'capitalize', marginBottom: 2 }}>
                      {item.item_name}
                    </div>
                    <div className="flex items-center gap-sm" style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                        <circle cx="12" cy="10" r="3"/>
                      </svg>
                      <span>{item.last_seen_room || "Unknown location"}</span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {item.last_seen_at ? formatTimeAgo(item.last_seen_at) : "N/A"}
                  </div>
                  {typeof item.confidence === "number" && (
                    <div 
                      className={`badge ${item.confidence > 0.7 ? 'success' : item.confidence > 0.4 ? 'warning' : ''}`}
                      style={{ marginTop: 4, fontSize: '0.65rem' }}
                    >
                      {(item.confidence * 100).toFixed(0)}%
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && items.length === 0 && !error && (
        <div className="card text-center" style={{ padding: 48 }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ margin: '0 auto 16px' }}>
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <h3 style={{ marginBottom: 8, color: 'var(--text-secondary)' }}>No items tracked yet</h3>
          <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
            Items will appear here as the camera detects them
          </p>
        </div>
      )}

      {/* Info Card */}
      {!loading && items.length > 0 && (
        <div className="card" style={{ marginTop: 24, background: 'var(--info-muted)', borderColor: 'rgba(59, 130, 246, 0.3)' }}>
          <div className="flex items-center gap-sm" style={{ color: 'var(--info)' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            <span style={{ fontSize: '0.875rem' }}>
              Item locations are updated automatically as the camera detects them
            </span>
          </div>
        </div>
      )}
    </main>
  );
}
