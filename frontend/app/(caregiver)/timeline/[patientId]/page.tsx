"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { apiGet } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import { useEventFeed } from "../../../../lib/useEventFeed";
import type { EventItem } from "../../../../lib/types";

const EVENT_ICONS: Record<string, { icon: string; color: string; bg: string }> = {
  face_recognized: { icon: '👤', color: 'var(--success)', bg: 'var(--success-muted)' },
  reminder_triggered: { icon: '⏰', color: 'var(--warning)', bg: 'var(--warning-muted)' },
  item_seen: { icon: '📦', color: 'var(--info)', bg: 'var(--info-muted)' },
  voice_query: { icon: '🎤', color: 'var(--accent-secondary)', bg: 'var(--accent-secondary-muted)' },
};

export default function TimelinePage({ params }: { params: { patientId: string } }) {
  const token = getToken();
  const [initialEvents, setInitialEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const { events, connected, error: wsError } = useEventFeed(params.patientId, token, initialEvents);

  useEffect(() => {
    async function loadInitial() {
      if (!token) {
        setError("Please login to access this page");
        setLoading(false);
        return;
      }
      const res = await apiGet<EventItem[]>(`/patients/${params.patientId}/events?limit=100`, token);
      setError(res.error || null);
      setInitialEvents(res.data || []);
      setPatientId(params.patientId);
      setLoading(false);
    }
    void loadInitial();
  }, [params.patientId, token]);

  function formatTime(timestamp: string): string {
    try {
      return new Date(timestamp).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    } catch {
      return timestamp;
    }
  }

  function formatDate(timestamp: string): string {
    try {
      return new Date(timestamp).toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return timestamp;
    }
  }

  function groupEventsByDate(events: EventItem[]): Record<string, EventItem[]> {
    const groups: Record<string, EventItem[]> = {};
    for (const event of events) {
      const date = event.occurred_at ? formatDate(event.occurred_at) : 'Unknown';
      if (!groups[date]) groups[date] = [];
      groups[date].push(event);
    }
    return groups;
  }

  const groupedEvents = groupEventsByDate(events);

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
            <h1 style={{ marginBottom: 4 }}>Event Timeline</h1>
            <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
              Activity history
            </p>
          </div>
          <div className="flex items-center gap-sm">
            <div className={`status-dot ${connected ? 'online' : 'offline'}`} />
            <span style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
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
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="card" style={{ padding: 12 }}>
              <div className="flex items-center gap-md">
                <div className="skeleton" style={{ width: 36, height: 36, borderRadius: 10 }} />
                <div style={{ flex: 1 }}>
                  <div className="skeleton" style={{ width: '60%', height: 16, marginBottom: 6 }} />
                  <div className="skeleton" style={{ width: '30%', height: 12 }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Events Timeline */}
      {!loading && events.length > 0 && (
        <div>
          {Object.entries(groupedEvents).map(([date, dateEvents]) => (
            <div key={date} style={{ marginBottom: 24 }}>
              <div 
                style={{ 
                  fontSize: '0.75rem', 
                  fontWeight: 600, 
                  color: 'var(--text-muted)', 
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  marginBottom: 12,
                  paddingLeft: 4
                }}
              >
                {date}
              </div>
              <div className="grid" style={{ gap: 8 }}>
                {dateEvents.map((event) => {
                  const eventStyle = EVENT_ICONS[event.type || ''] || { 
                    icon: '📋', 
                    color: 'var(--text-secondary)', 
                    bg: 'var(--surface)' 
                  };
                  
                  return (
                    <div key={event.id} className="card" style={{ padding: 12 }}>
                      <div className="flex items-start gap-md">
                        <div 
                          style={{ 
                            width: 36, 
                            height: 36, 
                            borderRadius: 10,
                            background: eventStyle.bg,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1rem',
                            flexShrink: 0
                          }}
                        >
                          {eventStyle.icon}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 600, marginBottom: 2, textTransform: 'capitalize' }}>
                            {event.type?.replace(/_/g, ' ') || 'Event'}
                          </div>
                          {event.payload && (
                            <div style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
                              {event.type === 'face_recognized' && (event.payload.name as string)}
                              {event.type === 'reminder_triggered' && (event.payload.message as string)}
                              {event.type === 'item_seen' && `${event.payload.item_name} in ${event.payload.room || 'unknown'}`}
                              {!['face_recognized', 'reminder_triggered', 'item_seen'].includes(event.type || '') && 
                                JSON.stringify(event.payload).slice(0, 50)}
                            </div>
                          )}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', flexShrink: 0 }}>
                          {event.occurred_at ? formatTime(event.occurred_at) : '—'}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && events.length === 0 && (
        <div className="card text-center" style={{ padding: 48 }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ margin: '0 auto 16px' }}>
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
          <h3 style={{ marginBottom: 8, color: 'var(--text-secondary)' }}>No events yet</h3>
          <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
            Events will appear here as they happen
          </p>
        </div>
      )}
    </main>
  );
}
